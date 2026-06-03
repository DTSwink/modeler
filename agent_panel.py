from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import agent_state


PANEL_WIDTH = 285
PANEL_HEIGHT = 132
TREE_WIDTH = 250


class AgentPanelView:
    def __init__(self, parent: ttk.Frame, mousewheel_callback) -> None:
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

    def destroy(self) -> None:
        self.frame.destroy()

    def hide(self) -> None:
        self.frame.place_forget()

    def show_agent(self, agent: dict) -> None:
        self.frame.configure(text=agent["label"])
        self.frame.place(x=0, rely=1.0, y=0, anchor="sw", width=PANEL_WIDTH, height=PANEL_HEIGHT)
        self.tree.delete(*self.tree.get_children())

        for section in agent_state.agent_snapshot_sections(agent):
            section_id = f"section:{section['title']}"
            self.tree.insert("", "end", iid=section_id, text=section["title"], open=True)
            for row in section["rows"]:
                self.tree.insert(section_id, "end", text=f"{row['label']}: {format_agent_detail_value(row)}")

    def scroll(self, event: tk.Event) -> None:
        if getattr(event, "delta", 0):
            self.tree.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.tree.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.tree.yview_scroll(1, "units")


def format_agent_detail_value(row: dict) -> str:
    if row.get("kind") == "meter":
        maximum = max(1, int(row.get("maximum", 100)))
        value = max(0, min(maximum, int(row["value"])))
        return f"{value}/{maximum}"
    return str(row["value"])
