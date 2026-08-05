// 16 preset colours, cycled by (id - 1) % 16.
export const PALETTE: readonly string[] = [
  '#ff0000',
  '#00ff00',
  '#ffdd00',
  '#0000ff',
  '#ff7f00',
  '#7f00ff',
  '#007fff',
  '#ff00ff',
  '#007f00',
  '#7f0000',
  '#00007f',
  '#00ffff',
  '#ff007f',
  '#7f7f00',
  '#007f7f',
  '#7f007f',
];

/** RGB in 0..255, indexed by palette slot. */
export const PALETTE_RGB: readonly [number, number, number][] = PALETTE.map((hex) => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
]);

export function slotOf(id: number): number {
  return (id - 1) & 15;
}

export function colorOf(id: number): string {
  return PALETTE[slotOf(id)];
}
