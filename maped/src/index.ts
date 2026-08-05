import './style.css';
import { createRenderer, type RenderOpts } from './renderer.ts';
import { HexGrid, History } from './grid.ts';
import { pixelToCell, gridSizeFor } from './hex.ts';
import { colorOf } from './palette.ts';

const canvas = document.getElementById('canvas') as HTMLCanvasElement;
const brushInput = document.getElementById('brushId') as HTMLInputElement;
const statusSpan = document.getElementById('status') as HTMLSpanElement;
const bucketButton = document.getElementById('bucket') as HTMLButtonElement;
const eyedropperButton = document.getElementById('eyedropper') as HTMLButtonElement;
const fillAlphaInput = document.getElementById('fillAlpha') as HTMLInputElement;

let grid = new HexGrid(260, 284);
const history = new History();

const state = {
  panX: 0,
  panY: 0,
  zoom: 1,
  fillAlpha: 0.5,
  lineAlpha: 0.8,
  textAlpha: 1,
  backdropAlpha: 1.0,
  cursorCol: -1,
  cursorRow: -1,
  cursorValid: false,
  brushId: 1,
  painting: false,
  panning: false,
  panStartX: 0,
  panStartY: 0,
  eyedropperMode: false,
  bucketMode: false,
};

let renderer: Awaited<ReturnType<typeof createRenderer>>;

function syncToolButtons() {
  bucketButton.classList.toggle('active', state.bucketMode);
  bucketButton.setAttribute('aria-pressed', String(state.bucketMode));
  eyedropperButton.classList.toggle('active', state.eyedropperMode);
  eyedropperButton.setAttribute('aria-pressed', String(state.eyedropperMode));
  canvas.classList.toggle('bucket', state.bucketMode);
}

async function init() {
  try {
    renderer = await createRenderer(canvas);
    requestAnimationFrame(render);
    statusSpan.textContent = `Grid: ${grid.cols}×${grid.rows}`;
  } catch (e) {
    statusSpan.textContent = `Error: ${e instanceof Error ? e.message : String(e)}`;
    console.error(e);
  }
}

function render() {
  const opts: RenderOpts = {
    panX: state.panX,
    panY: state.panY,
    zoom: state.zoom,
    fillAlpha: state.fillAlpha,
    lineAlpha: state.lineAlpha,
    textAlpha: state.textAlpha,
    backdropAlpha: state.backdropAlpha,
    cursorCol: state.cursorCol,
    cursorRow: state.cursorRow,
    cursorValid: state.cursorValid,
  };
  renderer.render(grid, opts);
  requestAnimationFrame(render);
}

function screenToWorld(clientX: number, clientY: number): [number, number] {
  const rect = canvas.getBoundingClientRect();
  const sx = (clientX - rect.left) * (canvas.width / rect.width);
  const sy = (clientY - rect.top) * (canvas.height / rect.height);
  return [state.panX + sx / state.zoom, state.panY + sy / state.zoom];
}

canvas.addEventListener('pointermove', (e) => {
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  const cell = pixelToCell(wx, wy, grid.cols, grid.rows);
  if (cell) {
    const [col, row] = cell;
    state.cursorCol = col;
    state.cursorRow = row;
    state.cursorValid = true;
    const id = grid.get(col, row);
    statusSpan.textContent = `[${col}, ${row}] ID=${id}`;
  } else {
    state.cursorValid = false;
    statusSpan.textContent = `Grid: ${grid.cols}×${grid.rows}`;
  }

  if (state.painting && cell && (e.buttons & 1 || e.buttons & 2)) {
    const [col, row] = cell;
    const targetId = e.buttons & 2 ? 0 : state.brushId;
    const patch = grid.set(col, row, targetId);
    if (patch) history.record([patch]);
  }

  if (state.panning && (e.buttons & 4)) {
    const dx = e.clientX - state.panStartX;
    const dy = e.clientY - state.panStartY;
    state.panX -= dx / state.zoom;
    state.panY -= dy / state.zoom;
    state.panStartX = e.clientX;
    state.panStartY = e.clientY;
  }
});

canvas.addEventListener('pointerdown', (e) => {
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  const cell = pixelToCell(wx, wy, grid.cols, grid.rows);

  if (e.button === 0 && cell) {
    const [col, row] = cell;
    if (state.eyedropperMode) {
      const id = grid.get(col, row);
      if (id > 0) {
        state.brushId = id;
        brushInput.value = String(id);
        brushInput.dispatchEvent(new Event('input'));
      }
      state.eyedropperMode = false;
      syncToolButtons();
      return;
    }
    if (state.bucketMode) {
      const patches = grid.fill(col, row, state.brushId);
      history.record(patches);
      history.commit();
      return;
    }
    state.painting = true;
    const patch = grid.set(col, row, state.brushId);
    if (patch) history.record([patch]);
  } else if (e.button === 2 && cell) {
    state.painting = true;
    const [col, row] = cell;
    const patch = grid.set(col, row, 0);
    if (patch) history.record([patch]);
  } else if (e.button === 1) {
    e.preventDefault();
    state.panning = true;
    state.panStartX = e.clientX;
    state.panStartY = e.clientY;
  }
});

canvas.addEventListener('pointerup', (e) => {
  if (e.button === 0 || e.button === 2) {
    if (state.painting) {
      history.commit();
      state.painting = false;
    }
  } else if (e.button === 1) {
    state.panning = false;
  }
});

canvas.addEventListener('contextmenu', (e) => e.preventDefault());

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  state.zoom = Math.max(0.1, Math.min(10, state.zoom * factor));
  const [wx2, wy2] = screenToWorld(e.clientX, e.clientY);
  state.panX += wx - wx2;
  state.panY += wy - wy2;
});

brushInput.addEventListener('input', () => {
  const val = parseInt(brushInput.value, 10);
  if (val >= 1 && val <= 255) {
    state.brushId = val;
    brushInput.style.backgroundColor = colorOf(val);
  }
});
brushInput.dispatchEvent(new Event('input'));

fillAlphaInput.addEventListener('input', () => {
  state.fillAlpha = parseInt(fillAlphaInput.value, 10) / 100;
});

eyedropperButton.addEventListener('click', () => {
  state.eyedropperMode = !state.eyedropperMode;
  state.bucketMode = false;
  syncToolButtons();
});

bucketButton.addEventListener('click', () => {
  state.bucketMode = !state.bucketMode;
  state.eyedropperMode = false;
  syncToolButtons();
});

syncToolButtons();

document.getElementById('undo')!.addEventListener('click', () => {
  history.undo(grid);
});

document.getElementById('redo')!.addEventListener('click', () => {
  history.redo(grid);
});

document.getElementById('clear')!.addEventListener('click', () => {
  if (confirm('Clear the entire grid?')) {
    grid.ids.fill(0);
    grid.revision++;
    history.clear();
  }
});

document.getElementById('save')!.addEventListener('click', () => {
  const blob = new Blob([grid.serialize()], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `grid_${grid.cols}x${grid.rows}.maped`;
  a.click();
  URL.revokeObjectURL(url);
});

document.getElementById('load')!.addEventListener('click', () => {
  (document.getElementById('loadFile') as HTMLInputElement).click();
});

document.getElementById('loadFile')!.addEventListener('change', async (e) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const buf = await file.arrayBuffer();
  try {
    grid = HexGrid.deserialize(new Uint8Array(buf));
    grid.revision = renderer.lastRevision + 1;
    history.clear();
    statusSpan.textContent = `Loaded ${grid.cols}×${grid.rows}`;
  } catch (err) {
    alert(`Failed to load: ${err instanceof Error ? err.message : String(err)}`);
  }
});

document.getElementById('backdrop')!.addEventListener('change', async (e) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) {
    renderer.setBackdrop(null);
    return;
  }
  const bmp = await createImageBitmap(file);
  renderer.setBackdrop(bmp);
  const [cols, rows] = gridSizeFor(bmp.width, bmp.height);
  if (cols !== grid.cols || rows !== grid.rows) {
    if (confirm(`Backdrop is ${bmp.width}×${bmp.height}. Resize grid to ${cols}×${rows}?`)) {
      grid = new HexGrid(cols, rows);
      history.clear();
      statusSpan.textContent = `Resized to ${cols}×${rows}`;
    }
  }
});

window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
    e.preventDefault();
    history.undo(grid);
  } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
    e.preventDefault();
    history.redo(grid);
  } else if (e.key === ' ' && !state.panning) {
    e.preventDefault();
  } else if (e.key === 'Escape' && (state.bucketMode || state.eyedropperMode)) {
    state.bucketMode = false;
    state.eyedropperMode = false;
    syncToolButtons();
  }
});

init();
