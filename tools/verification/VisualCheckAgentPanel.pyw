from __future__ import annotations

import ctypes
import ctypes.wintypes
import importlib.util
import json
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


def write_result(payload: dict) -> None:
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_editor_module():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("modeler_layout_editor", ROOT / "ModelerLayoutEditor.pyw")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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
        root.geometry("1500x920+8+8")
        root.overrideredirect(True)
        root.attributes("-alpha", 0.01)

        app = module.LayoutEditorApp(root)
        agent = app.simulation.agents[0]
        app.selected_kind = "agent"
        app.selected_id = agent["id"]
        app.render_all()
        root.update_idletasks()
        root.update()

        rows = []
        for section in app.agent_details_tree.get_children(""):
            rows.append(app.agent_details_tree.item(section, "text"))
            for child in app.agent_details_tree.get_children(section):
                rows.append(app.agent_details_tree.item(child, "text"))
        row_labels = {row.split(":", 1)[0] for row in rows}

        agent_place = {
            key: str(value)
            for key, value in app.agent_details_frame.place_info().items()
            if key != "in"
        }
        agent_panel_title = str(app.agent_details_frame.cget("text"))
        footer_hidden = app.selection_label.winfo_manager() == "" and app.footer_label.winfo_manager() == ""

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
            and agent_panel_title == agent["label"]
            and footer_hidden
            and agent_place.get("anchor") == "sw"
        )
        write_result(
            {
                "ok": ok,
                "png": str(PNG_PATH),
                "elapsedSeconds": round(time.perf_counter() - start, 3),
                "rows": rows,
                "agentPanelTitle": agent_panel_title,
                "agentPanelPlace": agent_place,
                "footerHidden": footer_hidden,
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
