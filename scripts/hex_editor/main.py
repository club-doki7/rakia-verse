"""
Hex Grid Map Editor
- pygame window + moderngl GPU rendering (instanced)
- Load map-terrain.png as background
- Pan (middle-drag or right-drag), zoom (scroll)
- Left click: paint color1, Shift+Left: paint color2
- Number keys 1-9, 0: select palette colors 1-9 (0 maps to slot 9)
- QWERTY keys Q W E R T Y: select palette colors 10-15
- S: save, L: load
- No MSAA
"""

import os
import sys
import math
import struct

import numpy as np
import pygame
import moderngl
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from hex_model import HexGrid, hex_pixel_center, pixel_to_hex, compute_grid_size, SIDE, HEX_W_EXACT, ROW_STEP

# --- Config ---
WINDOW_W, WINDOW_H = 1280, 720
MAP_W, MAP_H = 9000, 8508
BG_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "map-terrain.png")
SAVE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "hex_grid_data.json")

PALETTE = [
    (0, 0, 0),        # 0: reserved empty (not selectable via keys)
    (255, 0, 0),      # 1
    (0, 255, 0),      # 2
    (0, 128, 255),    # 3
    (255, 255, 0),    # 4
    (255, 128, 0),    # 5
    (128, 0, 255),    # 6
    (0, 255, 255),    # 7
    (255, 0, 255),    # 8
    (128, 128, 128),  # 9 (key 0)
    (192, 64, 0),     # 10 (key Q)
    (0, 192, 128),    # 11 (key W)
    (64, 64, 255),    # 12 (key E)
    (255, 192, 128),  # 13 (key R)
    (128, 255, 128),  # 14 (key T)
    (192, 128, 255),  # 15 (key Y)
]

# QWERTY row maps to palette indices 10-15
QWERTY_KEY_MAP = {
    pygame.K_q: 10,
    pygame.K_w: 11,
    pygame.K_e: 12,
    pygame.K_r: 13,
    pygame.K_t: 14,
    pygame.K_y: 15,
}

# --- Shaders ---
VERTEX_SHADER_BG = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
uniform mat4 u_proj;
void main() {
    gl_Position = u_proj * vec4(in_pos, 0.0, 1.0);
    v_uv = in_uv;
}
"""

FRAGMENT_SHADER_BG = """
#version 330
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_tex;
void main() {
    fragColor = texture(u_tex, v_uv);
}
"""

VERTEX_SHADER_HEX = """
#version 330
// Per-vertex (hex shape)
in vec2 in_vert;
// Per-instance
in vec2 in_center;   // pixel center of hex
in vec3 in_color1;   // normalized rgb
in vec3 in_color2;

out vec3 v_color1;
out vec3 v_color2;
out vec2 v_local;    // local position within hex for split rendering

uniform mat4 u_proj;

void main() {
    vec2 world_pos = in_center + in_vert;
    gl_Position = u_proj * vec4(world_pos, 0.0, 1.0);
    v_color1 = in_color1;
    v_color2 = in_color2;
    v_local = in_vert;
}
"""

FRAGMENT_SHADER_HEX = """
#version 330
in vec3 v_color1;
in vec3 v_color2;
in vec2 v_local;
out vec4 fragColor;

void main() {
    // Skip empty cells
    if (v_color1 == vec3(0.0) && v_color2 == vec3(0.0)) discard;

    vec3 c;
    if (v_color2 == vec3(0.0)) {
        // Only color1 set: fill entire cell
        c = v_color1;
    } else {
        // Both set: color1 takes ~2/3 area (shift split line toward color2 side)
        float split = v_local.x + v_local.y;
        if (split < 5.0) {
            c = v_color1;
        } else {
            c = v_color2;
        }
    }
    fragColor = vec4(c, 0.6);
}
"""

VERTEX_SHADER_GRID = """
#version 330
in vec2 in_vert;
in vec2 in_center;
uniform mat4 u_proj;
void main() {
    vec2 world_pos = in_center + in_vert;
    gl_Position = u_proj * vec4(world_pos, 0.0, 1.0);
}
"""

FRAGMENT_SHADER_GRID = """
#version 330
out vec4 fragColor;
uniform vec4 u_line_color;
void main() {
    fragColor = u_line_color;
}
"""

# HUD overlay shaders (screen-space)
VERTEX_SHADER_HUD = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    v_uv = in_uv;
}
"""

FRAGMENT_SHADER_HUD = """
#version 330
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_tex;
void main() {
    fragColor = texture(u_tex, v_uv);
}
"""


def make_hex_vertices(side: float) -> np.ndarray:
    """Generate 6 vertices for a tip-up hex centered at origin."""
    verts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        verts.append((side * math.cos(angle), side * math.sin(angle)))
    return np.array(verts, dtype="f4")


def make_hex_triangles(side: float) -> np.ndarray:
    """Triangle fan from center (0,0) for filled hex. 6 triangles."""
    verts = make_hex_vertices(side)
    center = np.array([0.0, 0.0], dtype="f4")
    tris = []
    for i in range(6):
        tris.append(center)
        tris.append(verts[i])
        tris.append(verts[(i + 1) % 6])
    return np.array(tris, dtype="f4")


def make_hex_line_verts(side: float) -> np.ndarray:
    """Line loop vertices for hex outline."""
    verts = make_hex_vertices(side)
    # LINE_LOOP: return vertices in order
    return verts


def build_projection(cam_x: float, cam_y: float, zoom: float, win_w: int, win_h: int) -> np.ndarray:
    """Orthographic projection centered on (cam_x, cam_y) with given zoom."""
    hw = (win_w / 2.0) / zoom
    hh = (win_h / 2.0) / zoom
    left = cam_x - hw
    right = cam_x + hw
    bottom = cam_y + hh  # y-down in pixel coords
    top = cam_y - hh

    # Orthographic matrix (column-major for OpenGL)
    proj = np.zeros((4, 4), dtype="f4")
    proj[0, 0] = 2.0 / (right - left)
    proj[1, 1] = 2.0 / (top - bottom)
    proj[2, 2] = -1.0
    proj[3, 0] = -(right + left) / (right - left)
    proj[3, 1] = -(top + bottom) / (top - bottom)
    proj[3, 3] = 1.0
    return proj


class HexEditor:
    def __init__(self, save_path: str = SAVE_PATH):
        self.save_path = save_path
        pygame.init()
        pygame.key.stop_text_input()
        pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption("Hex Grid Editor - " + SAVE_PATH)

        # moderngl context - no MSAA
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # Camera state
        self.cam_x = MAP_W / 2.0
        self.cam_y = MAP_H / 2.0
        self.zoom = 0.1  # start zoomed out
        self.win_w = WINDOW_W
        self.win_h = WINDOW_H

        # Grid data
        cols, rows = compute_grid_size(MAP_W, MAP_H)
        self.grid = HexGrid(cols, rows)
        print(f"Grid: {cols} x {rows} = {cols * rows} cells")

        # Current paint state
        self.current_color_idx = 1
        self.painting = False
        self.erasing = False
        self.paint_layer = 1  # 1 or 2
        self.hover_col = -1
        self.hover_row = -1

        # Setup rendering resources
        self._setup_background()
        self._setup_hex_rendering()
        self._setup_grid_lines()
        self._setup_hud()

        # Instance buffer needs rebuild when colors change
        self._instance_dirty = True

    def _setup_background(self):
        """Load background image as texture and create quad."""
        self.bg_prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER_BG,
            fragment_shader=FRAGMENT_SHADER_BG,
        )

        # Load image
        if os.path.exists(BG_IMAGE_PATH):
            img = Image.open(BG_IMAGE_PATH).convert("RGBA")
            self.bg_tex = self.ctx.texture(img.size, 4, img.tobytes())
            self.bg_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        else:
            # Fallback: 1x1 white texture
            self.bg_tex = self.ctx.texture((1, 1), 4, b"\xff\xff\xff\xff")
            print(f"Warning: background not found at {BG_IMAGE_PATH}")

        # Full-map quad (2 triangles)
        quad = np.array([
            # pos(x,y), uv(u,v)
            0, 0, 0, 0,
            MAP_W, 0, 1, 0,
            MAP_W, MAP_H, 1, 1,
            0, 0, 0, 0,
            MAP_W, MAP_H, 1, 1,
            0, MAP_H, 0, 1,
        ], dtype="f4")
        vbo = self.ctx.buffer(quad.tobytes())
        self.bg_vao = self.ctx.vertex_array(self.bg_prog, [(vbo, "2f 2f", "in_pos", "in_uv")])

    def _setup_hex_rendering(self):
        """Setup instanced hex fill rendering."""
        self.hex_prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER_HEX,
            fragment_shader=FRAGMENT_SHADER_HEX,
        )

        # Hex triangle geometry (per-vertex)
        tri_verts = make_hex_triangles(SIDE)
        self.hex_vbo = self.ctx.buffer(tri_verts.tobytes())

        # Instance buffer - will be rebuilt when dirty
        self.hex_instance_buf = None
        self.hex_vao = None
        self.instance_count = 0

    def _setup_grid_lines(self):
        """Setup instanced hex outline rendering."""
        self.grid_prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER_GRID,
            fragment_shader=FRAGMENT_SHADER_GRID,
        )

        # Hex outline vertices
        line_verts = make_hex_line_verts(SIDE)
        self.grid_vbo = self.ctx.buffer(line_verts.tobytes())

        # Instance buffer for grid (just centers)
        self.grid_instance_buf = None
        self.grid_vao = None
        self._grid_dirty = True

    def _setup_hud(self):
        """Setup HUD overlay: pygame Surface -> GL texture -> fullscreen quad."""
        self.hud_prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER_HUD,
            fragment_shader=FRAGMENT_SHADER_HUD,
        )
        # Fullscreen quad in NDC (covers entire screen)
        quad = np.array([
            -1, -1, 0, 0,
             1, -1, 1, 0,
             1,  1, 1, 1,
            -1, -1, 0, 0,
             1,  1, 1, 1,
            -1,  1, 0, 1,
        ], dtype="f4")
        vbo = self.ctx.buffer(quad.tobytes())
        self.hud_vao = self.ctx.vertex_array(self.hud_prog, [(vbo, "2f 2f", "in_pos", "in_uv")])
        # Create a pygame surface for HUD drawing
        self.hud_surface = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        self.hud_tex = self.ctx.texture((self.win_w, self.win_h), 4)
        self.hud_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._hud_dirty = True

    def _rebuild_hud(self):
        """Redraw HUD surface with palette and status info."""
        if self.hud_surface.get_size() != (self.win_w, self.win_h):
            self.hud_surface = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
            self.hud_tex.release()
            self.hud_tex = self.ctx.texture((self.win_w, self.win_h), 4)
            self.hud_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)

        self.hud_surface.fill((0, 0, 0, 0))

        # Draw palette swatches at top-left (two rows: 1-9 number keys, 10-15 QWERTY)
        swatch_size = 24
        margin = 4
        x0, y0 = 10, 10
        font = pygame.font.SysFont(None, 16)
        key_labels = ["", "1", "2", "3", "4", "5", "6", "7", "8", "0", "Q", "W", "E", "R", "T", "Y"]

        for i in range(1, len(PALETTE)):
            row_offset = 0 if i <= 9 else (swatch_size + margin + 12)
            col_idx = (i - 1) if i <= 9 else (i - 10)
            x = x0 + col_idx * (swatch_size + margin)
            y = y0 + row_offset
            color = PALETTE[i]
            pygame.draw.rect(self.hud_surface, color, (x, y, swatch_size, swatch_size))
            if i == self.current_color_idx:
                pygame.draw.rect(self.hud_surface, (255, 255, 255), (x - 2, y - 2, swatch_size + 4, swatch_size + 4), 2)
            # Key label below swatch
            lbl = font.render(key_labels[i], True, (200, 200, 200))
            self.hud_surface.blit(lbl, (x + swatch_size // 2 - lbl.get_width() // 2, y + swatch_size + 1))

        # Status text
        status_font = pygame.font.SysFont(None, 20)
        status_y = y0 + 2 * (swatch_size + margin + 12) + 4
        layer_txt = f"Layer: {self.paint_layer}  Zoom: {self.zoom:.2f}"
        txt_surf = status_font.render(layer_txt, True, (255, 255, 255))
        self.hud_surface.blit(txt_surf, (x0, status_y))

        # Hover coordinate
        if self.hover_col >= 0 and self.hover_row >= 0:
            coord_txt = f"Hex: ({self.hover_col}, {self.hover_row})"
            # Black text with white outline
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        outline_surf = status_font.render(coord_txt, True, (255, 255, 255))
                        self.hud_surface.blit(outline_surf, (x0 + dx, status_y + 20 + dy))
            coord_surf = status_font.render(coord_txt, True, (0, 0, 0))
            self.hud_surface.blit(coord_surf, (x0, status_y + 20))

        # Upload to texture (flip vertically for OpenGL)
        flipped = pygame.transform.flip(self.hud_surface, False, True)
        raw = pygame.image.tobytes(flipped, "RGBA")
        self.hud_tex.write(raw)
        self._hud_dirty = False

    def _rebuild_visible_instances(self):
        """Rebuild instance buffers for currently visible cells only."""
        # Determine visible region in world coords
        hw = (self.win_w / 2.0) / self.zoom
        hh = (self.win_h / 2.0) / self.zoom
        left = self.cam_x - hw - SIDE
        right = self.cam_x + hw + SIDE
        top = self.cam_y - hh - SIDE
        bottom = self.cam_y + hh + SIDE

        # Convert to row/col range
        row_min = max(0, int(top / ROW_STEP) - 1)
        row_max = min(self.grid.rows - 1, int(bottom / ROW_STEP) + 1)
        col_min = max(0, int(left / HEX_W_EXACT) - 1)
        col_max = min(self.grid.cols - 1, int(right / HEX_W_EXACT) + 1)

        # Build instance data for hex fills (only non-zero cells)
        # Format: center_x, center_y, r1, g1, b1, r2, g2, b2 (all float32)
        hex_instances = []
        grid_centers = []

        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                cx, cy = hex_pixel_center(c, r)
                if cx < left or cx > right or cy < top or cy > bottom:
                    continue
                grid_centers.append((cx, cy))

                i1 = self.grid.idx1[r, c]
                i2 = self.grid.idx2[r, c]
                if i1 or i2:
                    c1 = PALETTE[i1] if i1 < len(PALETTE) else (0, 0, 0)
                    c2 = PALETTE[i2] if i2 < len(PALETTE) else (0, 0, 0)
                    hex_instances.append((
                        cx, cy,
                        c1[0] / 255.0, c1[1] / 255.0, c1[2] / 255.0,
                        c2[0] / 255.0, c2[1] / 255.0, c2[2] / 255.0,
                    ))

        # Hex fill instances
        if hex_instances:
            data = np.array(hex_instances, dtype="f4")
            if self.hex_instance_buf:
                self.hex_instance_buf.release()
            self.hex_instance_buf = self.ctx.buffer(data.tobytes())
            self.instance_count = len(hex_instances)

            self.hex_vao = self.ctx.vertex_array(self.hex_prog, [
                (self.hex_vbo, "2f", "in_vert"),
                (self.hex_instance_buf, "2f 3f 3f /i", "in_center", "in_color1", "in_color2"),
            ])
        else:
            self.instance_count = 0
            self.hex_vao = None

        # Grid line instances
        if grid_centers:
            centers_data = np.array(grid_centers, dtype="f4")
            if self.grid_instance_buf:
                self.grid_instance_buf.release()
            self.grid_instance_buf = self.ctx.buffer(centers_data.tobytes())

            self.grid_vao = self.ctx.vertex_array(self.grid_prog, [
                (self.grid_vbo, "2f", "in_vert"),
                (self.grid_instance_buf, "2f /i", "in_center"),
            ])
            self.grid_line_count = len(grid_centers)
        else:
            self.grid_vao = None
            self.grid_line_count = 0

        self._instance_dirty = False
        self._grid_dirty = False

    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        """Convert screen pixel to world coordinate."""
        hw = (self.win_w / 2.0) / self.zoom
        hh = (self.win_h / 2.0) / self.zoom
        wx = self.cam_x - hw + sx / self.zoom
        wy = self.cam_y - hh + sy / self.zoom
        return wx, wy

    def _paint_at_screen(self, sx: int, sy: int):
        """Paint current color index at screen position."""
        wx, wy = self._screen_to_world(sx, sy)
        col, row = pixel_to_hex(wx, wy)
        if 0 <= col < self.grid.cols and 0 <= row < self.grid.rows:
            if self.paint_layer == 1:
                self.grid.set_idx1(col, row, self.current_color_idx)
            else:
                self.grid.set_idx2(col, row, self.current_color_idx)
            self._instance_dirty = True

    def _erase_at_screen(self, sx: int, sy: int):
        """Erase both colors at screen position."""
        wx, wy = self._screen_to_world(sx, sy)
        col, row = pixel_to_hex(wx, wy)
        if 0 <= col < self.grid.cols and 0 <= row < self.grid.rows:
            self.grid.set_idx1(col, row, 0)
            self.grid.set_idx2(col, row, 0)
            self._instance_dirty = True

    def run(self):
        clock = pygame.time.Clock()
        running = True
        dragging = False
        drag_start = (0, 0)
        cam_start = (0.0, 0.0)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE:
                    self.win_w, self.win_h = event.w, event.h
                    self.ctx.viewport = (0, 0, self.win_w, self.win_h)
                    self._instance_dirty = True
                    self._hud_dirty = True

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click - paint
                        self.painting = True
                        self._paint_at_screen(*event.pos)
                    elif event.button == 3:  # Right click - eraser
                        self.erasing = True
                        self._erase_at_screen(*event.pos)
                    elif event.button == 2:  # Middle - pan
                        dragging = True
                        drag_start = event.pos
                        cam_start = (self.cam_x, self.cam_y)
                    elif event.button == 4:  # Scroll up - zoom in
                        self.zoom *= 1.15
                        self._instance_dirty = True
                    elif event.button == 5:  # Scroll down - zoom out
                        self.zoom /= 1.15
                        self.zoom = max(self.zoom, 0.02)
                        self._instance_dirty = True

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.painting = False
                    elif event.button == 3:
                        self.erasing = False
                    elif event.button == 2:
                        dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    # Update hover coordinate
                    wx, wy = self._screen_to_world(*event.pos)
                    hc, hr = pixel_to_hex(wx, wy)
                    if hc != self.hover_col or hr != self.hover_row:
                        self.hover_col = hc
                        self.hover_row = hr
                        self._hud_dirty = True

                    if dragging:
                        dx = event.pos[0] - drag_start[0]
                        dy = event.pos[1] - drag_start[1]
                        self.cam_x = cam_start[0] - dx / self.zoom
                        self.cam_y = cam_start[1] - dy / self.zoom
                        self._instance_dirty = True
                    elif self.painting:
                        self._paint_at_screen(*event.pos)
                    elif self.erasing:
                        self._erase_at_screen(*event.pos)

                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.zoom *= 1.15
                    elif event.y < 0:
                        self.zoom /= 1.15
                        self.zoom = max(self.zoom, 0.02)
                    self._instance_dirty = True
                    self._hud_dirty = True

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        self.paint_layer = 2 if self.paint_layer == 1 else 1
                        self._hud_dirty = True
                        print(f"Layer: {self.paint_layer}")
                    elif event.key == pygame.K_s:
                        self.grid.save(self.save_path)
                        print(f"Saved to {self.save_path}")
                    elif event.key == pygame.K_l:
                        if os.path.exists(self.save_path):
                            self.grid = HexGrid.load(self.save_path)
                            self._instance_dirty = True
                            self._hud_dirty = True
                            print("Loaded")
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        idx = event.key - pygame.K_1 + 1
                        if idx < len(PALETTE):
                            self.current_color_idx = idx
                            self._hud_dirty = True
                            print(f"Color {idx}: {PALETTE[idx]}")
                    elif event.key == pygame.K_0:
                        idx = 9
                        if idx < len(PALETTE):
                            self.current_color_idx = idx
                            self._hud_dirty = True
                            print(f"Color {idx}: {PALETTE[idx]}")
                    elif event.key in QWERTY_KEY_MAP:
                        idx = QWERTY_KEY_MAP[event.key]
                        if idx < len(PALETTE):
                            self.current_color_idx = idx
                            self._hud_dirty = True
                            print(f"Color {idx}: {PALETTE[idx]}")

            # Render
            if self._instance_dirty or self._grid_dirty:
                self._rebuild_visible_instances()

            self.ctx.clear(0.2, 0.2, 0.2, 1.0)
            proj = build_projection(self.cam_x, self.cam_y, self.zoom, self.win_w, self.win_h)

            # Draw background
            self.bg_prog["u_proj"].write(proj.tobytes())
            self.bg_tex.use(0)
            self.bg_vao.render(moderngl.TRIANGLES)

            # Draw hex fills
            if self.hex_vao and self.instance_count > 0:
                self.hex_prog["u_proj"].write(proj.tobytes())
                self.hex_vao.render(moderngl.TRIANGLES, instances=self.instance_count)

            # Draw grid lines (only when zoomed in enough)
            if self.zoom > 0.4 and self.grid_vao and self.grid_line_count > 0:
                self.grid_prog["u_proj"].write(proj.tobytes())
                self.grid_prog["u_line_color"].value = (0.3, 0.3, 0.3, 0.5)
                self.grid_vao.render(moderngl.LINE_LOOP, instances=self.grid_line_count)

            # Draw HUD overlay
            if self._hud_dirty:
                self._rebuild_hud()
            self.hud_tex.use(0)
            self.hud_vao.render(moderngl.TRIANGLES)

            pygame.display.flip()
            clock.tick(60)

        # Auto-save on exit
        self.grid.save(self.save_path)
        print(f"Auto-saved to {self.save_path}")
        pygame.quit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hex Grid Map Editor")
    parser.add_argument("save_file", nargs="?", default=SAVE_PATH, help="Path to save/load hex grid data (default: maps/hex_grid_data.json)")
    args = parser.parse_args()
    editor = HexEditor(save_path=args.save_file)
    editor.run()
