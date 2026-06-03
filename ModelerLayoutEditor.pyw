from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
DATA_DIR = ROOT / "data"
DEFAULT_LAYOUT_PATH = DATA_DIR / "default_layout.json"
CURRENT_LAYOUT_PATH = DATA_DIR / "current_layout.json"
APP_ICON_ICO_PATH = ROOT / "Build" / "desktop" / "ModelerDesktopIcon.ico"
APP_ICON_PNG_PATH = ROOT / "Build" / "desktop" / "ModelerDesktopIconSource.png"
APP_USER_MODEL_ID = "DTSwink.Modeler"
CANVAS_BACKGROUND = "#ece5d6"
MAP_LABEL_MODES = [
    "Hover",
    "Adaptive",
    "All",
    "Selected",
]
MAJOR_POINT_TYPES = {
    "CommanderChair",
    "Gate",
    "WatchTower",
    "SpawnPoint",
}
REGION_ZONE_TYPES = {
    "Ocean",
    "Lake",
    "Forest",
}
SMALL_ZONE_TYPES = {
    "TentArea",
    "TrainingArea",
    "Infirmary",
}
BACKGROUND_ZONE_TYPES = {
    "Walkable",
    "Blocked",
    "Forest",
    "Ocean",
    "Lake",
}
LABEL_LINE_TAG = "label_line"
LABEL_BG_TAG = "label_bg"
LABEL_TEXT_TAG = "label_text"
HANDLE_TAG = "selection_handle"
FRAME_TAG = "world_frame"
SIMULATION_FRAME_MS = 16
SIMULATION_SPEED_OPTIONS = [
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
]
ROMAN_SIMULATION_ZONE_ID = "zone-roman-camp"
ROMAN_AGENT_COUNT = 5
SPACEBAR_TEXT_INPUT_CLASSES = {
    "Entry",
    "TEntry",
    "Text",
    "TCombobox",
    "Spinbox",
}
ZONE_TYPE_COLORS = {
    "TentArea": "#b7b2ab",
    "Infirmary": "#ede7df",
    "TrainingArea": "#d4934f",
}
LOCATION_TYPE_COLORS = {
    "CommanderChair": "#f0c94f",
    "Fire": "#eb6d3a",
    "Basin": "#2f6dff",
    "WatchTower": "#8257e5",
    "Gate": "",
}

ZONE_TYPES = [
    "Walkable",
    "Blocked",
    "Camp",
    "TentArea",
    "TrainingArea",
    "Forest",
    "Ocean",
    "Lake",
    "Infirmary",
    "CommanderArea",
    "WatchTowerVision",
    "SpawnArea",
]

POINT_TYPES = [
    "CommanderChair",
    "Fire",
    "Basin",
    "WatchTower",
    "Bell",
    "BigAlarm",
    "Gate",
    "InfirmaryBed",
    "NurseStation",
    "SpawnPoint",
    "PatrolPoint",
    "RallyPoint",
]

FACTIONS = [
    "Neutral",
    "Roman",
    "Ottoman",
    "Wildlife",
]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def deep_copy(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) != 6:
        return (127, 127, 127)
    return (
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
    )


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def blend_hex(color_a: str, color_b: str, weight_b: float) -> str:
    weight_b = clamp(weight_b, 0.0, 1.0)
    weight_a = 1.0 - weight_b
    rgb_a = hex_to_rgb(color_a)
    rgb_b = hex_to_rgb(color_b)
    blended = (
        int(rgb_a[0] * weight_a + rgb_b[0] * weight_b),
        int(rgb_a[1] * weight_a + rgb_b[1] * weight_b),
        int(rgb_a[2] * weight_a + rgb_b[2] * weight_b),
    )
    return rgb_to_hex(blended)


def semantic_zone_color(zone_type: str, fallback: str) -> str:
    return ZONE_TYPE_COLORS.get(zone_type, fallback)


def faction_color(faction: str) -> str:
    if faction == "Roman":
        return "#2f6dff"
    if faction == "Ottoman":
        return "#c84836"
    return "#7a6b56"


def semantic_location_color(location: dict) -> str:
    return LOCATION_TYPE_COLORS.get(location["type"], faction_color(location["faction"]))


def configure_windows_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def apply_window_icon(window: tk.Tk) -> None:
    if APP_ICON_ICO_PATH.exists():
        try:
            window.iconbitmap(default=str(APP_ICON_ICO_PATH))
        except Exception:
            pass
    if APP_ICON_PNG_PATH.exists():
        try:
            icon_image = tk.PhotoImage(file=str(APP_ICON_PNG_PATH))
            window._modeler_icon_image = icon_image
            window.iconphoto(True, icon_image)
        except Exception:
            pass


def today_stamp() -> str:
    return date.today().isoformat()


def format_build_stamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def format_sim_time(seconds: float) -> str:
    total_seconds = max(0.0, float(seconds))
    minutes = int(total_seconds // 60.0)
    remainder = total_seconds - minutes * 60.0
    return f"{minutes:02d}:{remainder:04.1f}"


def format_speed_label(multiplier: float) -> str:
    if abs(multiplier - round(multiplier)) < 0.001:
        return f"{int(round(multiplier))}x"
    return f"{multiplier:g}x"


def distance(a: dict, b: dict) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def local_to_world(point: dict, yaw_radians: float) -> dict:
    cosine = math.cos(yaw_radians)
    sine = math.sin(yaw_radians)
    return {
        "x": point["x"] * cosine - point["y"] * sine,
        "y": point["x"] * sine + point["y"] * cosine,
    }


def world_to_local(point: dict, center: dict, yaw_radians: float) -> dict:
    dx = point["x"] - center["x"]
    dy = point["y"] - center["y"]
    cosine = math.cos(-yaw_radians)
    sine = math.sin(-yaw_radians)
    return {
        "x": dx * cosine - dy * sine,
        "y": dx * sine + dy * cosine,
    }


def point_to_segment_distance(point: dict, a: dict, b: dict) -> float:
    dx = b["x"] - a["x"]
    dy = b["y"] - a["y"]
    if dx == 0 and dy == 0:
        return distance(point, a)
    t = ((point["x"] - a["x"]) * dx + (point["y"] - a["y"]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projected = {
        "x": a["x"] + dx * t,
        "y": a["y"] + dy * t,
    }
    return distance(point, projected)


class LayoutEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        apply_window_icon(self.root)
        self.window_title_base = "Modeler Layout Editor"
        self.root.title(self.window_title_base)
        self.root.geometry("1500x920")
        self.root.minsize(1180, 760)
        self.loaded_build_mtime = SCRIPT_PATH.stat().st_mtime
        self.restart_needed = False

        self.default_layout = read_json(DEFAULT_LAYOUT_PATH)
        self.layout = self._load_current_layout()
        self.saved_layout = deep_copy(self.layout)
        self.dirty = False
        self.selected_kind = "zone"
        self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
        self.hover_kind = None
        self.hover_id = None
        self.drag_state = None
        self.pan_state = None
        self.view = None
        self.view_zoom = 1.0
        self.view_center = self.default_view_center()
        self.undo_stack: list[dict] = []
        self.max_undo_states = 80
        self.label_boxes: list[tuple[float, float, float, float]] = []
        self.suppress_tree_event = False
        self.status_var = tk.StringVar(value="Ready. Click Save Layout to keep changes in data/current_layout.json.")
        self.meta_var = tk.StringVar()
        self.selection_var = tk.StringVar()
        self.play_button_var = tk.StringVar(value="Play")
        self.sim_summary_var = tk.StringVar()
        self.sim_speed_var = tk.StringVar(value=format_speed_label(1.0))
        self.freeze_layout_var = tk.BooleanVar(value=False)
        self.simulation_running = False
        self.simulation_speed = 1.0
        self.simulation_time_seconds = 0.0
        self.last_simulation_tick = time.perf_counter()
        self.spacebar_toggle_pending = False
        self.sim_rng = random.Random(1337)
        self.agents = self.build_initial_agents()
        self.restore_saved_view_state()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._sync_world_controls()
        self.render_all()
        self.root.bind_all("<KeyPress-space>", self.on_spacebar_press, add="+")
        self.root.bind_all("<KeyRelease-space>", self.on_spacebar_release, add="+")
        self.root.after(SIMULATION_FRAME_MS, self.on_simulation_frame)
        self.root.after(2500, self.poll_for_editor_code_update)

    def _load_current_layout(self) -> dict:
        if CURRENT_LAYOUT_PATH.exists():
            try:
                layout = read_json(CURRENT_LAYOUT_PATH)
                return self._normalize_layout(layout)
            except Exception:
                pass
        layout = self._normalize_layout(deep_copy(self.default_layout))
        write_json(CURRENT_LAYOUT_PATH, layout)
        return layout

    def _normalize_layout(self, payload: dict) -> dict:
        layout = deep_copy(payload)
        layout.setdefault("editor", {})
        layout["editor"].setdefault("snapToGrid", True)
        layout["editor"].setdefault("snapSize", 50)
        layout["editor"].setdefault("labelFontSize", 12)
        layout["editor"].setdefault("labelMode", "Hover")
        layout.setdefault("root", {})
        layout["root"].setdefault("cellSize", 100)
        layout["root"].setdefault("gridSize", {"x": 240, "y": 80})
        layout["root"].setdefault("drawLayout", True)
        layout["root"].setdefault("drawGrid", True)
        layout["root"].setdefault("drawLabels", True)
        layout.setdefault("zones", [])
        if "points" not in layout and "locations" in layout:
            layout["points"] = layout["locations"]
        layout.setdefault("points", [])
        layout["locations"] = layout["points"]
        layout.setdefault("walls", [])
        layout.setdefault("summary", "Editable layout marker foundation.")
        layout.setdefault("footer", "Native local editor for the latest Modeler layout state.")
        layout.setdefault("stage", "Engine-independent layout editor")
        layout.setdefault("block", "0A")
        layout.setdefault("updated", today_stamp())
        default_center = {
            "x": float(layout["root"]["gridSize"]["x"] * layout["root"]["cellSize"]) * 0.5,
            "y": float(layout["root"]["gridSize"]["y"] * layout["root"]["cellSize"]) * 0.5,
        }
        saved_view = layout["editor"].setdefault("savedView", {})
        saved_view["zoom"] = clamp(float(saved_view.get("zoom", 1.0)), 0.35, 8.0)
        saved_center = saved_view.setdefault("center", default_center)
        if not isinstance(saved_center, dict):
            saved_center = default_center
            saved_view["center"] = saved_center
        saved_center["x"] = float(saved_center.get("x", default_center["x"]))
        saved_center["y"] = float(saved_center.get("y", default_center["y"]))

        for index, zone in enumerate(layout["zones"]):
            zone.setdefault("id", f"zone-{index + 1}")
            zone.setdefault("label", zone["id"])
            zone.setdefault("type", "Walkable")
            zone.setdefault("faction", "Neutral")
            zone.setdefault("color", "#bca278")
            zone.setdefault("priority", 0)
            zone.setdefault("yawRadians", 0.0)
            zone.setdefault("center", {"x": 0.0, "y": 0.0})
            zone.setdefault("size", {"x": 1000.0, "y": 1000.0})
            zone["color"] = semantic_zone_color(zone["type"], zone["color"])

        for index, point in enumerate(layout["points"]):
            point.setdefault("id", f"point-{index + 1}")
            point.setdefault("label", point["id"])
            point.setdefault("type", "RallyPoint")
            point.setdefault("faction", "Neutral")
            point.setdefault("slotCount", 1)
            point.setdefault("facingRadians", 0.0)
            point.setdefault("radius", 100.0)
            point.setdefault("position", {"x": 0.0, "y": 0.0})

        for index, wall in enumerate(layout["walls"]):
            wall.setdefault("id", f"wall-{index + 1}")
            wall.setdefault("faction", "Neutral")
            wall.setdefault("thickness", 100.0)
            wall.setdefault("a", {"x": 0.0, "y": 0.0})
            wall.setdefault("b", {"x": 1000.0, "y": 0.0})

        return layout

    def build_initial_agents(self) -> list[dict]:
        zone = self.simulation_bounds_zone()
        rng = random.Random(1337)
        agents: list[dict] = []
        for index in range(ROMAN_AGENT_COUNT):
            position = self.random_point_in_zone(zone, rng, agents)
            heading = rng.uniform(0.0, math.tau)
            agents.append(
                {
                    "id": f"agent-roman-{index + 1}",
                    "label": f"Roman Agent {index + 1}",
                    "faction": "Roman",
                    "position": position,
                    "radius": 90.0,
                    "headingRadians": heading,
                    "targetHeadingRadians": heading,
                    "moveSpeed": rng.uniform(145.0, 225.0),
                    "turnRate": rng.uniform(1.4, 2.5),
                    "decisionTimer": rng.uniform(0.35, 1.6),
                }
            )
        return agents

    def random_point_in_zone(self, zone: dict, rng: random.Random, existing_agents: list[dict] | None = None) -> dict:
        margin = 180.0
        half_x = max(140.0, zone["size"]["x"] * 0.5 - margin)
        half_y = max(140.0, zone["size"]["y"] * 0.5 - margin)
        best_point = deep_copy(zone["center"])
        attempts = 16
        for _ in range(attempts):
            local = {
                "x": rng.uniform(-half_x, half_x),
                "y": rng.uniform(-half_y, half_y),
            }
            rotated = local_to_world(local, zone["yawRadians"])
            candidate = {
                "x": zone["center"]["x"] + rotated["x"],
                "y": zone["center"]["y"] + rotated["y"],
            }
            if not existing_agents:
                return candidate
            if all(distance(candidate, agent["position"]) >= 220.0 for agent in existing_agents):
                return candidate
            best_point = candidate
        return best_point

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, padding=16)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.configure(width=380)

        viewer = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        viewer.grid(row=0, column=1, sticky="nsew")
        viewer.columnconfigure(0, weight=1)
        viewer.rowconfigure(1, weight=1)

        title = ttk.Label(sidebar, text="Modeler Layout Editor", font=("Georgia", 24, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            sidebar,
            text="Native local editor for the current simulation layout. Drag markers directly on the map and tune exact values in the inspector.",
            wraplength=340,
            justify="left",
        )
        subtitle.pack(anchor="w", pady=(8, 14))

        button_row = ttk.Frame(sidebar)
        button_row.pack(fill="x", pady=(0, 12))
        self._make_button(button_row, "Save Layout", self.save_layout_now).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_button(button_row, "Refresh App", self.refresh_app).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self._make_button(button_row, "Undo", self.undo_last_change).grid(row=0, column=2, sticky="ew")
        self._make_button(button_row, "Reset Draft", self.reset_layout).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))
        self._make_button(button_row, "Import JSON", self.import_json).grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(6, 0))
        self._make_button(button_row, "Export JSON", self.export_json).grid(row=1, column=2, sticky="ew", pady=(6, 0))
        self._make_button(button_row, "Open Data Folder", self.open_data_folder).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        button_row.columnconfigure((0, 1, 2), weight=1)

        simulation_frame = ttk.LabelFrame(sidebar, text="Simulation", padding=12)
        simulation_frame.pack(fill="x", pady=(0, 12))
        simulation_frame.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(
            simulation_frame,
            text="Roman prototype: five agents wander inside the Roman camp at 60 FPS. Play keeps the layout live unless Freeze Layout is checked.",
            wraplength=320,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self._make_button(simulation_frame, None, self.toggle_simulation, textvariable=self.play_button_var).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        simulation_speed_combo = ttk.Combobox(
            simulation_frame,
            textvariable=self.sim_speed_var,
            values=[format_speed_label(value) for value in SIMULATION_SPEED_OPTIONS],
            state="readonly",
        )
        simulation_speed_combo.grid(row=1, column=1, sticky="ew", padx=(0, 6))
        simulation_speed_combo.bind("<<ComboboxSelected>>", self.apply_simulation_speed)
        ttk.Checkbutton(
            simulation_frame,
            text="Freeze Layout",
            variable=self.freeze_layout_var,
            command=self.on_freeze_layout_toggled,
        ).grid(row=1, column=2, sticky="w")
        ttk.Label(simulation_frame, textvariable=self.sim_summary_var, wraplength=320, justify="left").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )

        ttk.Label(sidebar, textvariable=self.status_var, wraplength=340, justify="left").pack(anchor="w", pady=(10, 14))

        world_frame = ttk.LabelFrame(sidebar, text="World Settings", padding=12)
        world_frame.pack(fill="x", pady=(0, 12))
        for index in range(2):
            world_frame.columnconfigure(index, weight=1)

        self.cell_size_var = tk.StringVar()
        self.grid_x_var = tk.StringVar()
        self.grid_y_var = tk.StringVar()
        self.snap_size_var = tk.StringVar()
        self.label_font_size_var = tk.StringVar()
        self.label_mode_var = tk.StringVar()
        self.zoom_percent_var = tk.StringVar()
        self.draw_grid_var = tk.BooleanVar()
        self.draw_labels_var = tk.BooleanVar()
        self.snap_enabled_var = tk.BooleanVar()

        self._make_entry(world_frame, "Cell Size", self.cell_size_var, 0, 0, self.apply_world_settings)
        self._make_entry(world_frame, "Snap Size", self.snap_size_var, 0, 1, self.apply_world_settings)
        self._make_entry(world_frame, "Grid Width", self.grid_x_var, 1, 0, self.apply_world_settings)
        self._make_entry(world_frame, "Grid Height", self.grid_y_var, 1, 1, self.apply_world_settings)
        self._make_entry(world_frame, "Label Text Size", self.label_font_size_var, 2, 0, self.apply_world_settings)
        ttk.Checkbutton(world_frame, text="Draw grid", variable=self.draw_grid_var, command=self.apply_world_settings).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(world_frame, text="Draw labels", variable=self.draw_labels_var, command=self.apply_world_settings).grid(row=3, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(world_frame, text="Snap moves to grid", variable=self.snap_enabled_var, command=self.apply_world_settings).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        view_frame = ttk.LabelFrame(sidebar, text="View", padding=12)
        view_frame.pack(fill="x", pady=(0, 12))
        view_frame.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(
            view_frame,
            text="Scroll on the map to zoom. Right-drag the map to pan around.",
            wraplength=320,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self._make_button(view_frame, "Zoom Out", self.zoom_out).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self._make_button(view_frame, "Fit View", self.reset_view).grid(row=1, column=1, sticky="ew", padx=(0, 6))
        self._make_button(view_frame, "Zoom In", self.zoom_in).grid(row=1, column=2, sticky="ew")
        ttk.Label(view_frame, text="Zoom").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(view_frame, textvariable=self.zoom_percent_var).grid(row=2, column=1, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Label(view_frame, text="Label Mode").grid(row=3, column=0, sticky="w", pady=(10, 0))
        label_mode_combo = ttk.Combobox(view_frame, textvariable=self.label_mode_var, values=MAP_LABEL_MODES, state="readonly")
        label_mode_combo.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(10, 0))
        label_mode_combo.bind("<<ComboboxSelected>>", self.apply_world_settings)

        tree_frame = ttk.LabelFrame(sidebar, text="Layout Items", padding=12)
        tree_frame.pack(fill="both", expand=True, pady=(0, 12))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse", height=14)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        inspector_frame = ttk.LabelFrame(sidebar, text="Inspector", padding=12)
        inspector_frame.pack(fill="x")
        inspector_frame.columnconfigure(0, weight=1)
        self.inspector_body = ttk.Frame(inspector_frame)
        self.inspector_body.grid(row=0, column=0, sticky="ew")

        top_bar = ttk.Frame(viewer)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_bar.columnconfigure(0, weight=1)

        viewer_title = ttk.Label(top_bar, text="Interactive Top-Down Layout", font=("Georgia", 18, "bold"))
        viewer_title.grid(row=0, column=0, sticky="w")
        viewer_meta = ttk.Label(top_bar, textvariable=self.meta_var, justify="right")
        viewer_meta.grid(row=0, column=1, sticky="e")

        viewer_hint = ttk.Label(
            top_bar,
            text="Click to select. Drag zones, locations, or walls directly on the map, scroll to zoom, right-drag to pan, and use the inspector for exact values. Use Refresh App to load the newest editor build.",
            wraplength=900,
            justify="left",
        )
        viewer_hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        canvas_frame = ttk.Frame(viewer, padding=0)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#ece5d6", highlightthickness=1, highlightbackground="#b7ab98")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Enter>", lambda _event: self.canvas.focus_set())
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<ButtonPress-3>", self.on_canvas_pan_press)
        self.canvas.bind("<B3-Motion>", self.on_canvas_pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_canvas_pan_release)
        self.canvas.bind("<MouseWheel>", self.on_canvas_mousewheel)
        self.canvas.bind("<Button-4>", self.on_canvas_mousewheel)
        self.canvas.bind("<Button-5>", self.on_canvas_mousewheel)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<Configure>", lambda _event: self.render_canvas())
        self.root.bind("<Control-s>", self.save_layout_now)
        self.root.bind("<Control-r>", self.refresh_app)
        self.root.bind("<Control-z>", self.undo_last_change)
        self.root.bind("<Control-0>", self.reset_view)

        footer_frame = ttk.Frame(viewer)
        footer_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        footer_frame.columnconfigure(0, weight=1)

        self.selection_label = ttk.Label(footer_frame, textvariable=self.selection_var, wraplength=960, justify="left")
        self.selection_label.grid(row=0, column=0, sticky="w")

        self.footer_label = ttk.Label(footer_frame, text="", wraplength=960, justify="left")
        self.footer_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _make_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, column: int, callback) -> None:
        field = ttk.Frame(parent)
        field.grid(row=row, column=column, sticky="ew", padx=(0, 8) if column == 0 else (0, 0), pady=(0, 8))
        field.columnconfigure(0, weight=1)
        ttk.Label(field, text=label).grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(field, textvariable=variable)
        entry.grid(row=1, column=0, sticky="ew")
        entry.bind("<Return>", callback)
        entry.bind("<FocusOut>", callback)

    def _make_button(self, parent, text: str | None, command, *, textvariable: tk.StringVar | None = None):
        def invoke():
            try:
                command()
            finally:
                self.root.after_idle(self.canvas.focus_set)

        button = ttk.Button(parent, text=text if textvariable is None else "", textvariable=textvariable, command=invoke, takefocus=False)
        button.bind("<KeyPress-space>", lambda _event: "break")
        return button

    def _sync_world_controls(self) -> None:
        root = self.layout["root"]
        editor = self.layout["editor"]
        self.cell_size_var.set(str(root["cellSize"]))
        self.grid_x_var.set(str(root["gridSize"]["x"]))
        self.grid_y_var.set(str(root["gridSize"]["y"]))
        self.snap_size_var.set(str(editor["snapSize"]))
        self.label_font_size_var.set(str(editor["labelFontSize"]))
        self.label_mode_var.set(editor["labelMode"])
        self.draw_grid_var.set(bool(root["drawGrid"]))
        self.draw_labels_var.set(bool(root["drawLabels"]))
        self.snap_enabled_var.set(bool(editor["snapToGrid"]))
        self.zoom_percent_var.set(f"{int(round(self.view_zoom * 100))}%")
        self.update_simulation_summary()

    def restore_saved_view_state(self) -> None:
        saved_view = self.layout.get("editor", {}).get("savedView", {})
        default_center = self.default_view_center()
        saved_center = saved_view.get("center", default_center)
        if not isinstance(saved_center, dict):
            saved_center = default_center
        self.view_zoom = clamp(float(saved_view.get("zoom", 1.0)), 0.35, 8.0)
        self.view_center = {
            "x": float(saved_center.get("x", default_center["x"])),
            "y": float(saved_center.get("y", default_center["y"])),
        }

    def persist_saved_view_state(self) -> None:
        self.layout.setdefault("editor", {})
        self.layout["editor"]["savedView"] = {
            "zoom": round(float(self.view_zoom), 4),
            "center": {
                "x": round(float(self.view_center["x"]), 2),
                "y": round(float(self.view_center["y"]), 2),
            },
        }

    def world_dimensions(self) -> tuple[float, float]:
        return (
            max(1.0, float(self.layout["root"]["gridSize"]["x"] * self.layout["root"]["cellSize"])),
            max(1.0, float(self.layout["root"]["gridSize"]["y"] * self.layout["root"]["cellSize"])),
        )

    def default_view_center(self) -> dict:
        world_width, world_height = self.world_dimensions()
        return {
            "x": world_width * 0.5,
            "y": world_height * 0.5,
        }

    def capture_state(self) -> dict:
        return {
            "layout": deep_copy(self.layout),
            "selected_kind": self.selected_kind,
            "selected_id": self.selected_id,
        }

    def record_undo_state(self, snapshot: dict) -> None:
        if self.undo_stack and self.undo_stack[-1] == snapshot:
            return
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_undo_states:
            self.undo_stack.pop(0)

    def ensure_valid_selection(self) -> None:
        if self.selected_kind == "agent" and self.selected_id is not None:
            for agent in self.agents:
                if agent["id"] == self.selected_id:
                    return
        if self.selected_kind in {"zone", "point", "wall"} and self.selected_id is not None:
            for item in self.layout[f"{self.selected_kind}s"]:
                if item["id"] == self.selected_id:
                    return
        for kind in ("zone", "point", "wall"):
            items = self.layout[f"{kind}s"]
            if items:
                self.selected_kind = kind
                self.selected_id = items[0]["id"]
                return
        self.selected_kind = "zone"
        self.selected_id = None

    def apply_snapshot(self, snapshot: dict) -> None:
        self.layout = self._normalize_layout(snapshot["layout"])
        self.selected_kind = snapshot.get("selected_kind", "zone")
        self.selected_id = snapshot.get("selected_id")
        self.hover_kind = None
        self.hover_id = None
        self.clamp_all_agents_to_bounds()
        self.ensure_valid_selection()
        self.dirty = self.layout != self.saved_layout
        self._sync_world_controls()

    def update_meta_and_title(self) -> None:
        build_text = f"UI {format_build_stamp(self.loaded_build_mtime)}"
        restart_text = " | Refresh to load newer UI" if self.restart_needed else ""
        dirty_suffix = " | Unsaved changes" if self.dirty else ""
        self.meta_var.set(f"Block {self.layout['block']} | {self.layout['stage']} | {self.layout['updated']} | {build_text}{restart_text}{dirty_suffix}")
        title = self.window_title_base
        if self.restart_needed:
            title += " - Refresh Needed"
        if self.dirty:
            title += "*"
        self.root.title(title)

    def poll_for_editor_code_update(self) -> None:
        try:
            self.restart_needed = SCRIPT_PATH.stat().st_mtime > self.loaded_build_mtime + 0.5
        except OSError:
            self.restart_needed = False
        self.update_meta_and_title()
        self.root.after(2500, self.poll_for_editor_code_update)

    def update_simulation_summary(self) -> None:
        state_text = "Running" if self.simulation_running else "Paused"
        freeze_suffix = " | Layout frozen" if self.freeze_layout_var.get() else ""
        self.play_button_var.set("Pause" if self.simulation_running else "Play")
        self.sim_summary_var.set(
            f"{state_text} | Sim {format_sim_time(self.simulation_time_seconds)} | {len(self.agents)} Roman agents | {format_speed_label(self.simulation_speed)}{freeze_suffix}"
        )

    def apply_simulation_speed(self, _event=None) -> str | None:
        try:
            self.simulation_speed = max(0.05, float(self.sim_speed_var.get().rstrip("x")))
        except ValueError:
            self.simulation_speed = 1.0
            self.sim_speed_var.set(format_speed_label(self.simulation_speed))
        self.update_simulation_summary()
        if _event is not None:
            return "break"
        return None

    def toggle_simulation(self) -> None:
        self.simulation_running = not self.simulation_running
        self.last_simulation_tick = time.perf_counter()
        self.status_var.set("Simulation running inside the Roman camp." if self.simulation_running else "Simulation paused.")
        self.update_simulation_summary()
        self.render_stats_and_labels()

    def on_freeze_layout_toggled(self) -> None:
        if self.freeze_layout_var.get() and self.selected_kind in {"zone", "point", "wall"}:
            self.clear_selection()
        self.status_var.set(
            "Layout frozen. Hover labels still work, but map handles and layout dragging are disabled."
            if self.freeze_layout_var.get()
            else "Layout unfrozen. Zones, locations, and walls can be edited again."
        )
        self.update_simulation_summary()
        self.render_all()

    def simulation_bounds_zone(self) -> dict:
        for zone in self.layout["zones"]:
            if zone["id"] == ROMAN_SIMULATION_ZONE_ID:
                return zone
        for zone in self.layout["zones"]:
            if zone["type"] == "Camp" and zone["faction"] == "Roman":
                return zone
        world_width, world_height = self.world_dimensions()
        return {
            "center": {"x": world_width * 0.5, "y": world_height * 0.5},
            "size": {"x": world_width, "y": world_height},
            "yawRadians": 0.0,
        }

    def clamp_agent_position(self, agent: dict, position: dict) -> tuple[dict, bool, bool]:
        zone = self.simulation_bounds_zone()
        margin = max(110.0, agent["radius"] * 1.2)
        local = world_to_local(position, zone["center"], zone["yawRadians"])
        max_x = max(80.0, zone["size"]["x"] * 0.5 - margin)
        max_y = max(80.0, zone["size"]["y"] * 0.5 - margin)
        clamped_local = {
            "x": clamp(local["x"], -max_x, max_x),
            "y": clamp(local["y"], -max_y, max_y),
        }
        hit_x = abs(clamped_local["x"] - local["x"]) > 0.001
        hit_y = abs(clamped_local["y"] - local["y"]) > 0.001
        rotated = local_to_world(clamped_local, zone["yawRadians"])
        return (
            {
                "x": zone["center"]["x"] + rotated["x"],
                "y": zone["center"]["y"] + rotated["y"],
            },
            hit_x,
            hit_y,
        )

    def reflected_heading(self, heading_radians: float, zone_yaw_radians: float, bounce_x: bool, bounce_y: bool) -> float:
        local_heading = heading_radians - zone_yaw_radians
        local_dx = math.cos(local_heading)
        local_dy = math.sin(local_heading)
        if bounce_x:
            local_dx *= -1.0
        if bounce_y:
            local_dy *= -1.0
        return math.atan2(local_dy, local_dx) + zone_yaw_radians

    def wrap_angle(self, angle_radians: float) -> float:
        return math.atan2(math.sin(angle_radians), math.cos(angle_radians))

    def step_angle_towards(self, current: float, target: float, max_delta: float) -> float:
        delta = self.wrap_angle(target - current)
        if abs(delta) <= max_delta:
            return target
        return current + math.copysign(max_delta, delta)

    def on_simulation_frame(self) -> None:
        now = time.perf_counter()
        real_dt = min(0.08, max(0.0, now - self.last_simulation_tick))
        self.last_simulation_tick = now
        changed = False
        if self.simulation_running and real_dt > 0.0:
            changed = self.advance_simulation(real_dt * self.simulation_speed)
        if changed:
            self.render_canvas()
            self.render_stats_and_labels()
        self.root.after(SIMULATION_FRAME_MS, self.on_simulation_frame)

    def advance_simulation(self, sim_dt: float) -> bool:
        if sim_dt <= 0.0:
            return False
        zone = self.simulation_bounds_zone()
        any_changed = False
        self.simulation_time_seconds += sim_dt
        dragged_agent_id = self.drag_state.get("id") if self.drag_state and self.drag_state.get("type") == "move-agent" else None
        for agent in self.agents:
            if dragged_agent_id == agent["id"]:
                continue
            agent["decisionTimer"] -= sim_dt
            if agent["decisionTimer"] <= 0.0:
                agent["targetHeadingRadians"] = agent["headingRadians"] + self.sim_rng.uniform(-1.7, 1.7)
                agent["decisionTimer"] = self.sim_rng.uniform(0.35, 1.4)
            agent["headingRadians"] = self.step_angle_towards(
                agent["headingRadians"],
                agent["targetHeadingRadians"],
                agent["turnRate"] * sim_dt,
            )
            proposed = {
                "x": agent["position"]["x"] + math.cos(agent["headingRadians"]) * agent["moveSpeed"] * sim_dt,
                "y": agent["position"]["y"] + math.sin(agent["headingRadians"]) * agent["moveSpeed"] * sim_dt,
            }
            clamped, bounce_x, bounce_y = self.clamp_agent_position(agent, proposed)
            agent["position"] = clamped
            if bounce_x or bounce_y:
                reflected = self.reflected_heading(agent["headingRadians"], zone["yawRadians"], bounce_x, bounce_y)
                agent["headingRadians"] = reflected
                agent["targetHeadingRadians"] = reflected + self.sim_rng.uniform(-0.55, 0.55)
                agent["decisionTimer"] = self.sim_rng.uniform(0.2, 0.9)
            any_changed = True
        self.update_simulation_summary()
        return any_changed

    def agent_visual_radius_pixels(self, agent: dict) -> float:
        return max(6.0, agent["radius"] * self.view["scale"] * 0.11)

    def agent_hit_radius_world(self, agent: dict) -> float:
        return (self.agent_visual_radius_pixels(agent) + 8.0) / self.view["scale"]

    def get_agent_by_id(self, agent_id: str | None) -> dict | None:
        if agent_id is None:
            return None
        for agent in self.agents:
            if agent["id"] == agent_id:
                return agent
        return None

    def get_agent_hit(self, world_point: dict) -> dict | None:
        for agent in reversed(self.agents):
            if distance(world_point, agent["position"]) <= self.agent_hit_radius_world(agent):
                return {"kind": "agent", "id": agent["id"]}
        return None

    def should_draw_agent_label(self, agent: dict) -> bool:
        return (self.hover_kind == "agent" and self.hover_id == agent["id"]) or (
            self.selected_kind == "agent" and self.selected_id == agent["id"]
        )

    def draw_agent(self, agent: dict) -> None:
        screen = self.world_to_canvas(agent["position"])
        radius = self.agent_visual_radius_pixels(agent)
        fill = blend_hex(faction_color(agent["faction"]), "#f7f4ee", 0.18)
        outline = "#e3bf47" if self.selected_kind == "agent" and self.selected_id == agent["id"] else "#1f1a15"
        outline_width = 3 if self.selected_kind == "agent" and self.selected_id == agent["id"] else 2
        facing_length = radius + 8.0
        self.canvas.create_line(
            screen["x"],
            screen["y"],
            screen["x"] + math.cos(agent["headingRadians"]) * facing_length,
            screen["y"] + math.sin(agent["headingRadians"]) * facing_length,
            fill=outline,
            width=2,
        )
        self.canvas.create_oval(
            screen["x"] - radius,
            screen["y"] - radius,
            screen["x"] + radius,
            screen["y"] + radius,
            fill=fill,
            outline=outline,
            width=outline_width,
        )
        core_radius = max(2.0, radius * 0.42)
        self.canvas.create_oval(
            screen["x"] - core_radius,
            screen["y"] - core_radius,
            screen["x"] + core_radius,
            screen["y"] + core_radius,
            fill="#f8f6f1",
            outline="",
        )

    def draw_agent_labels(self) -> None:
        for agent in self.agents:
            if not self.should_draw_agent_label(agent):
                continue
            screen = self.world_to_canvas(agent["position"])
            radius = self.agent_visual_radius_pixels(agent)
            badge_fill = blend_hex(faction_color(agent["faction"]), CANVAS_BACKGROUND, 0.76)
            badge_outline = blend_hex(faction_color(agent["faction"]), "#625b50", 0.34)
            for candidate_x, candidate_y, anchor in self.point_label_candidates(agent, screen, radius):
                bbox = self.draw_badge_label(
                    candidate_x,
                    candidate_y,
                    agent["label"],
                    anchor=anchor,
                    font=("Segoe UI", max(9, int(self.layout["editor"]["labelFontSize"]) - 1), "bold"),
                    text_fill="#1f1a15",
                    background_fill=badge_fill,
                    outline=badge_outline,
                    pad_x=7.0,
                    pad_y=3.0,
                    register=True,
                    allow_overlap=False,
                )
                if bbox is None:
                    continue
                line_end = self.closest_point_on_bbox(screen["x"], screen["y"], bbox)
                if distance({"x": screen["x"], "y": screen["y"]}, {"x": line_end[0], "y": line_end[1]}) > radius + 9:
                    self.canvas.create_line(
                        screen["x"],
                        screen["y"],
                        line_end[0],
                        line_end[1],
                        fill=badge_outline,
                        width=1,
                        tags=(LABEL_LINE_TAG,),
                    )
                break

    def on_spacebar_press(self, event: tk.Event) -> str | None:
        widget = self.root.focus_get() or event.widget
        widget_class = widget.winfo_class() if widget is not None else ""
        self.spacebar_toggle_pending = widget_class not in SPACEBAR_TEXT_INPUT_CLASSES
        if not self.spacebar_toggle_pending:
            return None
        return "break"

    def on_spacebar_release(self, _event: tk.Event) -> str | None:
        if not self.spacebar_toggle_pending:
            return None
        self.spacebar_toggle_pending = False
        self.toggle_simulation()
        return "break"

    def mark_dirty(self, message: str) -> None:
        self.dirty = self.layout != self.saved_layout
        self.status_var.set(message)
        self.update_meta_and_title()

    def clamp_all_agents_to_bounds(self) -> None:
        for agent in self.agents:
            clamped_position, _, _ = self.clamp_agent_position(agent, agent["position"])
            agent["position"] = clamped_position

    def commit_layout_change(self, before_state: dict, message: str, *, sync_world: bool = False) -> bool:
        changed = before_state["layout"] != self.layout
        if sync_world:
            self._sync_world_controls()
        if changed:
            self.record_undo_state(before_state)
            self.clamp_all_agents_to_bounds()
            self.mark_dirty(message)
        else:
            self.update_meta_and_title()
        self.render_all()
        return changed

    def clamp_view_center(self, center: dict, scale: float, width: float, height: float, world_width: float, world_height: float) -> dict:
        if scale <= 0:
            return self.default_view_center()
        visible_width = width / scale
        visible_height = height / scale
        if visible_width >= world_width:
            clamped_x = world_width * 0.5
        else:
            half_width = visible_width * 0.5
            clamped_x = min(max(center["x"], half_width), world_width - half_width)
        if visible_height >= world_height:
            clamped_y = world_height * 0.5
        else:
            half_height = visible_height * 0.5
            clamped_y = min(max(center["y"], half_height), world_height - half_height)
        return {
            "x": clamped_x,
            "y": clamped_y,
        }

    def base_view_scale(self, width: int, height: int) -> float:
        world_width, world_height = self.world_dimensions()
        pad = 28
        inner_width = max(1, width - pad * 2)
        inner_height = max(1, height - pad * 2)
        return min(inner_width / world_width, inner_height / world_height)

    def reset_view_state(self) -> None:
        self.view_zoom = 1.0
        self.view_center = self.default_view_center()
        self.zoom_percent_var.set("100%")

    def zoom_by_factor(self, factor: float, anchor_canvas: dict | None = None) -> None:
        if self.view is None:
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if anchor_canvas is None:
            anchor_canvas = {
                "x": width * 0.5,
                "y": height * 0.5,
            }
        anchor_world = self.canvas_to_world(anchor_canvas)
        next_zoom = min(8.0, max(0.35, self.view_zoom * factor))
        if abs(next_zoom - self.view_zoom) < 0.0001:
            return
        world_width, world_height = self.world_dimensions()
        base_scale = self.base_view_scale(width, height)
        new_scale = base_scale * next_zoom
        next_center = {
            "x": anchor_world["x"] - (anchor_canvas["x"] - width * 0.5) / new_scale,
            "y": anchor_world["y"] - (anchor_canvas["y"] - height * 0.5) / new_scale,
        }
        self.view_zoom = next_zoom
        self.view_center = self.clamp_view_center(next_center, new_scale, width, height, world_width, world_height)
        self.zoom_percent_var.set(f"{int(round(self.view_zoom * 100))}%")
        self.render_canvas()
        self.render_stats_and_labels()

    def zoom_in(self) -> None:
        self.zoom_by_factor(1.2)

    def zoom_out(self) -> None:
        self.zoom_by_factor(1 / 1.2)

    def reset_view(self, _event=None) -> str | None:
        self.reset_view_state()
        self.render_canvas()
        self.render_stats_and_labels()
        if _event is not None:
            return "break"
        return None

    def apply_world_settings(self, _event=None) -> None:
        before_state = self.capture_state()
        try:
            self.layout["root"]["cellSize"] = max(1, int(float(self.cell_size_var.get() or 1)))
            self.layout["root"]["gridSize"]["x"] = max(1, int(float(self.grid_x_var.get() or 1)))
            self.layout["root"]["gridSize"]["y"] = max(1, int(float(self.grid_y_var.get() or 1)))
            self.layout["editor"]["snapSize"] = max(1, int(float(self.snap_size_var.get() or 1)))
            self.layout["editor"]["labelFontSize"] = max(8, int(float(self.label_font_size_var.get() or 8)))
            self.layout["editor"]["labelMode"] = self.label_mode_var.get() if self.label_mode_var.get() in MAP_LABEL_MODES else "Hover"
            self.layout["root"]["drawGrid"] = bool(self.draw_grid_var.get())
            self.layout["root"]["drawLabels"] = bool(self.draw_labels_var.get())
            self.layout["editor"]["snapToGrid"] = bool(self.snap_enabled_var.get())
        except ValueError:
            self.status_var.set("World settings ignored until the numbers are valid.")
            return

        world_width, world_height = self.world_dimensions()
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        current_scale = max(self.base_view_scale(width, height) * self.view_zoom, 0.0001)
        self.view_center = self.clamp_view_center(self.view_center, current_scale, width, height, world_width, world_height)
        self.commit_layout_change(before_state, "Updated world settings. Changes are not saved yet.", sync_world=True)

    def open_data_folder(self) -> None:
        subprocess.Popen(["explorer", str(DATA_DIR)])

    def export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export layout JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="modeler-layout.json",
        )
        if not path:
            return
        write_json(Path(path), self.layout)
        self.status_var.set(f"Exported layout JSON to {path}")

    def import_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Import layout JSON",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        before_state = self.capture_state()
        try:
            self.layout = self._normalize_layout(read_json(Path(path)))
            self.selected_kind = "zone"
            self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
            self.restore_saved_view_state()
            self._sync_world_controls()
            self.commit_layout_change(before_state, f"Imported layout from {path}. Changes are not saved yet.")
        except Exception as error:
            messagebox.showerror("Import Failed", f"Could not import JSON.\n\n{error}")

    def reset_layout(self) -> None:
        if not messagebox.askyesno("Reset Draft", "Reset the current draft to the default layout?"):
            return
        before_state = self.capture_state()
        self.layout = self._normalize_layout(deep_copy(self.default_layout))
        self.selected_kind = "zone"
        self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
        self.restore_saved_view_state()
        self._sync_world_controls()
        self.commit_layout_change(before_state, "Reset layout to default. Changes are not saved yet.")

    def touch_and_save(self, message: str) -> None:
        self.layout["updated"] = today_stamp()
        self.persist_saved_view_state()
        for zone in self.layout["zones"]:
            zone["color"] = semantic_zone_color(zone["type"], zone["color"])
        self.layout["locations"] = self.layout["points"]
        write_json(CURRENT_LAYOUT_PATH, self.layout)
        self.saved_layout = deep_copy(self.layout)
        self.dirty = False
        self.status_var.set(message)
        self.update_meta_and_title()

    def confirm_unsaved_action(self, action_label: str) -> bool:
        if not self.dirty:
            return True
        decision = messagebox.askyesnocancel("Unsaved Changes", f"Save layout changes before {action_label}?")
        if decision is None:
            return False
        if decision:
            self.touch_and_save(f"Saved layout to {CURRENT_LAYOUT_PATH}")
        return True

    def refresh_app(self, _event=None) -> str | None:
        if not self.confirm_unsaved_action("refreshing the editor"):
            if _event is not None:
                return "break"
            return None
        if not self.dirty:
            self.persist_saved_view_state()
            write_json(CURRENT_LAYOUT_PATH, self.layout)
        try:
            subprocess.Popen([sys.executable, str(SCRIPT_PATH)], cwd=str(ROOT))
        except Exception as error:
            messagebox.showerror("Refresh Failed", f"Could not refresh the editor.\n\n{error}")
            if _event is not None:
                return "break"
            return None
        self.root.destroy()
        if _event is not None:
            return "break"
        return None

    def save_layout_now(self, _event=None) -> str | None:
        self.touch_and_save(f"Saved layout to {CURRENT_LAYOUT_PATH}")
        self.render_stats_and_labels()
        if _event is not None:
            return "break"
        return None

    def undo_last_change(self, _event=None) -> str | None:
        if not self.undo_stack:
            self.status_var.set("Nothing to undo yet.")
            if _event is not None:
                return "break"
            return None
        snapshot = self.undo_stack.pop()
        self.apply_snapshot(snapshot)
        self.status_var.set("Undid the last layout change.")
        self.update_meta_and_title()
        self.render_all()
        if _event is not None:
            return "break"
        return None

    def on_close(self) -> None:
        if self.confirm_unsaved_action("closing"):
            self.root.destroy()
            return

    def render_all(self) -> None:
        self.render_tree()
        self.render_inspector()
        self.render_canvas()
        self.render_stats_and_labels()

    def render_stats_and_labels(self) -> None:
        self.update_meta_and_title()
        selected = self.get_selected_item()
        if selected is None:
            self.selection_var.set("Nothing selected. Click a zone, location, or wall on the map or choose one in the list.")
        elif self.selected_kind == "zone":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the zone body to move it, or drag a corner handle to resize from that corner while the opposite corner stays put. "
                f"Current size: {int(selected['size']['x'])} x {int(selected['size']['y'])}."
            )
        elif self.selected_kind == "point":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the location to move it, drag the east handle to change radius, and drag the facing handle to rotate it."
            )
        elif self.selected_kind == "agent":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the agent freely inside the Roman camp while the simulation runs or pauses. Current speed: {int(round(selected['moveSpeed']))}."
            )
        else:
            self.selection_var.set(
                f"{selected['id']} selected. Drag the wall body to move it, or drag either endpoint handle to reshape it."
            )
        self.footer_label.configure(text=self.layout["footer"])
        self.update_simulation_summary()

    def render_tree(self) -> None:
        selection_iid = f"{self.selected_kind}:{self.selected_id}" if self.selected_id else None
        self.suppress_tree_event = True
        try:
            self.tree.delete(*self.tree.get_children())

            zones_parent = self.tree.insert("", "end", iid="group-zone", text="Zones", open=True)
            for zone in self.layout["zones"]:
                self.tree.insert(zones_parent, "end", iid=f"zone:{zone['id']}", text=zone["label"])

            points_parent = self.tree.insert("", "end", iid="group-point", text="Locations", open=True)
            for point in self.layout["points"]:
                self.tree.insert(points_parent, "end", iid=f"point:{point['id']}", text=point["label"])

            agents_parent = self.tree.insert("", "end", iid="group-agent", text="Roman Agents", open=True)
            for agent in self.agents:
                self.tree.insert(agents_parent, "end", iid=f"agent:{agent['id']}", text=agent["label"])

            walls_parent = self.tree.insert("", "end", iid="group-wall", text="Walls", open=True)
            for wall in self.layout["walls"]:
                self.tree.insert(walls_parent, "end", iid=f"wall:{wall['id']}", text=wall["id"])

            if selection_iid and self.tree.exists(selection_iid):
                self.tree.selection_set(selection_iid)
                self.tree.focus(selection_iid)
        finally:
            self.suppress_tree_event = False

    def render_inspector(self) -> None:
        for child in self.inspector_body.winfo_children():
            child.destroy()

        selected = self.get_selected_item()
        if selected is None:
            ttk.Label(self.inspector_body, text="Select a zone, location, or wall to edit its exact values.", wraplength=320, justify="left").pack(anchor="w")
            return

        if self.selected_kind == "zone":
            self.render_zone_inspector(selected)
        elif self.selected_kind == "point":
            self.render_point_inspector(selected)
        elif self.selected_kind == "agent":
            self.render_agent_inspector(selected)
        else:
            self.render_wall_inspector(selected)

    def render_zone_inspector(self, zone: dict) -> None:
        vars_map = {
            "label": tk.StringVar(value=zone["label"]),
            "type": tk.StringVar(value=zone["type"]),
            "faction": tk.StringVar(value=zone["faction"]),
            "x": tk.StringVar(value=str(zone["center"]["x"])),
            "y": tk.StringVar(value=str(zone["center"]["y"])),
            "width": tk.StringVar(value=str(zone["size"]["x"])),
            "height": tk.StringVar(value=str(zone["size"]["y"])),
            "yaw": tk.StringVar(value=str(round(math.degrees(zone["yawRadians"]), 2))),
            "color": tk.StringVar(value=zone["color"]),
        }

        self._inspector_entry("Label", vars_map["label"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_combo("Type", vars_map["type"], ZONE_TYPES, lambda _event=None: self._apply_zone_inspector(zone, vars_map))
        self._inspector_combo("Faction", vars_map["faction"], FACTIONS, lambda _event=None: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Center X", vars_map["x"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Center Y", vars_map["y"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Width", vars_map["width"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Height", vars_map["height"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Yaw Degrees", vars_map["yaw"], lambda: self._apply_zone_inspector(zone, vars_map))
        self._inspector_entry("Color", vars_map["color"], lambda: self._apply_zone_inspector(zone, vars_map))

    def render_point_inspector(self, point: dict) -> None:
        vars_map = {
            "label": tk.StringVar(value=point["label"]),
            "type": tk.StringVar(value=point["type"]),
            "faction": tk.StringVar(value=point["faction"]),
            "x": tk.StringVar(value=str(point["position"]["x"])),
            "y": tk.StringVar(value=str(point["position"]["y"])),
            "radius": tk.StringVar(value=str(point["radius"])),
            "facing": tk.StringVar(value=str(round(math.degrees(point["facingRadians"]), 2))),
            "slotCount": tk.StringVar(value=str(point["slotCount"])),
        }

        self._inspector_entry("Label", vars_map["label"], lambda: self._apply_point_inspector(point, vars_map))
        self._inspector_combo("Type", vars_map["type"], POINT_TYPES, lambda _event=None: self._apply_point_inspector(point, vars_map))
        self._inspector_combo("Faction", vars_map["faction"], FACTIONS, lambda _event=None: self._apply_point_inspector(point, vars_map))
        self._inspector_entry("Position X", vars_map["x"], lambda: self._apply_point_inspector(point, vars_map))
        self._inspector_entry("Position Y", vars_map["y"], lambda: self._apply_point_inspector(point, vars_map))
        self._inspector_entry("Radius", vars_map["radius"], lambda: self._apply_point_inspector(point, vars_map))
        self._inspector_entry("Facing Degrees", vars_map["facing"], lambda: self._apply_point_inspector(point, vars_map))
        self._inspector_entry("Slot Count", vars_map["slotCount"], lambda: self._apply_point_inspector(point, vars_map))

    def render_wall_inspector(self, wall: dict) -> None:
        vars_map = {
            "faction": tk.StringVar(value=wall["faction"]),
            "thickness": tk.StringVar(value=str(wall["thickness"])),
            "ax": tk.StringVar(value=str(wall["a"]["x"])),
            "ay": tk.StringVar(value=str(wall["a"]["y"])),
            "bx": tk.StringVar(value=str(wall["b"]["x"])),
            "by": tk.StringVar(value=str(wall["b"]["y"])),
        }

        ttk.Label(self.inspector_body, text=f"Wall Id: {wall['id']}").pack(anchor="w", pady=(0, 8))
        self._inspector_combo("Faction", vars_map["faction"], FACTIONS, lambda _event=None: self._apply_wall_inspector(wall, vars_map))
        self._inspector_entry("Thickness", vars_map["thickness"], lambda: self._apply_wall_inspector(wall, vars_map))
        self._inspector_entry("A X", vars_map["ax"], lambda: self._apply_wall_inspector(wall, vars_map))
        self._inspector_entry("A Y", vars_map["ay"], lambda: self._apply_wall_inspector(wall, vars_map))
        self._inspector_entry("B X", vars_map["bx"], lambda: self._apply_wall_inspector(wall, vars_map))
        self._inspector_entry("B Y", vars_map["by"], lambda: self._apply_wall_inspector(wall, vars_map))

    def render_agent_inspector(self, agent: dict) -> None:
        vars_map = {
            "label": tk.StringVar(value=agent["label"]),
            "x": tk.StringVar(value=str(round(agent["position"]["x"], 2))),
            "y": tk.StringVar(value=str(round(agent["position"]["y"], 2))),
            "speed": tk.StringVar(value=str(round(agent["moveSpeed"], 2))),
            "heading": tk.StringVar(value=str(round(math.degrees(agent["headingRadians"]), 2))),
        }
        ttk.Label(
            self.inspector_body,
            text="Runtime-only Roman agent. These edits do not change the saved map layout.",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        self._inspector_entry("Label", vars_map["label"], lambda: self._apply_agent_inspector(agent, vars_map))
        self._inspector_entry("Position X", vars_map["x"], lambda: self._apply_agent_inspector(agent, vars_map))
        self._inspector_entry("Position Y", vars_map["y"], lambda: self._apply_agent_inspector(agent, vars_map))
        self._inspector_entry("Move Speed", vars_map["speed"], lambda: self._apply_agent_inspector(agent, vars_map))
        self._inspector_entry("Heading Degrees", vars_map["heading"], lambda: self._apply_agent_inspector(agent, vars_map))

    def _inspector_entry(self, label: str, variable: tk.StringVar, callback) -> None:
        frame = ttk.Frame(self.inspector_body)
        frame.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=label).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=variable)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda _event: callback())
        entry.bind("<FocusOut>", lambda _event: callback())

    def _inspector_combo(self, label: str, variable: tk.StringVar, values: list[str], callback) -> None:
        frame = ttk.Frame(self.inspector_body)
        frame.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=label).pack(anchor="w")
        combo = ttk.Combobox(frame, textvariable=variable, values=values, state="readonly")
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", callback)

    def _apply_zone_inspector(self, zone: dict, vars_map: dict[str, tk.StringVar]) -> None:
        before_state = self.capture_state()
        try:
            zone["label"] = vars_map["label"].get().strip() or zone["label"]
            zone["type"] = vars_map["type"].get()
            zone["faction"] = vars_map["faction"].get()
            zone["center"]["x"] = float(vars_map["x"].get())
            zone["center"]["y"] = float(vars_map["y"].get())
            zone["size"]["x"] = max(50.0, float(vars_map["width"].get()))
            zone["size"]["y"] = max(50.0, float(vars_map["height"].get()))
            zone["yawRadians"] = math.radians(float(vars_map["yaw"].get()))
            zone["color"] = semantic_zone_color(zone["type"], vars_map["color"].get().strip() or zone["color"])
        except ValueError:
            self.status_var.set("Zone inspector ignored until the numbers are valid.")
            return
        self.commit_layout_change(before_state, "Edited zone. Changes are not saved yet.")

    def _apply_point_inspector(self, point: dict, vars_map: dict[str, tk.StringVar]) -> None:
        before_state = self.capture_state()
        try:
            point["label"] = vars_map["label"].get().strip() or point["label"]
            point["type"] = vars_map["type"].get()
            point["faction"] = vars_map["faction"].get()
            point["position"]["x"] = float(vars_map["x"].get())
            point["position"]["y"] = float(vars_map["y"].get())
            point["radius"] = max(10.0, float(vars_map["radius"].get()))
            point["facingRadians"] = math.radians(float(vars_map["facing"].get()))
            point["slotCount"] = max(0, int(float(vars_map["slotCount"].get())))
        except ValueError:
            self.status_var.set("Location inspector ignored until the numbers are valid.")
            return
        self.commit_layout_change(before_state, "Edited location. Changes are not saved yet.")

    def _apply_wall_inspector(self, wall: dict, vars_map: dict[str, tk.StringVar]) -> None:
        before_state = self.capture_state()
        try:
            wall["faction"] = vars_map["faction"].get()
            wall["thickness"] = max(10.0, float(vars_map["thickness"].get()))
            wall["a"]["x"] = float(vars_map["ax"].get())
            wall["a"]["y"] = float(vars_map["ay"].get())
            wall["b"]["x"] = float(vars_map["bx"].get())
            wall["b"]["y"] = float(vars_map["by"].get())
        except ValueError:
            self.status_var.set("Wall inspector ignored until the numbers are valid.")
            return
        self.commit_layout_change(before_state, "Edited wall. Changes are not saved yet.")

    def _apply_agent_inspector(self, agent: dict, vars_map: dict[str, tk.StringVar]) -> None:
        try:
            agent["label"] = vars_map["label"].get().strip() or agent["label"]
            agent["moveSpeed"] = max(25.0, float(vars_map["speed"].get()))
            agent["headingRadians"] = math.radians(float(vars_map["heading"].get()))
            agent["targetHeadingRadians"] = agent["headingRadians"]
            target_position = {
                "x": float(vars_map["x"].get()),
                "y": float(vars_map["y"].get()),
            }
        except ValueError:
            self.status_var.set("Agent inspector ignored until the numbers are valid.")
            return
        clamped_position, _, _ = self.clamp_agent_position(agent, target_position)
        agent["position"] = clamped_position
        self.status_var.set("Edited runtime agent state.")
        self.render_all()

    def get_selected_item(self) -> dict | None:
        if self.selected_kind == "agent":
            return self.get_agent_by_id(self.selected_id)
        items = self.layout[f"{self.selected_kind}s"] if self.selected_kind in {"zone", "point", "wall"} else []
        for item in items:
            if item["id"] == self.selected_id:
                return item
        return None

    def get_item_by_kind_and_id(self, kind: str, item_id: str | None) -> dict | None:
        if kind == "agent":
            return self.get_agent_by_id(item_id)
        if item_id is None or kind not in {"zone", "point", "wall"}:
            return None
        for item in self.layout[f"{kind}s"]:
            if item["id"] == item_id:
                return item
        return None

    def clear_selection(self) -> None:
        self.selected_kind = "zone"
        self.selected_id = None

    def is_background_zone(self, zone: dict) -> bool:
        return zone["type"] in BACKGROUND_ZONE_TYPES

    def hover_target_from_hit(self, hit: dict | None) -> tuple[str | None, str | None]:
        if not hit:
            return (None, None)
        if hit["kind"] == "agent":
            return ("agent", hit["id"])
        if hit["kind"] == "zone":
            return ("zone", hit["id"])
        if hit["kind"] == "point":
            return ("point", hit["id"])
        if hit["kind"] == "wall":
            return ("wall", hit["id"])
        return (None, None)

    def set_hover_target(self, kind: str | None, item_id: str | None) -> bool:
        if self.hover_kind == kind and self.hover_id == item_id:
            return False
        self.hover_kind = kind
        self.hover_id = item_id
        return True

    def on_tree_select(self, _event=None) -> None:
        if self.suppress_tree_event:
            return
        selection = self.tree.selection()
        if not selection:
            return
        iid = selection[0]
        if iid.startswith("group-"):
            return
        kind, item_id = iid.split(":", 1)
        if kind == self.selected_kind and item_id == self.selected_id:
            return
        self.selected_kind = kind
        self.selected_id = item_id
        self.render_all()

    def current_label_mode(self) -> str:
        mode = self.layout["editor"].get("labelMode", "Adaptive")
        return mode if mode in MAP_LABEL_MODES else "Hover"

    def zone_area(self, zone: dict) -> float:
        return float(zone["size"]["x"]) * float(zone["size"]["y"])

    def should_draw_zone_label(self, zone: dict) -> bool:
        if not self.layout["root"]["drawLabels"]:
            return False
        mode = self.current_label_mode()
        is_hovered = self.hover_kind == "zone" and self.hover_id == zone["id"]
        if mode == "Hover":
            return is_hovered
        if mode == "All":
            return True
        is_selected = self.selected_kind == "zone" and self.selected_id == zone["id"]
        if mode == "Selected":
            return is_selected
        if is_selected:
            return True
        if zone["type"] in REGION_ZONE_TYPES or zone["type"] == "Camp":
            return True
        if zone["type"] in SMALL_ZONE_TYPES:
            return self.view_zoom >= 1.75
        return self.zone_area(zone) >= 2_600_000 or self.view_zoom >= 1.55

    def should_draw_point_label(self, point: dict) -> bool:
        if not self.layout["root"]["drawLabels"]:
            return False
        mode = self.current_label_mode()
        is_hovered = self.hover_kind == "point" and self.hover_id == point["id"]
        if mode == "Hover":
            return is_hovered
        is_selected = self.selected_kind == "point" and self.selected_id == point["id"]
        if mode == "All":
            return True
        if mode == "Selected":
            return is_selected
        if is_selected:
            return True
        if self.view_zoom >= 2.0:
            return True
        return self.view_zoom >= 1.45 and point["type"] in MAJOR_POINT_TYPES

    def expanded_bbox(self, bbox: tuple[float, float, float, float], pad_x: float, pad_y: float) -> tuple[float, float, float, float]:
        return (
            bbox[0] - pad_x,
            bbox[1] - pad_y,
            bbox[2] + pad_x,
            bbox[3] + pad_y,
        )

    def bbox_intersects(self, left: tuple[float, float, float, float], right: tuple[float, float, float, float], pad: float = 4.0) -> bool:
        return not (
            left[2] + pad < right[0]
            or left[0] - pad > right[2]
            or left[3] + pad < right[1]
            or left[1] - pad > right[3]
        )

    def bbox_inside_canvas(self, bbox: tuple[float, float, float, float], pad: float = 4.0) -> bool:
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        return bbox[0] >= pad and bbox[1] >= pad and bbox[2] <= width - pad and bbox[3] <= height - pad

    def register_label_box(self, bbox: tuple[float, float, float, float]) -> None:
        self.label_boxes.append(bbox)

    def label_conflicts(self, bbox: tuple[float, float, float, float]) -> bool:
        return any(self.bbox_intersects(bbox, existing) for existing in self.label_boxes)

    def closest_point_on_bbox(self, point_x: float, point_y: float, bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        return (
            clamp(point_x, bbox[0], bbox[2]),
            clamp(point_y, bbox[1], bbox[3]),
        )

    def draw_badge_label(
        self,
        x: float,
        y: float,
        text: str,
        *,
        anchor: str = "center",
        font: tuple = ("Segoe UI", 10, "bold"),
        text_fill: str = "#1f1a15",
        background_fill: str = "#f3ede2",
        outline: str = "#9b907d",
        pad_x: float = 8.0,
        pad_y: float = 4.0,
        register: bool = True,
        allow_overlap: bool = True,
    ) -> tuple[float, float, float, float] | None:
        text_id = self.canvas.create_text(
            x,
            y,
            text=text,
            anchor=anchor,
            font=font,
            fill=text_fill,
            tags=(LABEL_TEXT_TAG,),
        )
        raw_bbox = self.canvas.bbox(text_id)
        if raw_bbox is None:
            self.canvas.delete(text_id)
            return None
        bbox = self.expanded_bbox(raw_bbox, pad_x, pad_y)
        if (not allow_overlap) and (self.label_conflicts(bbox) or not self.bbox_inside_canvas(bbox)):
            self.canvas.delete(text_id)
            return None
        rect_id = self.canvas.create_rectangle(
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3],
            fill=background_fill,
            outline=outline,
            width=1,
            tags=(LABEL_BG_TAG,),
        )
        self.canvas.tag_raise(text_id, rect_id)
        if register:
            self.register_label_box(bbox)
        return bbox

    def raise_overlay_layers(self) -> None:
        self.canvas.tag_raise(FRAME_TAG)
        self.canvas.tag_raise(HANDLE_TAG)
        self.canvas.tag_raise(LABEL_LINE_TAG)
        self.canvas.tag_raise(LABEL_BG_TAG)
        self.canvas.tag_raise(LABEL_TEXT_TAG)

    def zone_screen_bounds(self, zone: dict) -> tuple[float, float, float, float]:
        corners = [self.world_to_canvas(corner) for corner in self.zone_corners(zone)]
        xs = [corner["x"] for corner in corners]
        ys = [corner["y"] for corner in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    def zone_label_position(self, zone: dict) -> tuple[float, float, str]:
        bounds = self.zone_screen_bounds(zone)
        if zone["type"] == "Camp":
            return ((bounds[0] + bounds[2]) * 0.5, max(18.0, bounds[1] - 10), "s")
        if zone["type"] in SMALL_ZONE_TYPES:
            return (bounds[0] + 10, max(18.0, bounds[1] + 10), "nw")
        center = self.world_to_canvas(zone["center"])
        return (center["x"], center["y"], "center")

    def small_zone_label_candidates(self, zone: dict) -> list[tuple[float, float, str]]:
        bounds = self.zone_screen_bounds(zone)
        center_x = (bounds[0] + bounds[2]) * 0.5
        center_y = (bounds[1] + bounds[3]) * 0.5
        return [
            (bounds[0] + 10, max(18.0, bounds[1] + 10), "nw"),
            (bounds[2] - 10, max(18.0, bounds[1] + 10), "ne"),
            (bounds[0] + 10, bounds[3] - 10, "sw"),
            (bounds[2] - 10, bounds[3] - 10, "se"),
            (center_x, max(18.0, bounds[1] - 10), "s"),
            (center_x, bounds[3] + 10, "n"),
            (center_x, center_y, "center"),
        ]

    def zone_fill_color(self, zone: dict) -> str:
        mix_weight = 0.60 if not (self.selected_kind == "zone" and self.selected_id == zone["id"]) else 0.48
        return blend_hex(zone["color"], CANVAS_BACKGROUND, mix_weight)

    def point_label_candidates(self, point: dict, screen: dict, radius: float) -> list[tuple[float, float, str]]:
        base = radius + 16
        return [
            (screen["x"] + base, screen["y"], "w"),
            (screen["x"] + base, screen["y"] - base * 0.72, "sw"),
            (screen["x"] + base, screen["y"] + base * 0.72, "nw"),
            (screen["x"] - base, screen["y"], "e"),
            (screen["x"] - base, screen["y"] - base * 0.72, "se"),
            (screen["x"] - base, screen["y"] + base * 0.72, "ne"),
            (screen["x"], screen["y"] - base, "s"),
            (screen["x"], screen["y"] + base, "n"),
            (screen["x"] + base * 1.45, screen["y"] - base * 0.25, "w"),
            (screen["x"] - base * 1.45, screen["y"] - base * 0.25, "e"),
        ]

    def draw_point_labels(self) -> None:
        visible_points = [point for point in self.layout["points"] if self.should_draw_point_label(point)]
        visible_points.sort(
            key=lambda point: (
                0 if (self.selected_kind == "point" and self.selected_id == point["id"]) else 1,
                0 if point["type"] in MAJOR_POINT_TYPES else 1,
                -point["radius"],
            )
        )
        for point in visible_points:
            screen = self.world_to_canvas(point["position"])
            radius = self.point_visual_radius_pixels(point)
            color = semantic_location_color(point) or "#8a7d6a"
            badge_fill = blend_hex(color, CANVAS_BACKGROUND, 0.74)
            badge_outline = blend_hex(color, "#6c665b", 0.30)
            font_size = max(9, int(self.layout["editor"]["labelFontSize"]) - 1)

            for candidate_x, candidate_y, anchor in self.point_label_candidates(point, screen, radius):
                bbox = self.draw_badge_label(
                    candidate_x,
                    candidate_y,
                    point["label"],
                    anchor=anchor,
                    font=("Segoe UI", font_size, "bold" if point["type"] in MAJOR_POINT_TYPES else "normal"),
                    text_fill="#1f1a15",
                    background_fill=badge_fill,
                    outline=badge_outline,
                    pad_x=7.0,
                    pad_y=3.0,
                    register=True,
                    allow_overlap=False,
                )
                if bbox is None:
                    continue
                line_end = self.closest_point_on_bbox(screen["x"], screen["y"], bbox)
                if distance({"x": screen["x"], "y": screen["y"]}, {"x": line_end[0], "y": line_end[1]}) > radius + 10:
                    self.canvas.create_line(
                        screen["x"],
                        screen["y"],
                        line_end[0],
                        line_end[1],
                        fill=badge_outline,
                        width=1,
                        tags=(LABEL_LINE_TAG,),
                    )
                break

    def render_canvas(self) -> None:
        self.canvas.delete("all")
        self.label_boxes = []
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        view = self.compute_view(width, height)
        self.view = view

        self.canvas.create_rectangle(0, 0, width, height, fill=CANVAS_BACKGROUND, outline="")

        if self.layout["root"]["drawGrid"]:
            for x in range(0, self.layout["root"]["gridSize"]["x"] + 1, 4):
                world_x = x * self.layout["root"]["cellSize"]
                top = self.world_to_canvas({"x": world_x, "y": 0})
                bottom = self.world_to_canvas({"x": world_x, "y": view["worldHeight"]})
                self.canvas.create_line(top["x"], top["y"], bottom["x"], bottom["y"], fill="#ddd3c0")
            for y in range(0, self.layout["root"]["gridSize"]["y"] + 1, 4):
                world_y = y * self.layout["root"]["cellSize"]
                left = self.world_to_canvas({"x": 0, "y": world_y})
                right = self.world_to_canvas({"x": view["worldWidth"], "y": world_y})
                self.canvas.create_line(left["x"], left["y"], right["x"], right["y"], fill="#ddd3c0")

        if self.layout["root"]["drawLayout"]:
            for zone in sorted(self.layout["zones"], key=lambda item: item.get("priority", 0)):
                self.draw_zone(zone)
            for wall in self.layout["walls"]:
                self.draw_wall(wall)
            for point in self.layout["points"]:
                self.draw_point(point)
            for agent in self.agents:
                self.draw_agent(agent)
            self.draw_point_labels()
            self.draw_agent_labels()

        selected = self.get_selected_item()
        if selected and self.selected_kind in {"zone", "point", "wall"} and not self.freeze_layout_var.get():
            self.draw_handles(selected)

        top_left = self.world_to_canvas({"x": 0, "y": 0})
        bottom_right = self.world_to_canvas({"x": view["worldWidth"], "y": view["worldHeight"]})
        self.canvas.create_rectangle(
            top_left["x"],
            top_left["y"],
            bottom_right["x"],
            bottom_right["y"],
            outline="#8a7d6a",
            width=2,
            tags=(FRAME_TAG,),
        )
        self.raise_overlay_layers()

    def compute_view(self, width: int, height: int) -> dict:
        world_width, world_height = self.world_dimensions()
        base_scale = self.base_view_scale(width, height)
        scale = base_scale * self.view_zoom
        center = self.clamp_view_center(self.view_center, scale, width, height, world_width, world_height)
        self.view_center = center
        draw_width = world_width * scale
        draw_height = world_height * scale
        offset_x = width * 0.5 - center["x"] * scale
        offset_y = height * 0.5 - center["y"] * scale
        return {
            "width": width,
            "height": height,
            "worldWidth": world_width,
            "worldHeight": world_height,
            "baseScale": base_scale,
            "scale": scale,
            "drawWidth": draw_width,
            "drawHeight": draw_height,
            "offsetX": offset_x,
            "offsetY": offset_y,
        }

    def world_to_canvas(self, point: dict) -> dict:
        return {
            "x": self.view["offsetX"] + point["x"] * self.view["scale"],
            "y": self.view["offsetY"] + point["y"] * self.view["scale"],
        }

    def canvas_to_world(self, point: dict) -> dict:
        return {
            "x": (point["x"] - self.view["offsetX"]) / self.view["scale"],
            "y": (point["y"] - self.view["offsetY"]) / self.view["scale"],
        }

    def draw_zone(self, zone: dict) -> None:
        corners = self.zone_corners(zone)
        fill = self.zone_fill_color(zone)
        outline = "#294fb6" if self.selected_kind == "zone" and self.selected_id == zone["id"] else blend_hex(zone["color"], "#5f564a", 0.42)
        width = 3 if self.selected_kind == "zone" and self.selected_id == zone["id"] else 2 if zone["type"] == "Camp" else 1
        label_font_size = max(9, int(self.layout["editor"]["labelFontSize"]))
        points = []
        for corner in corners:
            screen = self.world_to_canvas(corner)
            points.extend([screen["x"], screen["y"]])
        self.canvas.create_polygon(points, fill=fill, outline=outline, width=width)
        if self.should_draw_zone_label(zone):
            badge_fill = blend_hex(zone["color"], CANVAS_BACKGROUND, 0.72 if zone["type"] in SMALL_ZONE_TYPES else 0.66)
            badge_outline = blend_hex(zone["color"], "#5f564a", 0.35)
            if zone["type"] in SMALL_ZONE_TYPES:
                for candidate_x, candidate_y, anchor in self.small_zone_label_candidates(zone):
                    bbox = self.draw_badge_label(
                        candidate_x,
                        candidate_y,
                        zone["label"],
                        anchor=anchor,
                        font=("Segoe UI", max(8, label_font_size - 1), "bold"),
                        text_fill="#1f1a15",
                        background_fill=badge_fill,
                        outline=badge_outline,
                        pad_x=7.0,
                        pad_y=3.0,
                        register=True,
                        allow_overlap=False,
                    )
                    if bbox is not None:
                        break
                else:
                    if not (self.selected_kind == "zone" and self.selected_id == zone["id"]):
                        return
                    label_x, label_y, anchor = self.zone_label_position(zone)
                    self.draw_badge_label(
                        label_x,
                        label_y,
                        zone["label"],
                        anchor=anchor,
                        font=("Segoe UI", max(8, label_font_size - 1), "bold"),
                        text_fill="#1f1a15",
                        background_fill=badge_fill,
                        outline=badge_outline,
                        pad_x=7.0,
                        pad_y=3.0,
                        register=True,
                        allow_overlap=True,
                    )
            else:
                label_x, label_y, anchor = self.zone_label_position(zone)
                self.draw_badge_label(
                    label_x,
                    label_y,
                    zone["label"],
                    anchor=anchor,
                    font=("Segoe UI", label_font_size, "bold"),
                    text_fill="#1f1a15",
                    background_fill=badge_fill,
                    outline=badge_outline,
                    pad_x=8.0,
                    pad_y=4.0,
                    register=True,
                    allow_overlap=True,
                )

    def draw_wall(self, wall: dict) -> None:
        a = self.world_to_canvas(wall["a"])
        b = self.world_to_canvas(wall["b"])
        color = "#294fb6" if self.selected_kind == "wall" and self.selected_id == wall["id"] else "#6c665b"
        width = max(4, wall["thickness"] * self.view["scale"] * 0.32)
        self.canvas.create_line(a["x"], a["y"], b["x"], b["y"], fill=color, width=width, capstyle=tk.ROUND)

    def draw_point(self, point: dict) -> None:
        screen = self.world_to_canvas(point["position"])
        color = semantic_location_color(point)
        arrow_color = color or "#7a6b56"
        radius = self.point_visual_radius_pixels(point)
        is_selected = self.selected_kind == "point" and self.selected_id == point["id"]
        outline = "#1f1a15" if is_selected else "#6c665b"
        outline_width = 3 if is_selected else 2
        self.canvas.create_oval(
            screen["x"] - radius,
            screen["y"] - radius,
            screen["x"] + radius,
            screen["y"] + radius,
            fill="#ffffff",
            outline=outline,
            width=outline_width,
        )
        inner_radius = self.location_inner_radius_pixels(point)
        if color:
            self.canvas.create_oval(
                screen["x"] - inner_radius,
                screen["y"] - inner_radius,
                screen["x"] + inner_radius,
                screen["y"] + inner_radius,
                fill=color,
                outline="",
            )
        facing_length = radius + max(16, point["radius"] * self.view["scale"] * 0.14)
        self.canvas.create_line(
            screen["x"],
            screen["y"],
            screen["x"] + math.cos(point["facingRadians"]) * facing_length,
            screen["y"] + math.sin(point["facingRadians"]) * facing_length,
            fill=arrow_color,
            width=3 if is_selected else 2,
            arrow=tk.LAST,
        )

    def point_visual_radius_pixels(self, point: dict) -> float:
        return max(6.0, point["radius"] * self.view["scale"] * 0.12)

    def location_inner_radius_pixels(self, point: dict) -> float:
        outer_radius = self.point_visual_radius_pixels(point)
        ring_thickness = clamp(outer_radius * 0.18, 2.3, 4.0)
        return max(3.0, outer_radius - ring_thickness)

    def point_hit_radius_world(self, point: dict) -> float:
        return (self.point_visual_radius_pixels(point) + 8.0) / self.view["scale"]

    def zone_local_corners(self, zone: dict) -> list[dict]:
        half_x = zone["size"]["x"] * 0.5
        half_y = zone["size"]["y"] * 0.5
        return [
            {"x": -half_x, "y": -half_y},
            {"x": half_x, "y": -half_y},
            {"x": half_x, "y": half_y},
            {"x": -half_x, "y": half_y},
        ]

    def zone_corners(self, zone: dict) -> list[dict]:
        result = []
        for local in self.zone_local_corners(zone):
            rotated = local_to_world(local, zone["yawRadians"])
            result.append({
                "x": zone["center"]["x"] + rotated["x"],
                "y": zone["center"]["y"] + rotated["y"],
            })
        return result

    def point_radius_handle(self, point: dict) -> dict:
        return {
            "x": point["position"]["x"] + point["radius"],
            "y": point["position"]["y"],
        }

    def point_facing_handle(self, point: dict) -> dict:
        distance_value = point["radius"] + 150
        return {
            "x": point["position"]["x"] + math.cos(point["facingRadians"]) * distance_value,
            "y": point["position"]["y"] + math.sin(point["facingRadians"]) * distance_value,
        }

    def draw_handles(self, item: dict) -> None:
        if self.selected_kind == "zone":
            for corner in self.zone_corners(item):
                screen = self.world_to_canvas(corner)
                self.canvas.create_rectangle(
                    screen["x"] - 6,
                    screen["y"] - 6,
                    screen["x"] + 6,
                    screen["y"] + 6,
                    fill="white",
                    outline="#294fb6",
                    width=2,
                    tags=(HANDLE_TAG,),
                )
        elif self.selected_kind == "point":
            for handle in (self.point_radius_handle(item), self.point_facing_handle(item)):
                screen = self.world_to_canvas(handle)
                self.canvas.create_oval(
                    screen["x"] - 6,
                    screen["y"] - 6,
                    screen["x"] + 6,
                    screen["y"] + 6,
                    fill="white",
                    outline="#294fb6",
                    width=2,
                    tags=(HANDLE_TAG,),
                )
        else:
            for endpoint in (item["a"], item["b"]):
                screen = self.world_to_canvas(endpoint)
                self.canvas.create_oval(
                    screen["x"] - 6,
                    screen["y"] - 6,
                    screen["x"] + 6,
                    screen["y"] + 6,
                    fill="white",
                    outline="#294fb6",
                    width=2,
                    tags=(HANDLE_TAG,),
                )

    def snap(self, value: float) -> float:
        if not self.layout["editor"]["snapToGrid"]:
            return value
        step = max(1, self.layout["editor"]["snapSize"])
        return round(value / step) * step

    def snap_point(self, point: dict) -> dict:
        return {
            "x": self.snap(point["x"]),
            "y": self.snap(point["y"]),
        }

    def get_handle_hit(self, world_point: dict) -> dict | None:
        if self.freeze_layout_var.get():
            return None
        selected = self.get_selected_item()
        if selected is None:
            return None
        handle_radius = 14 / self.view["scale"]
        if self.selected_kind == "zone":
            for corner_index, corner in enumerate(self.zone_corners(selected)):
                if distance(world_point, corner) <= handle_radius:
                    return {"kind": "zone-handle", "id": selected["id"], "cornerIndex": corner_index}
        elif self.selected_kind == "point":
            if distance(world_point, self.point_radius_handle(selected)) <= handle_radius:
                return {"kind": "point-radius", "id": selected["id"]}
            if distance(world_point, self.point_facing_handle(selected)) <= handle_radius:
                return {"kind": "point-facing", "id": selected["id"]}
        elif self.selected_kind == "wall":
            if distance(world_point, selected["a"]) <= handle_radius:
                return {"kind": "wall-endpoint", "id": selected["id"], "endpoint": "a"}
            if distance(world_point, selected["b"]) <= handle_radius:
                return {"kind": "wall-endpoint", "id": selected["id"], "endpoint": "b"}
        return None

    def hit_test(self, world_point: dict) -> dict | None:
        agent_hit = self.get_agent_hit(world_point)
        if agent_hit:
            return agent_hit

        handle_hit = self.get_handle_hit(world_point)
        if handle_hit:
            return handle_hit

        for point in reversed(self.layout["points"]):
            if distance(world_point, point["position"]) <= self.point_hit_radius_world(point):
                return {"kind": "point", "id": point["id"]}

        for wall in reversed(self.layout["walls"]):
            if point_to_segment_distance(world_point, wall["a"], wall["b"]) <= max(wall["thickness"] * 0.7, 140):
                return {"kind": "wall", "id": wall["id"]}

        ordered_zones = sorted(self.layout["zones"], key=lambda item: item.get("priority", 0), reverse=True)
        for zone in ordered_zones:
            local = world_to_local(world_point, zone["center"], zone["yawRadians"])
            if abs(local["x"]) <= zone["size"]["x"] * 0.5 and abs(local["y"]) <= zone["size"]["y"] * 0.5:
                return {"kind": "zone", "id": zone["id"]}
        return None

    def on_canvas_press(self, event: tk.Event) -> None:
        if self.view is None:
            return
        self.canvas.focus_set()
        world_point = self.canvas_to_world({"x": event.x, "y": event.y})
        hit = self.hit_test(world_point)
        hover_kind, hover_id = self.hover_target_from_hit(hit)
        self.set_hover_target(hover_kind, hover_id)
        if not hit:
            if self.selected_id is not None:
                self.clear_selection()
                self.status_var.set("Selection cleared.")
                self.render_all()
            return

        if hit["kind"] == "zone":
            zone = self.get_item_by_kind_and_id("zone", hit["id"])
            if zone is not None and self.is_background_zone(zone):
                self.clear_selection()
                self.status_var.set("Selection cleared.")
                self.render_all()
                return

        if hit["kind"] in {"zone", "zone-handle", "point", "point-radius", "point-facing", "wall", "wall-endpoint"} and self.freeze_layout_var.get():
            self.clear_selection()
            self.status_var.set("Layout is frozen. Uncheck Freeze Layout to edit the map.")
            self.render_all()
            return

        if hit["kind"] == "agent":
            self.selected_kind = "agent"
            self.selected_id = hit["id"]
        elif hit["kind"].startswith("zone"):
            self.selected_kind = "zone"
            self.selected_id = hit["id"]
        elif hit["kind"].startswith("point"):
            self.selected_kind = "point"
            self.selected_id = hit["id"]
        else:
            self.selected_kind = "wall"
            self.selected_id = hit["id"]

        item = self.get_selected_item()
        if item is None:
            return

        before_state = self.capture_state()
        if hit["kind"] == "zone":
            self.drag_state = {
                "type": "move-zone",
                "beforeState": before_state,
                "offset": {
                    "x": world_point["x"] - item["center"]["x"],
                    "y": world_point["y"] - item["center"]["y"],
                },
            }
        elif hit["kind"] == "zone-handle":
            corners = self.zone_corners(item)
            opposite_corner = corners[(hit["cornerIndex"] + 2) % 4]
            self.drag_state = {
                "type": "resize-zone",
                "beforeState": before_state,
                "cornerIndex": hit["cornerIndex"],
                "oppositeCornerWorld": deep_copy(opposite_corner),
            }
        elif hit["kind"] == "point":
            self.drag_state = {
                "type": "move-point",
                "beforeState": before_state,
                "offset": {
                    "x": world_point["x"] - item["position"]["x"],
                    "y": world_point["y"] - item["position"]["y"],
                },
            }
        elif hit["kind"] == "agent":
            self.drag_state = {
                "type": "move-agent",
                "id": item["id"],
                "offset": {
                    "x": world_point["x"] - item["position"]["x"],
                    "y": world_point["y"] - item["position"]["y"],
                },
            }
        elif hit["kind"] == "point-radius":
            self.drag_state = {"type": "resize-point", "beforeState": before_state}
        elif hit["kind"] == "point-facing":
            self.drag_state = {"type": "rotate-point", "beforeState": before_state}
        elif hit["kind"] == "wall":
            self.drag_state = {
                "type": "move-wall",
                "beforeState": before_state,
                "startPointer": world_point,
                "startA": deep_copy(item["a"]),
                "startB": deep_copy(item["b"]),
            }
        elif hit["kind"] == "wall-endpoint":
            self.drag_state = {
                "type": "move-wall-endpoint",
                "beforeState": before_state,
                "endpoint": hit["endpoint"],
            }

        self.render_all()

    def on_canvas_drag(self, event: tk.Event) -> None:
        if self.view is None or self.drag_state is None:
            return
        item = self.get_selected_item()
        if item is None:
            return
        world_point = self.canvas_to_world({"x": event.x, "y": event.y})

        drag_type = self.drag_state["type"]
        if drag_type == "move-zone":
            item["center"] = self.snap_point({
                "x": world_point["x"] - self.drag_state["offset"]["x"],
                "y": world_point["y"] - self.drag_state["offset"]["y"],
            })
        elif drag_type == "resize-zone":
            opposite_corner = self.drag_state["oppositeCornerWorld"]
            item["center"] = {
                "x": (world_point["x"] + opposite_corner["x"]) * 0.5,
                "y": (world_point["y"] + opposite_corner["y"]) * 0.5,
            }
            local = world_to_local(world_point, item["center"], item["yawRadians"])
            item["size"]["x"] = max(300.0, abs(local["x"]) * 2.0)
            item["size"]["y"] = max(300.0, abs(local["y"]) * 2.0)
        elif drag_type == "move-point":
            item["position"] = self.snap_point({
                "x": world_point["x"] - self.drag_state["offset"]["x"],
                "y": world_point["y"] - self.drag_state["offset"]["y"],
            })
        elif drag_type == "move-agent":
            clamped_position, _, _ = self.clamp_agent_position(
                item,
                {
                    "x": world_point["x"] - self.drag_state["offset"]["x"],
                    "y": world_point["y"] - self.drag_state["offset"]["y"],
                },
            )
            item["position"] = clamped_position
        elif drag_type == "resize-point":
            item["radius"] = max(20.0, distance(world_point, item["position"]))
        elif drag_type == "rotate-point":
            item["facingRadians"] = math.atan2(world_point["y"] - item["position"]["y"], world_point["x"] - item["position"]["x"])
        elif drag_type == "move-wall":
            dx = world_point["x"] - self.drag_state["startPointer"]["x"]
            dy = world_point["y"] - self.drag_state["startPointer"]["y"]
            item["a"] = self.snap_point({"x": self.drag_state["startA"]["x"] + dx, "y": self.drag_state["startA"]["y"] + dy})
            item["b"] = self.snap_point({"x": self.drag_state["startB"]["x"] + dx, "y": self.drag_state["startB"]["y"] + dy})
        elif drag_type == "move-wall-endpoint":
            item[self.drag_state["endpoint"]] = self.snap_point(world_point)

        self.status_var.set("Repositioning Roman agent." if drag_type == "move-agent" else "Editing layout. Changes are not saved yet.")
        self.render_canvas()
        self.render_stats_and_labels()

    def on_canvas_release(self, _event: tk.Event) -> None:
        if self.drag_state is None:
            return
        drag_type = self.drag_state.get("type")
        before_state = self.drag_state.get("beforeState")
        self.drag_state = None
        if before_state is not None:
            self.commit_layout_change(before_state, "Edited layout. Changes are not saved yet.")
        else:
            if drag_type == "move-agent":
                self.status_var.set("Moved Roman agent.")
            self.render_all()

    def on_canvas_pan_press(self, event: tk.Event) -> None:
        if self.view is None:
            return
        self.canvas.focus_set()
        self.pan_state = {
            "pointer": {"x": event.x, "y": event.y},
            "center": deep_copy(self.view_center),
        }
        self.canvas.configure(cursor="fleur")

    def on_canvas_pan_drag(self, event: tk.Event) -> None:
        if self.pan_state is None or self.view is None:
            return
        dx = event.x - self.pan_state["pointer"]["x"]
        dy = event.y - self.pan_state["pointer"]["y"]
        self.view_center = self.clamp_view_center(
            {
                "x": self.pan_state["center"]["x"] - dx / self.view["scale"],
                "y": self.pan_state["center"]["y"] - dy / self.view["scale"],
            },
            self.view["scale"],
            self.view["width"],
            self.view["height"],
            self.view["worldWidth"],
            self.view["worldHeight"],
        )
        self.render_canvas()
        self.render_stats_and_labels()

    def on_canvas_pan_release(self, _event: tk.Event) -> None:
        self.pan_state = None
        self.canvas.configure(cursor="")

    def on_canvas_mousewheel(self, event: tk.Event) -> str:
        if self.view is None:
            return "break"
        delta = getattr(event, "delta", 0)
        if getattr(event, "num", None) == 4:
            delta = 120
        elif getattr(event, "num", None) == 5:
            delta = -120
        if delta == 0:
            return "break"
        factor = 1.12 if delta > 0 else 1 / 1.12
        self.zoom_by_factor(factor, {"x": event.x, "y": event.y})
        return "break"

    def on_canvas_motion(self, event: tk.Event) -> None:
        if self.view is None or self.drag_state is not None or self.pan_state is not None:
            return
        world_point = self.canvas_to_world({"x": event.x, "y": event.y})
        hit = self.hit_test(world_point)
        hover_kind, hover_id = self.hover_target_from_hit(hit)
        hover_changed = self.set_hover_target(hover_kind, hover_id)
        if hit and hit["kind"] == "agent":
            self.canvas.configure(cursor="hand2")
        elif hit and hit["kind"] in {"zone-handle", "point-radius", "point-facing", "wall-endpoint"}:
            self.canvas.configure(cursor="crosshair")
        elif hit and not (self.freeze_layout_var.get() and hit["kind"] in {"zone", "point", "wall"}):
            self.canvas.configure(cursor="fleur")
        else:
            self.canvas.configure(cursor="")
        if hover_changed:
            self.render_canvas()

    def on_canvas_leave(self, _event: tk.Event) -> None:
        self.canvas.configure(cursor="")
        if self.set_hover_target(None, None):
            self.render_canvas()


def main() -> None:
    try:
        configure_windows_app_identity()
        root = tk.Tk()
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        LayoutEditorApp(root)
        root.update_idletasks()
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(250, lambda: root.attributes("-topmost", False))
        root.focus_force()
        root.mainloop()
    except Exception as error:
        try:
            fallback = tk.Tk()
            fallback.withdraw()
            messagebox.showerror("Modeler Layout Editor", f"Editor failed to launch.\n\n{error}")
            fallback.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
