struct Uniforms {
  // pan.xy (world px), zoom (device px per world px), glyph alpha
  panZoom: vec4f,
  // viewport.xy (device px), backdrop size (world px)
  viewport: vec4f,
  // cols, visible cols, min visible col, min visible row
  extent: vec4i,
  // fill alpha, line alpha, backdrop alpha, unused
  style: vec4f,
  // hovered col, hovered row, valid flag, unused
  cursor: vec4i,
}

const SIDE: f32 = 10.0;
const SQRT3: f32 = 1.7320508;
const HEX_W: f32 = SQRT3 * SIDE;
const ROW_H: f32 = 1.5 * SIDE;
const ORIGIN = vec2f(HEX_W * 0.5, SIDE);
const SIXTH: f32 = 1.0471976;
const OFFSCREEN = vec4f(0.0, 0.0, 2.0, 1.0);
const GLYPH_HALF = vec2f(8.0, 4.0);

var<private> QUAD = array<vec2f, 6>(
  vec2f(0.0, 0.0), vec2f(1.0, 0.0), vec2f(0.0, 1.0),
  vec2f(1.0, 0.0), vec2f(1.0, 1.0), vec2f(0.0, 1.0),
);

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var<storage, read> cells: array<u32>;
@group(0) @binding(2) var glyphTex: texture_2d<f32>;
@group(0) @binding(3) var texSampler: sampler;

@group(1) @binding(0) var backdropTex: texture_2d<f32>;

var<private> PALETTE = array<vec3f, 16>(
  vec3f(1.000, 0.000, 0.000), vec3f(0.000, 1.000, 0.000),
  vec3f(1.000, 0.867, 0.000), vec3f(0.000, 0.000, 1.000),
  vec3f(1.000, 0.498, 0.000), vec3f(0.498, 0.000, 1.000),
  vec3f(0.000, 0.498, 1.000), vec3f(1.000, 0.000, 1.000),
  vec3f(0.000, 0.498, 0.000), vec3f(0.498, 0.000, 0.000),
  vec3f(0.000, 0.000, 0.498), vec3f(0.000, 1.000, 1.000),
  vec3f(1.000, 0.000, 0.498), vec3f(0.498, 0.498, 0.000),
  vec3f(0.000, 0.498, 0.498), vec3f(0.498, 0.000, 0.498),
);

fn cellCenter(col: i32, row: i32) -> vec2f {
  let odd = f32(row & 1) * 0.5;
  return ORIGIN + vec2f(HEX_W * (f32(col) + odd), ROW_H * f32(row));
}

fn corner(k: f32) -> vec2f {
  let a = k * SIXTH;
  return vec2f(sin(a), cos(a)) * SIDE;
}

fn toClip(world: vec2f) -> vec4f {
  let screen = (world - u.panZoom.xy) * u.panZoom.z;
  let ndc = screen / u.viewport.xy * 2.0 - 1.0;
  return vec4f(ndc.x, -ndc.y, 0.0, 1.0);
}

/** Unpacks the 8-bit id stored for a linear cell index. */
fn idAt(index: i32) -> u32 {
  let word = cells[u32(index) >> 2u];
  return (word >> ((u32(index) & 3u) * 8u)) & 0xffu;
}

fn visibleCell(instance: u32) -> vec2i {
  let visCols = u.extent.y;
  let i = i32(instance);
  return vec2i(u.extent.z + i % visCols, u.extent.w + i / visCols);
}

struct FillOut {
  @builtin(position) pos: vec4f,
  @location(0) color: vec4f,
}

@vertex
fn vsFill(@builtin(vertex_index) vi: u32, @builtin(instance_index) inst: u32) -> FillOut {
  var out: FillOut;
  let cell = visibleCell(inst);
  let id = idAt(cell.y * u.extent.x + cell.x);
  if (id == 0u) {
    out.pos = OFFSCREEN;
    out.color = vec4f(0.0);
    return out;
  }
  let tri = vi / 3u;
  let vert = vi % 3u;
  var local = vec2f(0.0);
  if (vert > 0u) {
    local = corner(f32(tri + vert - 1u));
  }
  out.pos = toClip(cellCenter(cell.x, cell.y) + local);
  out.color = vec4f(PALETTE[(id - 1u) & 15u], u.style.x);
  return out;
}

@fragment
fn fsFill(in: FillOut) -> @location(0) vec4f {
  return vec4f(in.color.rgb * in.color.a, in.color.a);
}

@vertex
fn vsLines(@builtin(vertex_index) vi: u32, @builtin(instance_index) inst: u32) -> @builtin(position) vec4f {
  let cell = visibleCell(inst);
  let k = f32(vi / 2u + vi % 2u);
  return toClip(cellCenter(cell.x, cell.y) + corner(k));
}

@fragment
fn fsLines() -> @location(0) vec4f {
  let a = u.style.y;
  return vec4f(vec3f(0.62) * a, a);
}

@vertex
fn vsCursor(@builtin(vertex_index) vi: u32) -> @builtin(position) vec4f {
  if (u.cursor.z == 0) {
    return OFFSCREEN;
  }
  let local = corner(f32(vi / 2u + vi % 2u)) * 1.08;
  return toClip(cellCenter(u.cursor.x, u.cursor.y) + local);
}

@fragment
fn fsCursor() -> @location(0) vec4f {
  return vec4f(1.0, 0.95, 0.4, 1.0);
}

struct TextOut {
  @builtin(position) pos: vec4f,
  @location(0) uv: vec2f,
  @location(1) tint: vec4f,
}

@vertex
fn vsText(@builtin(vertex_index) vi: u32, @builtin(instance_index) inst: u32) -> TextOut {
  var out: TextOut;
  let cell = visibleCell(inst);
  let id = idAt(cell.y * u.extent.x + cell.x);
  if (id == 0u || u.panZoom.w <= 0.0) {
    out.pos = OFFSCREEN;
    out.uv = vec2f(0.0);
    out.tint = vec4f(0.0);
    return out;
  }
  let q = QUAD[vi];
  let world = cellCenter(cell.x, cell.y) + (q * 2.0 - 1.0) * GLYPH_HALF;
  let tile = vec2f(f32(id % 16u), f32(id / 16u));
  let rgb = PALETTE[(id - 1u) & 15u];
  let luma = dot(rgb, vec3f(0.299, 0.587, 0.114));
  out.pos = toClip(world);
  out.uv = (tile + q) / 16.0;
  out.tint = vec4f(vec3f(select(1.0, 0.0, luma > 0.55)), u.panZoom.w);
  return out;
}

@fragment
fn fsText(in: TextOut) -> @location(0) vec4f {
  let a = textureSample(glyphTex, texSampler, in.uv).a * in.tint.a;
  return vec4f(in.tint.rgb * a, a);
}

struct BackdropOut {
  @builtin(position) pos: vec4f,
  @location(0) uv: vec2f,
}

@vertex
fn vsBackdrop(@builtin(vertex_index) vi: u32) -> BackdropOut {
  var out: BackdropOut;
  let q = QUAD[vi];
  out.pos = toClip(q * u.viewport.zw);
  out.uv = q;
  return out;
}

@fragment
fn fsBackdrop(in: BackdropOut) -> @location(0) vec4f {
  let c = textureSample(backdropTex, texSampler, in.uv);
  return vec4f(c.rgb * c.a * u.style.z, c.a * u.style.z);
}
