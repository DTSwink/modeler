from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_LAYOUT_PATH = DATA_DIR / "default_layout.json"
CURRENT_LAYOUT_PATH = DATA_DIR / "current_layout.json"

ZONE_TYPES = [
    "Walkable",
    "Blocked",
    "Camp",
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
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def deep_copy(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def today_stamp() -> str:
    return __import__("datetime").date.today().isoformat()


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
        self.root.title("Modeler Layout Editor")
        self.root.geometry("1500x920")
        self.root.minsize(1180, 760)

        self.default_layout = read_json(DEFAULT_LAYOUT_PATH)
        self.layout = self._load_current_layout()
        self.selected_kind = "zone"
        self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
        self.drag_state = None
        self.view = None
        self.status_var = tk.StringVar(value="Ready. Draft autosaves to data/current_layout.json.")
        self.meta_var = tk.StringVar()
        self.selection_var = tk.StringVar()

        self._build_ui()
        self._sync_world_controls()
        self.render_all()

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
        layout.setdefault("root", {})
        layout["root"].setdefault("cellSize", 100)
        layout["root"].setdefault("gridSize", {"x": 240, "y": 80})
        layout["root"].setdefault("drawLayout", True)
        layout["root"].setdefault("drawGrid", True)
        layout["root"].setdefault("drawLabels", True)
        layout.setdefault("zones", [])
        layout.setdefault("points", [])
        layout.setdefault("walls", [])
        layout.setdefault("summary", "Editable layout marker foundation.")
        layout.setdefault("footer", "Native local editor for the latest Modeler layout state.")
        layout.setdefault("stage", "Engine-independent layout editor")
        layout.setdefault("block", "0A")
        layout.setdefault("updated", today_stamp())

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
        ttk.Button(button_row, text="Reset Draft", command=self.reset_layout).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text="Import JSON", command=self.import_json).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text="Export JSON", command=self.export_json).grid(row=0, column=2, sticky="ew")
        button_row.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(sidebar, text="Open Data Folder", command=self.open_data_folder).pack(fill="x")

        ttk.Label(sidebar, textvariable=self.status_var, wraplength=340, justify="left").pack(anchor="w", pady=(10, 14))

        world_frame = ttk.LabelFrame(sidebar, text="World Settings", padding=12)
        world_frame.pack(fill="x", pady=(0, 12))
        for index in range(2):
            world_frame.columnconfigure(index, weight=1)

        self.cell_size_var = tk.StringVar()
        self.grid_x_var = tk.StringVar()
        self.grid_y_var = tk.StringVar()
        self.snap_size_var = tk.StringVar()
        self.draw_grid_var = tk.BooleanVar()
        self.draw_labels_var = tk.BooleanVar()
        self.snap_enabled_var = tk.BooleanVar()

        self._make_entry(world_frame, "Cell Size", self.cell_size_var, 0, 0, self.apply_world_settings)
        self._make_entry(world_frame, "Snap Size", self.snap_size_var, 0, 1, self.apply_world_settings)
        self._make_entry(world_frame, "Grid Width", self.grid_x_var, 1, 0, self.apply_world_settings)
        self._make_entry(world_frame, "Grid Height", self.grid_y_var, 1, 1, self.apply_world_settings)
        ttk.Checkbutton(world_frame, text="Draw grid", variable=self.draw_grid_var, command=self.apply_world_settings).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(world_frame, text="Draw labels", variable=self.draw_labels_var, command=self.apply_world_settings).grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(world_frame, text="Snap moves to grid", variable=self.snap_enabled_var, command=self.apply_world_settings).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

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
            text="Click to select. Drag bodies to move, drag handles to reshape, use the inspector for exact values.",
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
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Leave>", lambda _event: self.canvas.configure(cursor=""))
        self.canvas.bind("<Configure>", lambda _event: self.render_canvas())

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

    def _sync_world_controls(self) -> None:
        root = self.layout["root"]
        editor = self.layout["editor"]
        self.cell_size_var.set(str(root["cellSize"]))
        self.grid_x_var.set(str(root["gridSize"]["x"]))
        self.grid_y_var.set(str(root["gridSize"]["y"]))
        self.snap_size_var.set(str(editor["snapSize"]))
        self.draw_grid_var.set(bool(root["drawGrid"]))
        self.draw_labels_var.set(bool(root["drawLabels"]))
        self.snap_enabled_var.set(bool(editor["snapToGrid"]))

    def apply_world_settings(self, _event=None) -> None:
        try:
            self.layout["root"]["cellSize"] = max(1, int(float(self.cell_size_var.get() or 1)))
            self.layout["root"]["gridSize"]["x"] = max(1, int(float(self.grid_x_var.get() or 1)))
            self.layout["root"]["gridSize"]["y"] = max(1, int(float(self.grid_y_var.get() or 1)))
            self.layout["editor"]["snapSize"] = max(1, int(float(self.snap_size_var.get() or 1)))
            self.layout["root"]["drawGrid"] = bool(self.draw_grid_var.get())
            self.layout["root"]["drawLabels"] = bool(self.draw_labels_var.get())
            self.layout["editor"]["snapToGrid"] = bool(self.snap_enabled_var.get())
        except ValueError:
            self.status_var.set("World settings ignored until the numbers are valid.")
            return

        self.touch_and_save("Autosaved world settings.")
        self.render_all()

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
        try:
            self.layout = self._normalize_layout(read_json(Path(path)))
            self.selected_kind = "zone"
            self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
            self.touch_and_save(f"Imported layout from {path}")
            self._sync_world_controls()
            self.render_all()
        except Exception as error:
            messagebox.showerror("Import Failed", f"Could not import JSON.\n\n{error}")

    def reset_layout(self) -> None:
        if not messagebox.askyesno("Reset Draft", "Reset the current draft to the default layout?"):
            return
        self.layout = self._normalize_layout(deep_copy(self.default_layout))
        self.selected_kind = "zone"
        self.selected_id = self.layout["zones"][0]["id"] if self.layout["zones"] else None
        self._sync_world_controls()
        self.touch_and_save("Reset layout to default.")
        self.render_all()

    def touch_and_save(self, message: str) -> None:
        self.layout["updated"] = today_stamp()
        write_json(CURRENT_LAYOUT_PATH, self.layout)
        self.status_var.set(message)
        self.meta_var.set(f"Block {self.layout['block']} | {self.layout['stage']} | {self.layout['updated']}")

    def render_all(self) -> None:
        self.render_tree()
        self.render_inspector()
        self.render_canvas()
        self.render_stats_and_labels()

    def render_stats_and_labels(self) -> None:
        self.meta_var.set(f"Block {self.layout['block']} | {self.layout['stage']} | {self.layout['updated']}")
        selected = self.get_selected_item()
        if selected is None:
            self.selection_var.set("No item selected. Click a marker on the map or choose one in the list.")
        elif self.selected_kind == "zone":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the zone body to move it, or drag a corner handle to resize it. "
                f"Current size: {int(selected['size']['x'])} x {int(selected['size']['y'])}."
            )
        elif self.selected_kind == "point":
            self.selection_var.set(
                f"{selected['label']} selected. Drag the point to move it, drag the east handle to change radius, and drag the facing handle to rotate it."
            )
        else:
            self.selection_var.set(
                f"{selected['id']} selected. Drag the wall body to move it, or drag either endpoint handle to reshape it."
            )
        self.footer_label.configure(text=self.layout["footer"])

    def render_tree(self) -> None:
        selection_iid = f"{self.selected_kind}:{self.selected_id}" if self.selected_id else None
        self.tree.delete(*self.tree.get_children())

        zones_parent = self.tree.insert("", "end", iid="group-zone", text="Zones", open=True)
        for zone in self.layout["zones"]:
            self.tree.insert(zones_parent, "end", iid=f"zone:{zone['id']}", text=zone["label"])

        points_parent = self.tree.insert("", "end", iid="group-point", text="Points", open=True)
        for point in self.layout["points"]:
            self.tree.insert(points_parent, "end", iid=f"point:{point['id']}", text=point["label"])

        walls_parent = self.tree.insert("", "end", iid="group-wall", text="Walls", open=True)
        for wall in self.layout["walls"]:
            self.tree.insert(walls_parent, "end", iid=f"wall:{wall['id']}", text=wall["id"])

        if selection_iid and self.tree.exists(selection_iid):
            self.tree.selection_set(selection_iid)
            self.tree.focus(selection_iid)

    def render_inspector(self) -> None:
        for child in self.inspector_body.winfo_children():
            child.destroy()

        selected = self.get_selected_item()
        if selected is None:
            ttk.Label(self.inspector_body, text="Select a zone, point, or wall to edit its exact values.", wraplength=320, justify="left").pack(anchor="w")
            return

        if self.selected_kind == "zone":
            self.render_zone_inspector(selected)
        elif self.selected_kind == "point":
            self.render_point_inspector(selected)
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
        try:
            zone["label"] = vars_map["label"].get().strip() or zone["label"]
            zone["type"] = vars_map["type"].get()
            zone["faction"] = vars_map["faction"].get()
            zone["center"]["x"] = float(vars_map["x"].get())
            zone["center"]["y"] = float(vars_map["y"].get())
            zone["size"]["x"] = max(50.0, float(vars_map["width"].get()))
            zone["size"]["y"] = max(50.0, float(vars_map["height"].get()))
            zone["yawRadians"] = math.radians(float(vars_map["yaw"].get()))
            zone["color"] = vars_map["color"].get().strip() or zone["color"]
        except ValueError:
            self.status_var.set("Zone inspector ignored until the numbers are valid.")
            return
        self.touch_and_save("Autosaved zone edit.")
        self.render_all()

    def _apply_point_inspector(self, point: dict, vars_map: dict[str, tk.StringVar]) -> None:
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
            self.status_var.set("Point inspector ignored until the numbers are valid.")
            return
        self.touch_and_save("Autosaved point edit.")
        self.render_all()

    def _apply_wall_inspector(self, wall: dict, vars_map: dict[str, tk.StringVar]) -> None:
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
        self.touch_and_save("Autosaved wall edit.")
        self.render_all()

    def get_selected_item(self) -> dict | None:
        items = self.layout[f"{self.selected_kind}s"] if self.selected_kind in {"zone", "point", "wall"} else []
        for item in items:
            if item["id"] == self.selected_id:
                return item
        return None

    def on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        iid = selection[0]
        if iid.startswith("group-"):
            return
        kind, item_id = iid.split(":", 1)
        self.selected_kind = kind
        self.selected_id = item_id
        self.render_all()

    def render_canvas(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        view = self.compute_view(width, height)
        self.view = view

        self.canvas.create_rectangle(0, 0, width, height, fill="#ece5d6", outline="")

        if self.layout["root"]["drawGrid"]:
            for x in range(0, self.layout["root"]["gridSize"]["x"] + 1, 4):
                world_x = x * self.layout["root"]["cellSize"]
                screen = self.world_to_canvas({"x": world_x, "y": 0})
                self.canvas.create_line(screen["x"], view["offsetY"], screen["x"], view["offsetY"] + view["drawHeight"], fill="#d4cab8")
            for y in range(0, self.layout["root"]["gridSize"]["y"] + 1, 4):
                world_y = y * self.layout["root"]["cellSize"]
                screen = self.world_to_canvas({"x": 0, "y": world_y})
                self.canvas.create_line(view["offsetX"], screen["y"], view["offsetX"] + view["drawWidth"], screen["y"], fill="#d4cab8")

        if self.layout["root"]["drawLayout"]:
            for zone in sorted(self.layout["zones"], key=lambda item: item.get("priority", 0)):
                self.draw_zone(zone)
            for wall in self.layout["walls"]:
                self.draw_wall(wall)
            for point in self.layout["points"]:
                self.draw_point(point)

        selected = self.get_selected_item()
        if selected:
            self.draw_handles(selected)

        self.canvas.create_rectangle(
            view["offsetX"],
            view["offsetY"],
            view["offsetX"] + view["drawWidth"],
            view["offsetY"] + view["drawHeight"],
            outline="#8a7d6a",
            width=2,
        )

    def compute_view(self, width: int, height: int) -> dict:
        world_width = self.layout["root"]["gridSize"]["x"] * self.layout["root"]["cellSize"]
        world_height = self.layout["root"]["gridSize"]["y"] * self.layout["root"]["cellSize"]
        pad = 28
        inner_width = max(1, width - pad * 2)
        inner_height = max(1, height - pad * 2)
        scale = min(inner_width / world_width, inner_height / world_height)
        draw_width = world_width * scale
        draw_height = world_height * scale
        offset_x = (width - draw_width) * 0.5
        offset_y = (height - draw_height) * 0.5
        return {
            "width": width,
            "height": height,
            "worldWidth": world_width,
            "worldHeight": world_height,
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
        fill = zone["color"]
        outline = "#294fb6" if self.selected_kind == "zone" and self.selected_id == zone["id"] else "#5f564a"
        width = 3 if self.selected_kind == "zone" and self.selected_id == zone["id"] else 1
        points = []
        for corner in corners:
            screen = self.world_to_canvas(corner)
            points.extend([screen["x"], screen["y"]])
        self.canvas.create_polygon(points, fill=fill, outline=outline, width=width, stipple="gray25")
        if self.layout["root"]["drawLabels"]:
            center = self.world_to_canvas(zone["center"])
            self.canvas.create_text(center["x"], center["y"], text=zone["label"], font=("Georgia", 12, "bold"), fill="#1f1a15")

    def draw_wall(self, wall: dict) -> None:
        a = self.world_to_canvas(wall["a"])
        b = self.world_to_canvas(wall["b"])
        color = "#294fb6" if self.selected_kind == "wall" and self.selected_id == wall["id"] else "#6c665b"
        width = max(4, wall["thickness"] * self.view["scale"] * 0.32)
        self.canvas.create_line(a["x"], a["y"], b["x"], b["y"], fill=color, width=width, capstyle=tk.ROUND)

    def draw_point(self, point: dict) -> None:
        screen = self.world_to_canvas(point["position"])
        color = "#2f6dff" if point["faction"] == "Roman" else "#c84836" if point["faction"] == "Ottoman" else "#7a6b56"
        radius = max(6, point["radius"] * self.view["scale"] * 0.12)
        self.canvas.create_oval(screen["x"] - radius, screen["y"] - radius, screen["x"] + radius, screen["y"] + radius, fill=color, outline="white", width=2)
        facing_length = radius + max(16, point["radius"] * self.view["scale"] * 0.14)
        self.canvas.create_line(
            screen["x"],
            screen["y"],
            screen["x"] + math.cos(point["facingRadians"]) * facing_length,
            screen["y"] + math.sin(point["facingRadians"]) * facing_length,
            fill=color,
            width=2,
            arrow=tk.LAST,
        )
        if self.layout["root"]["drawLabels"]:
            self.canvas.create_text(screen["x"] + 10, screen["y"] - 10, text=point["label"], anchor="sw", font=("Georgia", 11), fill="#1f1a15")

    def zone_corners(self, zone: dict) -> list[dict]:
        half_x = zone["size"]["x"] * 0.5
        half_y = zone["size"]["y"] * 0.5
        corners = [
            {"x": -half_x, "y": -half_y},
            {"x": half_x, "y": -half_y},
            {"x": half_x, "y": half_y},
            {"x": -half_x, "y": half_y},
        ]
        result = []
        for local in corners:
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
                self.canvas.create_rectangle(screen["x"] - 6, screen["y"] - 6, screen["x"] + 6, screen["y"] + 6, fill="white", outline="#294fb6", width=2)
        elif self.selected_kind == "point":
            for handle in (self.point_radius_handle(item), self.point_facing_handle(item)):
                screen = self.world_to_canvas(handle)
                self.canvas.create_oval(screen["x"] - 6, screen["y"] - 6, screen["x"] + 6, screen["y"] + 6, fill="white", outline="#294fb6", width=2)
        else:
            for endpoint in (item["a"], item["b"]):
                screen = self.world_to_canvas(endpoint)
                self.canvas.create_oval(screen["x"] - 6, screen["y"] - 6, screen["x"] + 6, screen["y"] + 6, fill="white", outline="#294fb6", width=2)

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
        selected = self.get_selected_item()
        if selected is None:
            return None
        handle_radius = 14 / self.view["scale"]
        if self.selected_kind == "zone":
            for corner in self.zone_corners(selected):
                if distance(world_point, corner) <= handle_radius:
                    return {"kind": "zone-handle", "id": selected["id"]}
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
        handle_hit = self.get_handle_hit(world_point)
        if handle_hit:
            return handle_hit

        for point in reversed(self.layout["points"]):
            if distance(world_point, point["position"]) <= max(point["radius"], 120):
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
        world_point = self.canvas_to_world({"x": event.x, "y": event.y})
        hit = self.hit_test(world_point)
        if not hit:
            return

        if hit["kind"].startswith("zone"):
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

        if hit["kind"] == "zone":
            self.drag_state = {
                "type": "move-zone",
                "offset": {
                    "x": world_point["x"] - item["center"]["x"],
                    "y": world_point["y"] - item["center"]["y"],
                },
            }
        elif hit["kind"] == "zone-handle":
            self.drag_state = {"type": "resize-zone"}
        elif hit["kind"] == "point":
            self.drag_state = {
                "type": "move-point",
                "offset": {
                    "x": world_point["x"] - item["position"]["x"],
                    "y": world_point["y"] - item["position"]["y"],
                },
            }
        elif hit["kind"] == "point-radius":
            self.drag_state = {"type": "resize-point"}
        elif hit["kind"] == "point-facing":
            self.drag_state = {"type": "rotate-point"}
        elif hit["kind"] == "wall":
            self.drag_state = {
                "type": "move-wall",
                "startPointer": world_point,
                "startA": deep_copy(item["a"]),
                "startB": deep_copy(item["b"]),
            }
        elif hit["kind"] == "wall-endpoint":
            self.drag_state = {
                "type": "move-wall-endpoint",
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
            local = world_to_local(world_point, item["center"], item["yawRadians"])
            item["size"]["x"] = max(300.0, abs(local["x"]) * 2.0)
            item["size"]["y"] = max(300.0, abs(local["y"]) * 2.0)
        elif drag_type == "move-point":
            item["position"] = self.snap_point({
                "x": world_point["x"] - self.drag_state["offset"]["x"],
                "y": world_point["y"] - self.drag_state["offset"]["y"],
            })
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

        self.layout["updated"] = today_stamp()
        self.status_var.set("Editing layout...")
        self.render_canvas()
        self.render_stats_and_labels()

    def on_canvas_release(self, _event: tk.Event) -> None:
        if self.drag_state is None:
            return
        self.drag_state = None
        self.touch_and_save("Autosaved layout edit.")
        self.render_all()

    def on_canvas_motion(self, event: tk.Event) -> None:
        if self.view is None or self.drag_state is not None:
            return
        world_point = self.canvas_to_world({"x": event.x, "y": event.y})
        hit = self.hit_test(world_point)
        if hit and hit["kind"] in {"zone-handle", "point-radius", "point-facing", "wall-endpoint"}:
            self.canvas.configure(cursor="crosshair")
        elif hit:
            self.canvas.configure(cursor="fleur")
        else:
            self.canvas.configure(cursor="")


def main() -> None:
    root = tk.Tk()
    ttk.Style().theme_use("vista" if "vista" in ttk.Style().theme_names() else ttk.Style().theme_use())
    LayoutEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
