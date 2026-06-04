from __future__ import annotations

import importlib
import math
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import agent_panel
import agent_state
import agent_brains
import editor_runtime
import living_body
import perception
import sim_resources
from editor_runtime import RomanSimulationRuntime
from editor_view_state import read_saved_view, write_saved_view
from layout_document import deep_copy, merge_layout_save, normalize_layout, read_json, write_json
from sim_geometry import clamp, distance, local_to_world, point_to_segment_distance, world_to_local


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
RENDER_FRAME_INTERVAL_SECONDS = 1.0 / 30.0
INTERACTION_PULSE_DURATION_SECONDS = 0.9
SIMULATION_SPEED_OPTIONS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
ROMAN_SIMULATION_ZONE_ID = "zone-roman-camp"
ROMAN_AGENT_COUNT = 5
DYNAMIC_RELOAD_MODULES = [
    agent_state,
    agent_panel,
    agent_brains,
    editor_runtime,
    living_body,
    perception,
    sim_resources,
]
OMNIDIRECTIONAL_POINT_TYPES = {
    "Fire",
    "Basin",
    "JarLocation",
}
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
    "JarLocation": "#d2ad58",
    "WatchTower": "#8257e5",
    "Gate": "",
}
INTERACTION_COLORS = {
    "drink": "#2f6dff",
    "eat": "#7a1f19",
    "pick_up_jar": "#d2ad58",
    "fill_jar": "#3e8bff",
    "fill_basin": "#2f6dff",
    "drop_jar": "#d2ad58",
    "attack_target": "#d84f35",
    "place_raw_pig": "#f2d62d",
    "pick_up_dead_pig": "#8d5a32",
    "drop_dead_pig": "#8d5a32",
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
    "JarLocation",
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


def point_has_facing(point: dict) -> bool:
    return point["type"] not in OMNIDIRECTIONAL_POINT_TYPES


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


class LayoutEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        apply_window_icon(self.root)
        self.window_title_base = "Modeler Layout Editor"
        self.root.title(self.window_title_base)
        self.root.geometry("1500x920")
        self.root.minsize(1180, 760)
        self.loaded_build_mtime = SCRIPT_PATH.stat().st_mtime
        self.loaded_dynamic_module_mtimes = self.current_dynamic_module_mtimes()
        self.restart_needed = False
        self.dynamic_reload_needed = False

        self.default_layout = read_json(DEFAULT_LAYOUT_PATH)
        self.layout = self._load_current_layout()
        self.saved_layout = deep_copy(self.layout)
        self.dirty = False
        self.selected_kind = "zone"
        self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
        self.hover_kind = None
        self.hover_id = None
        self.last_agent_details_id = None
        self.drag_state = None
        self.pan_state = None
        self.view = None
        self.view_zoom = 1.0
        self.view_center = self.default_view_center()
        self.undo_stack: list[dict] = []
        self.max_undo_states = 80
        self.label_boxes: list[tuple[float, float, float, float]] = []
        self.canvas_frame = None
        self.agent_panel_view = None
        self.suppress_tree_event = False
        self.status_var = tk.StringVar(value="Ready. Click Save Layout to keep changes in data/current_layout.json.")
        self.meta_var = tk.StringVar()
        self.selection_var = tk.StringVar()
        self.play_button_var = tk.StringVar(value="Play")
        self.sim_summary_var = tk.StringVar()
        self.sim_speed_var = tk.StringVar(value=format_speed_label(1.0))
        self.freeze_layout_var = tk.BooleanVar(value=False)
        self.last_simulation_tick = time.perf_counter()
        self.last_canvas_render = 0.0
        self.last_agent_details_refresh = 0.0
        self.interaction_pulses: list[dict] = []
        self.spacebar_toggle_pending = False
        self.restore_saved_view_state()
        self.simulation = RomanSimulationRuntime(
            self.layout,
            spawn_zone_id=ROMAN_SIMULATION_ZONE_ID,
            agent_count=ROMAN_AGENT_COUNT,
        )

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._sync_world_controls()
        self.render_all()
        self.root.bind_all("<KeyPress-space>", self.on_spacebar_press, add="+")
        self.root.bind_all("<KeyRelease-space>", self.on_spacebar_release, add="+")
        self.root.bind_all("<KeyPress-KP_Add>", self.on_simulation_speed_key, add="+")
        self.root.bind_all("<KeyPress-KP_Subtract>", self.on_simulation_speed_key, add="+")
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
        return normalize_layout(
            payload,
            zone_color_resolver=semantic_zone_color,
            updated_default=today_stamp(),
        )

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
            text="Roman prototype: five agents spawn in the Roman camp, then wander across the full map at 60 FPS. Play keeps the layout live unless Freeze Layout is checked.",
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
        self.canvas_frame = canvas_frame

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

        self.agent_panel_view = agent_panel.AgentPanelView(
            canvas_frame,
            self.on_agent_details_mousewheel,
            refresh_callback=self.handle_command_bridge_refresh,
        )
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

    def on_agent_details_mousewheel(self, event: tk.Event) -> str:
        if self.agent_panel_view is not None:
            self.agent_panel_view.scroll(event)
        return "break"

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
        self.view_zoom, self.view_center = read_saved_view(self.layout, self.default_view_center())

    def persist_saved_view_state(self) -> None:
        write_saved_view(self.layout, self.view_zoom, self.view_center)

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
            for agent in self.simulation.agents:
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

    def ensure_valid_last_clicked_agent(self) -> None:
        if self.last_agent_details_id is None:
            return
        if self.get_agent_by_id(self.last_agent_details_id) is not None:
            return
        self.last_agent_details_id = None

    def remember_last_clicked_agent(self, agent_id: str | None) -> None:
        if agent_id is None:
            return
        if self.get_agent_by_id(agent_id) is None:
            return
        self.last_agent_details_id = agent_id

    def current_dynamic_module_mtimes(self) -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for module in DYNAMIC_RELOAD_MODULES:
            module_path = getattr(module, "__file__", None)
            if not module_path:
                continue
            try:
                mtimes[module.__name__] = Path(module_path).stat().st_mtime
            except OSError:
                mtimes[module.__name__] = 0.0
        return mtimes

    def rebuild_dynamic_widgets(self) -> None:
        if self.agent_panel_view is not None:
            self.agent_panel_view.destroy()
        if self.canvas_frame is not None:
            self.agent_panel_view = agent_panel.AgentPanelView(
                self.canvas_frame,
                self.on_agent_details_mousewheel,
                refresh_callback=self.handle_command_bridge_refresh,
            )

    def apply_snapshot(self, snapshot: dict) -> None:
        self.layout = self._normalize_layout(snapshot["layout"])
        self.selected_kind = snapshot.get("selected_kind", "zone")
        self.selected_id = snapshot.get("selected_id")
        self.hover_kind = None
        self.hover_id = None
        self.simulation.attach_layout(self.layout)
        self.ensure_valid_selection()
        self.ensure_valid_last_clicked_agent()
        self.dirty = self.layout != self.saved_layout
        self._sync_world_controls()

    def reload_saved_layout_if_clean(self) -> bool:
        if self.dirty:
            return False
        try:
            layout = self._normalize_layout(read_json(CURRENT_LAYOUT_PATH))
        except Exception:
            return False
        if layout == self.layout:
            return False
        self.layout = layout
        self.saved_layout = deep_copy(layout)
        self.simulation.attach_layout(self.layout)
        self.ensure_valid_selection()
        self.ensure_valid_last_clicked_agent()
        self._sync_world_controls()
        return True

    def update_meta_and_title(self) -> None:
        build_text = f"UI {format_build_stamp(self.loaded_build_mtime)}"
        reload_text = " | Refresh modules available" if self.dynamic_reload_needed else ""
        restart_text = " | Restart needed for editor shell" if self.restart_needed else ""
        dirty_suffix = " | Unsaved changes" if self.dirty else ""
        self.meta_var.set(f"Block {self.layout['block']} | {self.layout['stage']} | {self.layout['updated']} | {build_text}{reload_text}{restart_text}{dirty_suffix}")
        title = self.window_title_base
        if self.restart_needed:
            title += " - Restart Needed"
        elif self.dynamic_reload_needed:
            title += " - Module Refresh Available"
        if self.dirty:
            title += "*"
        self.root.title(title)

    def poll_for_editor_code_update(self) -> None:
        try:
            self.restart_needed = SCRIPT_PATH.stat().st_mtime > self.loaded_build_mtime + 0.5
        except OSError:
            self.restart_needed = False
        current_mtimes = self.current_dynamic_module_mtimes()
        self.dynamic_reload_needed = any(
            current_mtimes.get(name, 0.0) > self.loaded_dynamic_module_mtimes.get(name, 0.0) + 0.5
            for name in current_mtimes
        )
        self.update_meta_and_title()
        self.root.after(2500, self.poll_for_editor_code_update)

    def update_simulation_summary(self) -> None:
        self.play_button_var.set("Pause" if self.simulation.running else "Play")
        state_text = "Running" if self.simulation.running else "Paused"
        freeze_suffix = " | Layout frozen" if self.freeze_layout_var.get() else ""
        self.sim_summary_var.set(
            f"{state_text} | Sim {format_sim_time(self.simulation.time_seconds)} | {len(self.simulation.agents)} Roman agents | {format_speed_label(self.simulation.speed_multiplier)}{freeze_suffix}"
        )

    def apply_simulation_speed(self, _event=None) -> str | None:
        try:
            self.set_simulation_speed(max(0.05, float(self.sim_speed_var.get().rstrip("x"))))
        except ValueError:
            self.set_simulation_speed(1.0)
        if _event is not None:
            return "break"
        return None

    def set_simulation_speed(self, multiplier: float) -> None:
        self.simulation.speed_multiplier = max(0.05, float(multiplier))
        self.sim_speed_var.set(format_speed_label(self.simulation.speed_multiplier))
        self.update_simulation_summary()

    def nudge_simulation_speed(self, direction: int) -> None:
        current = float(self.simulation.speed_multiplier)
        if direction > 0:
            candidates = [value for value in SIMULATION_SPEED_OPTIONS if value > current + 0.001]
            next_speed = candidates[0] if candidates else SIMULATION_SPEED_OPTIONS[-1]
        else:
            candidates = [value for value in reversed(SIMULATION_SPEED_OPTIONS) if value < current - 0.001]
            next_speed = candidates[0] if candidates else SIMULATION_SPEED_OPTIONS[0]
        self.set_simulation_speed(next_speed)
        self.status_var.set(f"Simulation speed set to {format_speed_label(next_speed)}.")

    def on_simulation_speed_key(self, event: tk.Event) -> str:
        if getattr(event, "keysym", "") == "KP_Add":
            self.nudge_simulation_speed(1)
        else:
            self.nudge_simulation_speed(-1)
        return "break"

    def toggle_simulation(self) -> None:
        self.simulation.running = not self.simulation.running
        self.last_simulation_tick = time.perf_counter()
        self.status_var.set("Simulation running across the map." if self.simulation.running else "Simulation paused.")
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

    def simulation_spawn_zone(self) -> dict:
        return self.simulation.spawn_zone()

    def clamp_agent_position(self, agent: dict, position: dict) -> tuple[dict, bool, bool]:
        return self.simulation.clamp_agent_position(agent, position)

    def on_simulation_frame(self) -> None:
        now = time.perf_counter()
        real_dt = min(0.08, max(0.0, now - self.last_simulation_tick))
        self.last_simulation_tick = now
        changed = False
        if self.simulation.running and real_dt > 0.0:
            changed = self.advance_simulation(real_dt * self.simulation.speed_multiplier)
        self.prune_interaction_pulses(now)
        if changed or self.interaction_pulses:
            if now - self.last_canvas_render >= RENDER_FRAME_INTERVAL_SECONDS:
                self.last_canvas_render = now
                self.render_canvas()
                self.render_stats_and_labels()
            self.render_agent_details_panel(force=False)
        self.root.after(SIMULATION_FRAME_MS, self.on_simulation_frame)

    def advance_simulation(self, sim_dt: float) -> bool:
        dragged_agent_id = self.drag_state.get("id") if self.drag_state and self.drag_state.get("type") == "move-agent" else None
        any_changed = self.simulation.advance(sim_dt, dragged_agent_id=dragged_agent_id)
        self.collect_interaction_events()
        self.update_simulation_summary()
        return any_changed or bool(self.interaction_pulses)

    def collect_interaction_events(self) -> None:
        now = time.perf_counter()
        for event in self.simulation.consume_interaction_events():
            event["startedAt"] = now
            self.interaction_pulses.append(event)
        if len(self.interaction_pulses) > 80:
            self.interaction_pulses = self.interaction_pulses[-80:]

    def prune_interaction_pulses(self, now: float | None = None) -> None:
        if not self.interaction_pulses:
            return
        now = time.perf_counter() if now is None else now
        self.interaction_pulses = [
            pulse
            for pulse in self.interaction_pulses
            if now - pulse.get("startedAt", now) < INTERACTION_PULSE_DURATION_SECONDS
        ]

    def agent_visual_radius_pixels(self, agent: dict) -> float:
        return max(6.0, agent["radius"] * self.view["scale"] * 0.11)

    def agent_hit_radius_world(self, agent: dict) -> float:
        return (self.agent_visual_radius_pixels(agent) + 8.0) / self.view["scale"]

    def get_agent_by_id(self, agent_id: str | None) -> dict | None:
        return self.simulation.get_agent_by_id(agent_id)

    def get_agent_hit(self, world_point: dict) -> dict | None:
        for agent in reversed(self.simulation.agents):
            if distance(world_point, agent["position"]) <= self.agent_hit_radius_world(agent):
                return {"kind": "agent", "id": agent["id"]}
        return None

    def get_agent_vision_cone_hit(self, world_point: dict) -> dict | None:
        visible_agents = [
            agent
            for agent in self.simulation.agents
            if agent.get("health", {}).get("status") != "dead" and perception.is_in_vision_cone(agent, world_point)
        ]
        if not visible_agents:
            return None
        agent = min(visible_agents, key=lambda item: distance(world_point, item["position"]))
        return {"kind": "agent-vision", "id": agent["id"]}

    def should_draw_agent_label(self, agent: dict) -> bool:
        return (self.hover_kind == "agent" and self.hover_id == agent["id"]) or (
            self.selected_kind == "agent" and self.selected_id == agent["id"]
        )

    def draw_agent(self, agent: dict) -> None:
        screen = self.world_to_canvas(agent["position"])
        radius = self.agent_visual_radius_pixels(agent)
        is_dead = agent.get("health", {}).get("status") == "dead"
        fill = "#4a4640" if is_dead else blend_hex(faction_color(agent["faction"]), "#f7f4ee", 0.18)
        core_fill = "#2d2a26" if is_dead else "#f8f6f1"
        facing_fill = "#5d574f" if is_dead else "#1f1a15"
        outline = "#8a7442" if is_dead and self.selected_kind == "agent" and self.selected_id == agent["id"] else "#e3bf47" if self.selected_kind == "agent" and self.selected_id == agent["id"] else "#1f1a15"
        outline_width = 3 if self.selected_kind == "agent" and self.selected_id == agent["id"] else 2
        facing_length = radius + 8.0
        self.canvas.create_line(
            screen["x"],
            screen["y"],
            screen["x"] + math.cos(agent["headingRadians"]) * facing_length,
            screen["y"] + math.sin(agent["headingRadians"]) * facing_length,
            fill=facing_fill if is_dead else outline,
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
            fill=core_fill,
            outline="",
        )
        self.draw_agent_inventory_marker(agent, screen, radius)

    def draw_agent_inventory_marker(self, agent: dict, screen: dict, radius: float) -> None:
        inventory = agent.get("inventory", {})
        if not inventory:
            return
        marker_x = screen["x"] + radius * 0.72
        marker_y = screen["y"] - radius * 0.72
        marker_radius = max(3.0, radius * 0.26)
        if inventory.get("rawPig"):
            self.canvas.create_oval(
                marker_x - marker_radius,
                marker_y - marker_radius,
                marker_x + marker_radius,
                marker_y + marker_radius,
                fill="#9c5b26",
                outline="#4e3320",
                width=1,
            )
            return
        if inventory.get("jar"):
            fill = "#3e8bff" if inventory.get("jarFilled") else "#f6f1df"
            self.canvas.create_rectangle(
                marker_x - marker_radius,
                marker_y - marker_radius,
                marker_x + marker_radius,
                marker_y + marker_radius,
                fill=fill,
                outline="#4f5d70",
                width=1,
            )

    def draw_agent_labels(self) -> None:
        for agent in self.simulation.agents:
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
        self.simulation.clamp_all_agents_to_bounds()

    def commit_layout_change(self, before_state: dict, message: str, *, sync_world: bool = False) -> bool:
        changed = before_state["layout"] != self.layout
        if sync_world:
            self._sync_world_controls()
        if changed:
            self.record_undo_state(before_state)
            self.simulation.attach_layout(self.layout)
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
            self.simulation.attach_layout(self.layout)
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
        self.simulation.attach_layout(self.layout)
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
        disk_layout = read_json(CURRENT_LAYOUT_PATH)
        merged_layout = merge_layout_save(self.saved_layout, self.layout, disk_layout)
        if "points" in merged_layout:
            merged_layout["locations"] = deep_copy(merged_layout["points"])
        self.layout = self._normalize_layout(merged_layout)
        write_json(CURRENT_LAYOUT_PATH, self.layout)
        self.saved_layout = deep_copy(self.layout)
        self.simulation.attach_layout(self.layout)
        self.ensure_valid_selection()
        self.ensure_valid_last_clicked_agent()
        self._sync_world_controls()
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

    def handle_command_bridge_refresh(self, _command: dict) -> str:
        self.refresh_app(show_error_dialog=False, raise_errors=True)
        return "Reloaded dynamic UI modules in the current window."

    def refresh_app(
        self,
        _event=None,
        *,
        show_error_dialog: bool = True,
        raise_errors: bool = False,
    ) -> str | None:
        global agent_state, agent_panel, agent_brains, editor_runtime, living_body, perception, sim_resources, RomanSimulationRuntime, DYNAMIC_RELOAD_MODULES
        try:
            importlib.invalidate_caches()
            living_body = importlib.reload(living_body)
            perception = importlib.reload(perception)
            agent_state = importlib.reload(agent_state)
            agent_panel = importlib.reload(agent_panel)
            agent_brains = importlib.reload(agent_brains)
            sim_resources = importlib.reload(sim_resources)
            editor_runtime = importlib.reload(editor_runtime)
            RomanSimulationRuntime = editor_runtime.RomanSimulationRuntime
            DYNAMIC_RELOAD_MODULES = [
                agent_state,
                agent_panel,
                agent_brains,
                editor_runtime,
                living_body,
                perception,
                sim_resources,
            ]
            self.rebuild_dynamic_widgets()
            self.loaded_dynamic_module_mtimes = self.current_dynamic_module_mtimes()
            self.dynamic_reload_needed = False
            layout_reloaded = self.reload_saved_layout_if_clean()
            if layout_reloaded:
                self.status_var.set("Reloaded dynamic UI modules and saved layout in the current window.")
            else:
                self.status_var.set("Reloaded dynamic UI modules in the current window.")
            self.render_all()
        except Exception as error:
            self.status_var.set(f"Refresh failed: {error}")
            if show_error_dialog:
                messagebox.showerror("Refresh Failed", f"Could not reload dynamic UI modules.\n\n{error}")
            if raise_errors:
                raise
            if _event is not None:
                return "break"
            return None
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
        self.render_agent_details_panel()
        self.render_canvas()
        self.render_stats_and_labels()

    def render_stats_and_labels(self) -> None:
        self.update_meta_and_title()
        selected = self.get_selected_item()
        show_footer = self.selected_kind != "agent"
        if selected is None:
            self.selection_var.set("Nothing selected. Click a zone, location, or wall on the map or choose one in the list.")
        elif self.selected_kind == "zone":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the zone body to move it, or drag a corner handle to resize from that corner while the opposite corner stays put. "
                f"Current size: {int(selected['size']['x'])} x {int(selected['size']['y'])}."
            )
        elif self.selected_kind == "point":
            if point_has_facing(selected):
                self.selection_var.set(
                    f"{selected['label']} selected. Drag the location to move it, drag the east handle to change radius, and drag the facing handle to rotate it."
                )
            else:
                self.selection_var.set(
                    f"{selected['label']} selected. Drag the location to move it, or drag the east handle to change radius."
                )
        elif self.selected_kind == "agent":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the agent freely across the map while the simulation runs or pauses. "
                f"Speed: {int(round(selected['moveSpeed']))}. Live hunger, thirst, and status are in the lower-left Agent Attributes panel."
            )
        else:
            self.selection_var.set(
                f"{selected['id']} selected. Drag the wall body to move it, or drag either endpoint handle to reshape it."
            )
        self.footer_label.configure(text=self.layout["footer"])
        if show_footer:
            self.selection_label.grid(row=0, column=0, sticky="w")
            self.footer_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        else:
            self.selection_label.grid_remove()
            self.footer_label.grid_remove()
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
            for agent in self.simulation.agents:
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

    def render_agent_details_panel(self, *, force: bool = True) -> None:
        if self.agent_panel_view is None:
            return
        if self.selected_kind != "agent":
            self.clear_agent_details()
            self.agent_panel_view.hide()
            return

        agent = self.get_agent_by_id(self.selected_id)
        if agent is None:
            self.clear_agent_details()
            self.agent_panel_view.hide()
            return
        self.remember_last_clicked_agent(agent["id"])
        now = time.perf_counter()
        if not force and now - self.last_agent_details_refresh < 0.25:
            return
        self.last_agent_details_refresh = now
        self.agent_panel_view.show_agent(agent)

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
        if point_has_facing(point):
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
            text="Runtime-only Roman agent. These edits do not change the saved map layout. Full live attributes are shown in the bottom panel.",
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
            if point_has_facing(point):
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
        self.last_agent_details_id = None

    def clear_agent_details(self) -> None:
        self.last_agent_details_id = None

    def is_background_zone(self, zone: dict) -> bool:
        return zone["type"] in BACKGROUND_ZONE_TYPES

    def hover_target_from_hit(self, hit: dict | None) -> tuple[str | None, str | None]:
        if not hit:
            return (None, None)
        if hit["kind"] in {"agent", "agent-vision"}:
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
        if kind == "agent":
            self.remember_last_clicked_agent(item_id)
        else:
            self.clear_agent_details()
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

    def point_label_text(self, point: dict) -> str:
        if point["type"] != "Basin":
            return point["label"]
        basin = sim_resources.basin_state(self.simulation.resources, point["id"])
        if basin is None:
            return point["label"]
        capacity = float(basin.get("capacity", 0.0))
        maximum = max(1.0, float(basin.get("maximum", sim_resources.BASIN_MAX_CAPACITY)))
        return f"{point['label']} {int(round(capacity / maximum * 100.0))}% full"

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
                    self.point_label_text(point),
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
            for agent in self.simulation.agents:
                self.draw_agent_vision_cone(agent)
            for pig in self.simulation.resources.get("pigs", []):
                self.draw_pig(pig)
            for dead_pig in self.simulation.resources.get("deadPigs", []):
                self.draw_dead_pig(dead_pig)
            for agent in self.simulation.agents:
                self.draw_agent(agent)
            self.draw_interaction_pulses()
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

    def draw_agent_vision_cone(self, agent: dict) -> None:
        if agent.get("health", {}).get("status") == "dead":
            return
        cone_points = perception.vision_cone_points(agent, segments=14)
        screen_points = []
        for point in cone_points:
            screen = self.world_to_canvas(point)
            screen_points.extend([screen["x"], screen["y"]])
        outline = blend_hex(faction_color(agent["faction"]), CANVAS_BACKGROUND, 0.78)
        self.canvas.create_polygon(
            screen_points,
            fill="",
            outline=outline,
            width=1,
            tags=("vision_cone",),
        )

    def draw_interaction_pulses(self) -> None:
        if not self.interaction_pulses:
            return
        now = time.perf_counter()
        self.prune_interaction_pulses(now)
        for pulse in self.interaction_pulses:
            position = pulse.get("position")
            if not isinstance(position, dict):
                continue
            progress = clamp((now - pulse.get("startedAt", now)) / INTERACTION_PULSE_DURATION_SECONDS, 0.0, 1.0)
            color = blend_hex(INTERACTION_COLORS.get(pulse.get("kind"), "#e3bf47"), CANVAS_BACKGROUND, progress * 0.74)
            target_screen = self.world_to_canvas(position)
            agent_position = pulse.get("agentPosition")
            if isinstance(agent_position, dict):
                agent_screen = self.world_to_canvas(agent_position)
                if distance(agent_screen, target_screen) > 8.0:
                    self.canvas.create_line(
                        agent_screen["x"],
                        agent_screen["y"],
                        target_screen["x"],
                        target_screen["y"],
                        fill=color,
                        width=max(1, int(3 - progress)),
                        dash=(5, 4),
                        tags=("interaction_pulse",),
                    )
            base_radius = max(8.0, 40.0 * self.view["scale"])
            ring_radius = base_radius + 30.0 * progress
            self.canvas.create_oval(
                target_screen["x"] - ring_radius,
                target_screen["y"] - ring_radius,
                target_screen["x"] + ring_radius,
                target_screen["y"] + ring_radius,
                fill="",
                outline=color,
                width=max(1, int(4 - 2 * progress)),
                tags=("interaction_pulse",),
            )
            tick_radius = max(3.0, base_radius * 0.32)
            self.canvas.create_line(
                target_screen["x"] - tick_radius,
                target_screen["y"],
                target_screen["x"] + tick_radius,
                target_screen["y"],
                fill=color,
                width=2,
                tags=("interaction_pulse",),
            )
            self.canvas.create_line(
                target_screen["x"],
                target_screen["y"] - tick_radius,
                target_screen["x"],
                target_screen["y"] + tick_radius,
                fill=color,
                width=2,
                tags=("interaction_pulse",),
            )

    def draw_pig(self, pig: dict) -> None:
        screen = self.world_to_canvas(pig["position"])
        radius = max(3.0, pig["radius"] * self.view["scale"] * 0.09)
        self.canvas.create_oval(
            screen["x"] - radius,
            screen["y"] - radius,
            screen["x"] + radius,
            screen["y"] + radius,
            fill="#8d5a32",
            outline="#4e3320",
            width=1,
            tags=("pig",),
        )
        snout_radius = max(1.5, radius * 0.35)
        self.canvas.create_oval(
            screen["x"] + radius * 0.25 - snout_radius,
            screen["y"] - snout_radius,
            screen["x"] + radius * 0.25 + snout_radius,
            screen["y"] + snout_radius,
            fill="#b5774a",
            outline="",
            tags=("pig",),
        )

    def draw_dead_pig(self, dead_pig: dict) -> None:
        screen = self.world_to_canvas(dead_pig["position"])
        radius = max(3.0, dead_pig["radius"] * self.view["scale"] * 0.1)
        self.canvas.create_oval(
            screen["x"] - radius * 1.15,
            screen["y"] - radius * 0.75,
            screen["x"] + radius * 1.15,
            screen["y"] + radius * 0.75,
            fill="#5d4634",
            outline="#2d2118",
            width=1,
            tags=("dead_pig",),
        )
        self.canvas.create_line(
            screen["x"] - radius * 0.65,
            screen["y"] - radius * 0.6,
            screen["x"] + radius * 0.65,
            screen["y"] + radius * 0.6,
            fill="#2d2118",
            width=1,
            tags=("dead_pig",),
        )
        self.canvas.create_line(
            screen["x"] - radius * 0.65,
            screen["y"] + radius * 0.6,
            screen["x"] + radius * 0.65,
            screen["y"] - radius * 0.6,
            fill="#2d2118",
            width=1,
            tags=("dead_pig",),
        )

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
        if point["type"] == "Basin":
            self.draw_basin_resource(point, screen, inner_radius)
        elif point["type"] == "Fire":
            self.draw_fire_resource(point, screen, inner_radius, radius)
        elif point["type"] == "JarLocation":
            self.draw_jar_location(point, screen, inner_radius)
        elif color:
            self.canvas.create_oval(
                screen["x"] - inner_radius,
                screen["y"] - inner_radius,
                screen["x"] + inner_radius,
                screen["y"] + inner_radius,
                fill=color,
                outline="",
            )
        if point_has_facing(point):
            facing_length = radius + max(16, point["radius"] * self.view["scale"] * 0.14)
            self.canvas.create_line(
                screen["x"],
                screen["y"],
                screen["x"] + math.cos(point["facingRadians"]) * facing_length,
                screen["y"] + math.sin(point["facingRadians"]) * facing_length,
                fill=arrow_color,
                width=3 if is_selected else 2,
                arrow=tk.LAST,
                tags=("point_facing_arrow",),
            )

    def draw_basin_resource(self, point: dict, screen: dict, inner_radius: float) -> None:
        self.canvas.create_oval(
            screen["x"] - inner_radius,
            screen["y"] - inner_radius,
            screen["x"] + inner_radius,
            screen["y"] + inner_radius,
            fill="#f9f7ef",
            outline="",
            tags=("resource_basin",),
        )
        fraction = sim_resources.basin_capacity_fraction(self.simulation.resources, point["id"])
        self.draw_disc_fill_fraction(screen["x"], screen["y"], inner_radius, fraction, "#2f6dff", tags=("resource_basin_fill",))
        self.canvas.create_oval(
            screen["x"] - inner_radius,
            screen["y"] - inner_radius,
            screen["x"] + inner_radius,
            screen["y"] + inner_radius,
            fill="",
            outline="#d7d2c7",
            width=1,
            tags=("resource_basin",),
        )

    def draw_disc_fill_fraction(self, cx: float, cy: float, radius: float, fraction: float, fill: str, *, tags: tuple[str, ...]) -> None:
        fraction = clamp(fraction, 0.0, 1.0)
        if fraction <= 0.0:
            return
        if fraction >= 1.0:
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=fill, outline="", tags=tags)
            return
        boundary_y = cy + radius - 2.0 * radius * fraction
        dy = boundary_y - cy
        dx = math.sqrt(max(0.0, radius * radius - dy * dy))
        right_angle = math.atan2(dy, dx)
        left_angle = math.atan2(dy, -dx)
        if right_angle < 0.0:
            right_angle += math.tau
        if left_angle < 0.0:
            left_angle += math.tau
        if left_angle < right_angle:
            left_angle += math.tau
        points = []
        steps = 24
        for index in range(steps + 1):
            theta = right_angle + (left_angle - right_angle) * index / steps
            points.extend([cx + math.cos(theta) * radius, cy + math.sin(theta) * radius])
        self.canvas.create_polygon(points, fill=fill, outline="", tags=tags)

    def draw_fire_resource(self, point: dict, screen: dict, inner_radius: float, outer_radius: float) -> None:
        self.canvas.create_oval(
            screen["x"] - inner_radius,
            screen["y"] - inner_radius,
            screen["x"] + inner_radius,
            screen["y"] + inner_radius,
            fill="#eb6d3a",
            outline="",
            tags=("resource_fire",),
        )
        fire_state = sim_resources.fire_state(self.simulation.resources, point["id"])
        slots = fire_state["slots"] if fire_state is not None else []
        slot_width = max(24.0, outer_radius * 1.58)
        slot_height = max(8.0, outer_radius * 0.42)
        gap = max(4.0, slot_height * 0.42)
        start_x = screen["x"] + outer_radius * 1.45
        start_y = screen["y"] - (len(slots) * slot_height + max(0, len(slots) - 1) * gap) - outer_radius * 0.32
        for index, slot in enumerate(slots):
            y = start_y + index * (slot_height + gap)
            self.draw_fire_slot(start_x, y, slot_width, slot_height, slot)

    def draw_fire_slot(self, x: float, y: float, width: float, height: float, slot: dict) -> None:
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#d8d0bd",
            outline="#6c665b",
            width=1,
            tags=("resource_fire_slot",),
        )
        state = slot.get("state", "empty")
        amount_fraction = clamp(float(slot.get("amount", 0.0)) / 100.0, 0.0, 1.0)
        if state == "empty" or amount_fraction <= 0.0:
            return
        fill = "#f2d62d" if state == "raw" else "#7a1f19"
        self.canvas.create_rectangle(
            x + 2,
            y + 2,
            x + 2 + max(0.0, width - 4) * amount_fraction,
            y + height - 2,
            fill=fill,
            outline="",
            tags=("resource_fire_slot_fill", f"resource_fire_slot_{state}"),
        )

    def draw_jar_location(self, point: dict, screen: dict, inner_radius: float) -> None:
        size = inner_radius * 1.34
        rack_left = screen["x"] - size * 0.58
        rack_top = screen["y"] - size * 0.34
        rack_right = screen["x"] + size * 0.58
        rack_bottom = screen["y"] + size * 0.42
        self.canvas.create_rectangle(
            rack_left,
            rack_top,
            rack_right,
            rack_bottom,
            fill="#e1c67a",
            outline="#8a6d31",
            width=1,
            tags=("resource_jar_location",),
        )
        self.canvas.create_rectangle(
            rack_left,
            screen["y"] + size * 0.15,
            rack_right,
            screen["y"] + size * 0.24,
            fill="#8a6d31",
            outline="",
            tags=("resource_jar_location",),
        )
        jar_radius = max(2.0, size * 0.16)
        for offset in (-0.31, 0.0, 0.31):
            jar_x = screen["x"] + size * offset
            self.canvas.create_rectangle(
                jar_x - jar_radius * 0.58,
                screen["y"] - jar_radius * 1.44,
                jar_x + jar_radius * 0.58,
                screen["y"] - jar_radius * 0.8,
                fill="#b78a39",
                outline="#6c5128",
                width=1,
                tags=("resource_jar_location",),
            )
            self.canvas.create_oval(
                jar_x - jar_radius,
                screen["y"] - jar_radius,
                jar_x + jar_radius,
                screen["y"] + jar_radius * 0.85,
                fill="#d2ad58",
                outline="#6c5128",
                width=1,
                tags=("resource_jar_location",),
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
            handles = [self.point_radius_handle(item)]
            if point_has_facing(item):
                handles.append(self.point_facing_handle(item))
            for handle in handles:
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
            if point_has_facing(selected) and distance(world_point, self.point_facing_handle(selected)) <= handle_radius:
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

        vision_hit = self.get_agent_vision_cone_hit(world_point)
        if vision_hit:
            return vision_hit

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

        if hit["kind"] in {"agent", "agent-vision"}:
            self.selected_kind = "agent"
            self.selected_id = hit["id"]
            self.remember_last_clicked_agent(hit["id"])
        elif hit["kind"].startswith("zone"):
            self.selected_kind = "zone"
            self.selected_id = hit["id"]
            self.clear_agent_details()
        elif hit["kind"].startswith("point"):
            self.selected_kind = "point"
            self.selected_id = hit["id"]
            self.clear_agent_details()
        else:
            self.selected_kind = "wall"
            self.selected_id = hit["id"]
            self.clear_agent_details()

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
        elif hit["kind"] == "agent-vision":
            self.drag_state = None
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
        if drag_type == "move-agent":
            self.render_agent_details_panel()

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
        if hit and hit["kind"] in {"agent", "agent-vision"}:
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
