// Pointy-top ("tip-up") hex grid, odd-r offset storage.
// Cell coordinates stay integer; conversion to pixels happens only at draw/hit-test time.

export const SIDE = 10;
export const SQRT3 = Math.sqrt(3);
export const HEX_W = SQRT3 * SIDE; // horizontal distance between column centers
export const ROW_H = 1.5 * SIDE; // vertical distance between row centers
export const ORIGIN_X = HEX_W / 2;
export const ORIGIN_Y = SIDE;

export function gridSizeFor(pixelW: number, pixelH: number): [number, number] {
  const cols = Math.max(1, Math.ceil(pixelW / HEX_W));
  const rows = Math.max(1, Math.ceil(pixelH / ROW_H));
  return [cols, rows];
}

export function cellCenter(col: number, row: number): [number, number] {
  return [ORIGIN_X + HEX_W * (col + 0.5 * (row & 1)), ORIGIN_Y + ROW_H * row];
}

/** World pixel -> odd-r offset cell. Returns null when outside the grid. */
export function pixelToCell(
  x: number,
  y: number,
  cols: number,
  rows: number,
): [number, number] | null {
  const px = x - ORIGIN_X;
  const py = y - ORIGIN_Y;
  const fq = ((SQRT3 / 3) * px - py / 3) / SIDE;
  const fr = ((2 / 3) * py) / SIDE;
  const [q, r] = axialRound(fq, fr);
  const col = q + ((r - (r & 1)) >> 1);
  if (col < 0 || r < 0 || col >= cols || r >= rows) return null;
  return [col, r];
}

function axialRound(fq: number, fr: number): [number, number] {
  const fs = -fq - fr;
  let q = Math.round(fq);
  let r = Math.round(fr);
  const s = Math.round(fs);
  const dq = Math.abs(q - fq);
  const dr = Math.abs(r - fr);
  const ds = Math.abs(s - fs);
  if (dq > dr && dq > ds) q = -r - s;
  else if (dr > ds) r = -q - s;
  return [q, r];
}

/** Odd-r neighbours, in axial-equivalent order. */
export function neighbours(col: number, row: number): [number, number][] {
  const odd = row & 1;
  const dx = odd ? 1 : 0;
  return [
    [col + 1, row],
    [col - 1 + dx, row - 1],
    [col + dx, row - 1],
    [col - 1, row],
    [col - 1 + dx, row + 1],
    [col + dx, row + 1],
  ];
}
