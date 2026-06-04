from __future__ import annotations

import ctypes
import ctypes.wintypes
import importlib.util
import json
import math
import pathlib
import sys
import time
import tkinter as tk

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "Build" / "verification"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PNG_PATH = OUT_DIR / "visual_eye_check_agent_panel.png"
RESULT_PATH = OUT_DIR / "visual_eye_check_agent_panel.json"

GWL_EXSTYLE = -20
HWND_BOTTOM = 1
SW_SHOWNOACTIVATE = 4
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
VERIFY_HEIGHT = 920
VERIFY_WIDTH = 1500
VERIFY_X = 8
VERIFY_Y = 8
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


def write_result(payload: dict) -> None:
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_editor_module():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("modeler_layout_editor", ROOT / "ModelerLayoutEditor.pyw")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure_nonintrusive_window(window: tk.Tk) -> None:
    window.geometry(f"{VERIFY_WIDTH}x{VERIFY_HEIGHT}+{VERIFY_X}+{VERIFY_Y}")
    window.overrideredirect(True)
    try:
        window.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    window.update_idletasks()

    hwnd = ctypes.wintypes.HWND(window.winfo_id())
    user32 = ctypes.windll.user32
    current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd,
        GWL_EXSTYLE,
        current_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
    )
    window.deiconify()
    window.update_idletasks()
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(
        hwnd,
        HWND_BOTTOM,
        VERIFY_X,
        VERIFY_Y,
        VERIFY_WIDTH,
        VERIFY_HEIGHT,
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def capture_window(window: tk.Tk) -> tuple[Image.Image, dict]:
    hwnd = ctypes.wintypes.HWND(window.winfo_id())
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    gdi32.SelectObject(hdc_mem, hbitmap)
    print_result = user32.PrintWindow(hwnd, hdc_mem, 2)

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]

    class BitmapInfo(ctypes.Structure):
        _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", ctypes.c_uint32 * 3)]

    bitmap_info = BitmapInfo()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    bitmap_info.bmiHeader.biWidth = width
    bitmap_info.bmiHeader.biHeight = -height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buffer, ctypes.byref(bitmap_info), 0)
    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)

    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)

    return image, {"printWindow": int(print_result), "width": width, "height": height}


def inspect_image(image: Image.Image) -> dict:
    rgb = image.convert("RGB")
    colors = rgb.getcolors(maxcolors=1_000_000)
    unique_colors = len(colors) if colors else 0
    dark_pixels = sum(count for count, color in colors if max(color) < 80) if colors else 0
    nonwhite_pixels = sum(count for count, color in colors if color != (255, 255, 255)) if colors else 0
    width, height = image.size
    panel_region = rgb.crop((390, max(0, height - 190), 735, height))
    panel_colors = panel_region.getcolors(maxcolors=500_000)
    panel_dark_pixels = sum(count for count, color in panel_colors if max(color) < 80) if panel_colors else 0
    return {
        "uniqueColors": unique_colors,
        "darkPixels": dark_pixels,
        "nonwhitePixels": nonwhite_pixels,
        "panelDarkPixels": panel_dark_pixels,
    }


def main() -> None:
    start = time.perf_counter()
    root = None
    try:
        module = load_editor_module()
        root = tk.Tk()
        root.withdraw()

        app = module.LayoutEditorApp(root)
        configure_nonintrusive_window(root)
        agent = app.simulation.agents[0]
        app.selected_kind = "agent"
        app.selected_id = agent["id"]
        app.render_all()
        root.update_idletasks()
        root.update()

        app.agent_panel_view.tree.item("section:Health", open=False)
        app.render_agent_details_panel(force=True)
        root.update_idletasks()
        root.update()

        rows = []
        agent_tree = app.agent_panel_view.tree
        for section in agent_tree.get_children(""):
            rows.append(agent_tree.item(section, "text"))
            for child in agent_tree.get_children(section):
                rows.append(agent_tree.item(child, "text"))
        row_labels = {row.split(":", 1)[0] for row in rows}
        root_sections = [agent_tree.item(section, "text") for section in agent_tree.get_children("")]
        health_stayed_closed = not bool(agent_tree.item("section:Health", "open"))

        agent_place = {
            key: str(value)
            for key, value in app.agent_panel_view.frame.place_info().items()
            if key != "in"
        }
        agent_panel_title = str(app.agent_panel_view.frame.cget("text"))
        footer_hidden = app.selection_label.winfo_manager() == "" and app.footer_label.winfo_manager() == ""
        basin = module.sim_resources.first_point(app.layout, "Basin", "Roman")
        basin_label = ""
        if basin is not None:
            app.hover_kind = "point"
            app.hover_id = basin["id"]
            app.render_canvas()
            root.update_idletasks()
            root.update()
            label_text_ids = app.canvas.find_withtag(module.LABEL_TEXT_TAG)
            label_texts = [app.canvas.itemcget(item_id, "text") for item_id in label_text_ids]
            basin_label = next((text for text in label_texts if basin["label"] in text), "")
        cone_fill_values = [
            app.canvas.itemcget(item_id, "fill")
            for item_id in app.canvas.find_withtag("vision_cone")
        ]
        cone_click_hit = None
        cone_agent = app.simulation.agents[0]
        cone_point = {
            "x": cone_agent["position"]["x"] + module.perception.VISION_DISTANCE * 0.25 * math.cos(cone_agent["headingRadians"]),
            "y": cone_agent["position"]["y"] + module.perception.VISION_DISTANCE * 0.25 * math.sin(cone_agent["headingRadians"]),
        }
        cone_click_hit = app.hit_test(cone_point)

        image, capture_meta = capture_window(root)
        image.save(PNG_PATH)
        image_meta = inspect_image(image)

        root.destroy()
        root = None

        required_rows = {"Health", "Needs", "Movement", "Identity", "Hunger", "Thirst", "Status"}
        ok = (
            capture_meta["printWindow"] != 0
            and image_meta["uniqueColors"] > 20
            and image_meta["panelDarkPixels"] > 30
            and required_rows.issubset(row_labels)
            and root_sections[0] == "Needs"
            and health_stayed_closed
            and agent_panel_title == agent["label"]
            and footer_hidden
            and agent_place.get("anchor") == "sw"
            and "full" in basin_label
            and all(value == "" for value in cone_fill_values)
            and isinstance(cone_click_hit, dict)
            and cone_click_hit.get("kind") == "agent-vision"
        )
        write_result(
            {
                "ok": ok,
                "png": str(PNG_PATH),
                "elapsedSeconds": round(time.perf_counter() - start, 3),
                "rows": rows,
                "rootSections": root_sections,
                "healthStayedClosed": health_stayed_closed,
                "agentPanelTitle": agent_panel_title,
                "agentPanelPlace": agent_place,
                "footerHidden": footer_hidden,
                "basinLabel": basin_label,
                "coneFillValues": cone_fill_values[:10],
                "coneClickHit": cone_click_hit,
                **capture_meta,
                **image_meta,
            }
        )
    except Exception as error:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        write_result({"ok": False, "error": repr(error), "png": str(PNG_PATH)})


if __name__ == "__main__":
    main()
