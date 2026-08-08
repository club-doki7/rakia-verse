// Pre-renders the numbers 1..255 into one offscreen 2D canvas, uploaded as a WebGPU texture.

export const TILE_W = 64;
export const TILE_H = 32;
export const ATLAS_COLS = 16;
export const ATLAS_ROWS = 16;
export const ATLAS_W = TILE_W * ATLAS_COLS;
export const ATLAS_H = TILE_H * ATLAS_ROWS;

export function buildGlyphAtlas(): OffscreenCanvas {
  const canvas = new OffscreenCanvas(ATLAS_W, ATLAS_H);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('2D context unavailable for the glyph atlas');

  ctx.clearRect(0, 0, ATLAS_W, ATLAS_H);
  ctx.font = `600 ${TILE_H - 10}px ui-monospace, "Cascadia Mono", Consolas, monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ffffff';

  for (let id = 1; id <= 255; id++) {
    const cx = (id % ATLAS_COLS) * TILE_W + TILE_W / 2;
    const cy = Math.floor(id / ATLAS_COLS) * TILE_H + TILE_H / 2;
    ctx.fillText(String(id), cx, cy, TILE_W - 6);
  }
  return canvas;
}
