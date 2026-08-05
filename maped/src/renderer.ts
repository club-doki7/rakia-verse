import shaderSrc from './shader.wgsl?raw';
import { buildGlyphAtlas, ATLAS_W, ATLAS_H } from './glyphs.ts';
import { HEX_W, ROW_H } from './hex.ts';
import type { HexGrid } from './grid.ts';

const UNIFORM_BYTES = 80;

const PREMULTIPLIED_BLEND: GPUBlendState = {
  color: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' },
  alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' },
};

export interface RenderOpts {
  panX: number;
  panY: number;
  zoom: number;
  fillAlpha: number;
  lineAlpha: number;
  textAlpha: number;
  backdropAlpha: number;
  cursorCol: number;
  cursorRow: number;
  cursorValid: boolean;
}

export class Renderer {
  readonly canvas: HTMLCanvasElement;
  private readonly device: GPUDevice;
  private readonly context: GPUCanvasContext;
  private readonly format: GPUTextureFormat;

  private readonly glyphTexture: GPUTexture;
  private backdropTexture: GPUTexture | null = null;
  private backdropW = 0;
  private backdropH = 0;

  private readonly sampler: GPUSampler;
  private readonly uniformBuffer: GPUBuffer;
  private cellBuffer!: GPUBuffer;
  private cellCapacity = 0;

  private readonly bindGroupLayout0: GPUBindGroupLayout;
  private readonly bindGroupLayout1: GPUBindGroupLayout;

  private readonly fillPipeline: GPURenderPipeline;
  private readonly linesPipeline: GPURenderPipeline;
  private readonly cursorPipeline: GPURenderPipeline;
  private readonly textPipeline: GPURenderPipeline;
  private readonly backdropPipeline: GPURenderPipeline;

  private bindGroup0: GPUBindGroup;
  private bindGroup1: GPUBindGroup | null = null;

  public lastRevision = -1;

  constructor(canvas: HTMLCanvasElement, device: GPUDevice, context: GPUCanvasContext) {
    this.canvas = canvas;
    this.device = device;
    this.context = context;
    this.format = navigator.gpu.getPreferredCanvasFormat();

    context.configure({ device, format: this.format, alphaMode: 'premultiplied' });

    this.glyphTexture = this.uploadGlyphAtlas();
    this.sampler = device.createSampler({ magFilter: 'linear', minFilter: 'linear' });
    this.uniformBuffer = device.createBuffer({
      size: UNIFORM_BYTES,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });

    const bothStages = GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT;
    this.bindGroupLayout0 = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: bothStages, buffer: { type: 'uniform' } },
        { binding: 1, visibility: GPUShaderStage.VERTEX, buffer: { type: 'read-only-storage' } },
        { binding: 2, visibility: GPUShaderStage.FRAGMENT, texture: { sampleType: 'float' } },
        { binding: 3, visibility: GPUShaderStage.FRAGMENT, sampler: { type: 'filtering' } },
      ],
    });
    this.bindGroupLayout1 = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: GPUShaderStage.FRAGMENT, texture: { sampleType: 'float' } },
      ],
    });

    const gridLayout = device.createPipelineLayout({ bindGroupLayouts: [this.bindGroupLayout0] });
    const backdropLayout = device.createPipelineLayout({
      bindGroupLayouts: [this.bindGroupLayout0, this.bindGroupLayout1],
    });

    const module = device.createShaderModule({ code: shaderSrc });
    const target: GPUColorTargetState = { format: this.format, blend: PREMULTIPLIED_BLEND };

    const pipeline = (
      layout: GPUPipelineLayout,
      vs: string,
      fs: string,
      topology: GPUPrimitiveTopology,
    ): GPURenderPipeline =>
      device.createRenderPipeline({
        layout,
        vertex: { module, entryPoint: vs },
        fragment: { module, entryPoint: fs, targets: [target] },
        primitive: { topology },
      });

    this.fillPipeline = pipeline(gridLayout, 'vsFill', 'fsFill', 'triangle-list');
    this.linesPipeline = pipeline(gridLayout, 'vsLines', 'fsLines', 'line-list');
    this.cursorPipeline = pipeline(gridLayout, 'vsCursor', 'fsCursor', 'line-list');
    this.textPipeline = pipeline(gridLayout, 'vsText', 'fsText', 'triangle-list');
    this.backdropPipeline = pipeline(backdropLayout, 'vsBackdrop', 'fsBackdrop', 'triangle-list');

    this.growCellBuffer(4096);
    this.bindGroup0 = this.createBindGroup0();
  }

  private uploadGlyphAtlas(): GPUTexture {
    const canvas = buildGlyphAtlas();
    const texture = this.device.createTexture({
      size: [ATLAS_W, ATLAS_H],
      format: 'rgba8unorm',
      usage:
        GPUTextureUsage.TEXTURE_BINDING |
        GPUTextureUsage.COPY_DST |
        GPUTextureUsage.RENDER_ATTACHMENT,
    });
    this.device.queue.copyExternalImageToTexture({ source: canvas }, { texture }, [
      ATLAS_W,
      ATLAS_H,
    ]);
    return texture;
  }

  setBackdrop(image: ImageBitmap | null): void {
    if (this.backdropTexture) {
      this.backdropTexture.destroy();
      this.backdropTexture = null;
      this.bindGroup1 = null;
      this.backdropW = 0;
      this.backdropH = 0;
    }
    if (!image) return;

    this.backdropW = image.width;
    this.backdropH = image.height;
    this.backdropTexture = this.device.createTexture({
      size: [image.width, image.height],
      format: 'rgba8unorm',
      usage:
        GPUTextureUsage.TEXTURE_BINDING |
        GPUTextureUsage.COPY_DST |
        GPUTextureUsage.RENDER_ATTACHMENT,
    });
    this.device.queue.copyExternalImageToTexture(
      { source: image },
      { texture: this.backdropTexture },
      [image.width, image.height],
    );
    this.bindGroup1 = this.device.createBindGroup({
      layout: this.bindGroupLayout1,
      entries: [{ binding: 0, resource: this.backdropTexture.createView() }],
    });
  }

  private createBindGroup0(): GPUBindGroup {
    return this.device.createBindGroup({
      layout: this.bindGroupLayout0,
      entries: [
        { binding: 0, resource: { buffer: this.uniformBuffer } },
        { binding: 1, resource: { buffer: this.cellBuffer } },
        { binding: 2, resource: this.glyphTexture.createView() },
        { binding: 3, resource: this.sampler },
      ],
    });
  }

  private growCellBuffer(minWords: number): boolean {
    if (this.cellCapacity >= minWords) return false;
    this.cellBuffer?.destroy();
    this.cellCapacity = minWords;
    this.cellBuffer = this.device.createBuffer({
      size: minWords * 4,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    return true;
  }

  private uploadGrid(grid: HexGrid): void {
    if (this.lastRevision === grid.revision) return;
    const words = Math.ceil((grid.cols * grid.rows) / 4);
    if (this.growCellBuffer(words)) this.bindGroup0 = this.createBindGroup0();

    const packed = new Uint32Array(words);
    const bytes = new Uint8Array(packed.buffer);
    bytes.set(grid.ids);
    this.device.queue.writeBuffer(this.cellBuffer, 0, packed);
    this.lastRevision = grid.revision;
  }

  render(grid: HexGrid, opts: RenderOpts): void {
    this.uploadGrid(grid);

    const dpr = window.devicePixelRatio || 1;
    const w = Math.floor(this.canvas.clientWidth * dpr);
    const h = Math.floor(this.canvas.clientHeight * dpr);
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }

    const minCol = Math.max(0, Math.floor((opts.panX - HEX_W) / HEX_W));
    const maxCol = Math.min(grid.cols - 1, Math.ceil((opts.panX + w / opts.zoom + HEX_W) / HEX_W));
    const minRow = Math.max(0, Math.floor((opts.panY - ROW_H) / ROW_H));
    const maxRow = Math.min(grid.rows - 1, Math.ceil((opts.panY + h / opts.zoom + ROW_H) / ROW_H));
    const visCols = maxCol - minCol + 1;
    const visRows = maxRow - minRow + 1;
    const instances = visCols > 0 && visRows > 0 ? visCols * visRows : 0;

    const uniforms = new ArrayBuffer(UNIFORM_BYTES);
    const f32 = new Float32Array(uniforms);
    const i32 = new Int32Array(uniforms);
    f32[0] = opts.panX;
    f32[1] = opts.panY;
    f32[2] = opts.zoom;
    f32[3] = opts.textAlpha;
    f32[4] = w;
    f32[5] = h;
    f32[6] = this.backdropW;
    f32[7] = this.backdropH;
    i32[8] = grid.cols;
    i32[9] = visCols;
    i32[10] = minCol;
    i32[11] = minRow;
    f32[12] = opts.fillAlpha;
    f32[13] = opts.lineAlpha;
    f32[14] = opts.backdropAlpha;
    i32[16] = opts.cursorCol;
    i32[17] = opts.cursorRow;
    i32[18] = opts.cursorValid ? 1 : 0;
    this.device.queue.writeBuffer(this.uniformBuffer, 0, uniforms);

    const encoder = this.device.createCommandEncoder();
    const pass = encoder.beginRenderPass({
      colorAttachments: [
        {
          view: this.context.getCurrentTexture().createView(),
          loadOp: 'clear',
          storeOp: 'store',
          clearValue: { r: 0.12, g: 0.12, b: 0.14, a: 1.0 },
        },
      ],
    });

    if (this.backdropTexture && this.bindGroup1 && opts.backdropAlpha > 0) {
      pass.setPipeline(this.backdropPipeline);
      pass.setBindGroup(0, this.bindGroup0);
      pass.setBindGroup(1, this.bindGroup1);
      pass.draw(6, 1);
    }

    if (instances > 0) {
      pass.setBindGroup(0, this.bindGroup0);

      if (opts.fillAlpha > 0) {
        pass.setPipeline(this.fillPipeline);
        pass.draw(18, instances);
      }
      if (opts.lineAlpha > 0) {
        pass.setPipeline(this.linesPipeline);
        pass.draw(12, instances);
      }
      if (opts.textAlpha > 0) {
        pass.setPipeline(this.textPipeline);
        pass.draw(6, instances);
      }
      if (opts.cursorValid) {
        pass.setPipeline(this.cursorPipeline);
        pass.draw(12, 1);
      }
    }

    pass.end();
    this.device.queue.submit([encoder.finish()]);
  }

  destroy(): void {
    this.glyphTexture.destroy();
    this.backdropTexture?.destroy();
    this.uniformBuffer.destroy();
    this.cellBuffer.destroy();
  }
}

export async function createRenderer(canvas: HTMLCanvasElement): Promise<Renderer> {
  if (!navigator.gpu) throw new Error('WebGPU not supported in this browser');
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) throw new Error('No WebGPU adapter found');
  const device = await adapter.requestDevice();
  const context = canvas.getContext('webgpu');
  if (!context) throw new Error('Failed to get WebGPU context');
  return new Renderer(canvas, device, context);
}
