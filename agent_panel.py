from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import agent_state
import editor_command_bridge


PANEL_WIDTH = 285
PANEL_HEIGHT = 132
TREE_WIDTH = 250


class AgentPanelView:
    def __init__(
        self,
        parent: ttk.Frame,
        mousewheel_callback,
        refresh_callback: Callable[[dict], str | None] | None = None,
    ) -> None:
        self.root = parent.winfo_toplevel()
        self.refresh_callback = refresh_callback
        self.section_open_state: dict[str, bool] = {}
        self.frame = ttk.LabelFrame(parent, text="", padding=8)
        self.frame.place(x=0, rely=1.0, y=0, anchor="sw", width=PANEL_WIDTH, height=PANEL_HEIGHT)
        self.frame.place_forget()
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self.frame,
            show="tree",
            height=5,
            selectmode="none",
        )
        self.tree.column("#0", width=TREE_WIDTH, minwidth=190, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<MouseWheel>", mousewheel_callback)
        self.tree.bind("<Button-4>", mousewheel_callback)
        self.tree.bind("<Button-5>", mousewheel_callback)
        self.tree.bind("<<TreeviewOpen>>", self.remember_section_state)
        self.tree.bind("<<TreeviewClose>>", self.remember_section_state)
        editor_command_bridge.install_tk_command_bridge(
            self.root,
            {
                editor_command_bridge.ACTION_REFRESH: self.handle_refresh_command,
                editor_command_bridge.ACTION_PING: self.handle_ping_command,
            },
        )

    def destroy(self) -> None:
        self.frame.destroy()

    def hide(self) -> None:
        self.frame.place_forget()

    def show_agent(self, agent: dict) -> None:
        self.frame.configure(text=agent["label"])
        self.frame.place(x=0, rely=1.0, y=0, anchor="sw", width=PANEL_WIDTH, height=PANEL_HEIGHT)
        self.capture_section_state()
        self.tree.delete(*self.tree.get_children())

        for section in agent_state.agent_snapshot_sections(agent):
            section_id = f"section:{section['title']}"
            is_open = self.section_open_state.get(section["title"], section["title"] == "Needs")
            self.tree.insert("", "end", iid=section_id, text=section["title"], open=is_open)
            for row in section["rows"]:
                self.tree.insert(section_id, "end", text=f"{row['label']}: {format_agent_detail_value(row)}")

    def capture_section_state(self) -> None:
        for section_id in self.tree.get_children(""):
            title = str(self.tree.item(section_id, "text"))
            self.section_open_state[title] = bool(self.tree.item(section_id, "open"))

    def remember_section_state(self, _event: tk.Event | None = None) -> None:
        self.root.after_idle(self.capture_section_state)

    def scroll(self, event: tk.Event) -> None:
        if getattr(event, "delta", 0):
            self.tree.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.tree.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.tree.yview_scroll(1, "units")

    def handle_refresh_command(self, command: dict) -> str:
        if self.refresh_callback is not None:
            return self.refresh_callback(command) or "Reloaded dynamic UI modules in the current window."
        self.root.event_generate("<Control-r>", when="tail")
        return "Refresh event queued in the editor window."

    def handle_ping_command(self, _command: dict) -> str:
        return "Modeler editor is alive."


def format_agent_detail_value(row: dict) -> str:
    if row.get("kind") == "meter":
        maximum = max(1, int(row.get("maximum", 100)))
        value = max(0, min(maximum, int(row["value"])))
        return f"{value}/{maximum}"
    return str(row["value"])
