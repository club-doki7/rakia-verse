import { neighbours } from './hex.ts';

export const MAGIC = 0x07210d00;
const HEADER_BYTES = 8;

export interface Patch {
  index: number;
  before: number;
  after: number;
}

export class HexGrid {
  readonly cols: number;
  readonly rows: number;
  readonly ids: Uint8Array;
  /** Bumped on every mutation so the renderer knows when to re-upload. */
  revision = 0;

  constructor(cols: number, rows: number, ids?: Uint8Array) {
    this.cols = cols;
    this.rows = rows;
    this.ids = ids ?? new Uint8Array(cols * rows);
  }

  contains(col: number, row: number): boolean {
    return col >= 0 && row >= 0 && col < this.cols && row < this.rows;
  }

  indexOf(col: number, row: number): number {
    return row * this.cols + col;
  }

  get(col: number, row: number): number {
    return this.contains(col, row) ? this.ids[this.indexOf(col, row)] : 0;
  }

  /** Writes one cell, returning the patch when the value actually changed. */
  set(col: number, row: number, id: number): Patch | null {
    if (!this.contains(col, row)) return null;
    const index = this.indexOf(col, row);
    const before = this.ids[index];
    if (before === id) return null;
    this.ids[index] = id;
    this.revision++;
    return { index, before, after: id };
  }

  apply(patches: readonly Patch[], direction: 'redo' | 'undo'): void {
    for (const p of patches) this.ids[p.index] = direction === 'redo' ? p.after : p.before;
    this.revision++;
  }

  /** Flood fill over the connected region sharing the seed's id. */
  fill(col: number, row: number, id: number): Patch[] {
    if (!this.contains(col, row)) return [];
    const target = this.get(col, row);
    if (target === id) return [];

    const patches: Patch[] = [];
    const seen = new Uint8Array(this.cols * this.rows);
    const stack: [number, number][] = [[col, row]];
    seen[this.indexOf(col, row)] = 1;

    while (stack.length > 0) {
      const [c, r] = stack.pop()!;
      const patch = this.set(c, r, id);
      if (patch) patches.push(patch);
      for (const [nc, nr] of neighbours(c, r)) {
        if (!this.contains(nc, nr)) continue;
        const ni = this.indexOf(nc, nr);
        if (seen[ni] === 1 || this.ids[ni] !== target) continue;
        seen[ni] = 1;
        stack.push([nc, nr]);
      }
    }
    return patches;
  }

  serialize(): Uint8Array<ArrayBuffer> {
    const buffer = new ArrayBuffer(HEADER_BYTES + this.ids.length);
    const out = new Uint8Array(buffer);
    const view = new DataView(buffer);
    view.setUint32(0, MAGIC, false);
    view.setUint16(4, this.cols, true);
    view.setUint16(6, this.rows, true);
    out.set(this.ids, HEADER_BYTES);
    return out;
  }

  static deserialize(bytes: Uint8Array): HexGrid {
    if (bytes.length < HEADER_BYTES) throw new Error('File too short to be a maped grid');
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (view.getUint32(0, false) !== MAGIC) throw new Error('Bad magic; not a maped grid file');
    const cols = view.getUint16(4, true);
    const rows = view.getUint16(6, true);
    const expected = cols * rows;
    if (bytes.length - HEADER_BYTES < expected) throw new Error('Truncated grid payload');
    return new HexGrid(cols, rows, bytes.slice(HEADER_BYTES, HEADER_BYTES + expected));
  }
}

export class History {
  private readonly undoStack: Patch[][] = [];
  private readonly redoStack: Patch[][] = [];
  private readonly limit: number;
  private pending: Patch[] = [];

  constructor(limit = 256) {
    this.limit = limit;
  }

  record(patches: readonly Patch[]): void {
    this.pending.push(...patches);
  }

  /** Seals the patches recorded since the last commit into one undoable step. */
  commit(): boolean {
    if (this.pending.length === 0) return false;
    this.undoStack.push(this.pending);
    this.pending = [];
    this.redoStack.length = 0;
    if (this.undoStack.length > this.limit) this.undoStack.shift();
    return true;
  }

  undo(grid: HexGrid): boolean {
    const step = this.undoStack.pop();
    if (!step) return false;
    grid.apply(step, 'undo');
    this.redoStack.push(step);
    return true;
  }

  redo(grid: HexGrid): boolean {
    const step = this.redoStack.pop();
    if (!step) return false;
    grid.apply(step, 'redo');
    this.undoStack.push(step);
    return true;
  }

  clear(): void {
    this.undoStack.length = 0;
    this.redoStack.length = 0;
    this.pending = [];
  }
}
