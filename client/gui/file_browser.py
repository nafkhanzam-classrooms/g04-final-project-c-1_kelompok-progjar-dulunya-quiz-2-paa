import tkinter as tk
from tkinter import ttk


class ProjectTreeFrame(tk.Frame):
    def __init__(self, parent, bg_color, tree_data, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.tree_data = tree_data or []
        self._build_contents()
    def _create_file(self):
        selected = self.tree.selection()

        parent = selected[0] if selected else ""
        file_name = "new_file.py"

        self.tree.insert(parent, "end", text=file_name)


    def _create_folder(self):
        selected = self.tree.selection()

        parent = selected[0] if selected else ""
        folder_name = "New Folder"

        new_folder = self.tree.insert(parent, "end", text=folder_name, open=True)
    def _build_contents(self):
        header = tk.Label(self, text="Project Tree", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))
        
        button_frame = tk.Frame(self)
        button_frame.pack(fill="x", padx=8, pady=(0, 4))

        new_file_btn = tk.Button(button_frame, text="New File", command=self._create_file)
        new_file_btn.pack(side="left", padx=4)

        new_folder_btn = tk.Button(button_frame, text="New Folder", command=self._create_folder)
        new_folder_btn.pack(side="left", padx=4)
        
        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        style = ttk.Style()
        style.configure(
            "ProjectTreeview.Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            rowheight=28,
            padding=4,
        )
        style.layout(
            "ProjectTreeview.Treeview",
            [
                (
                    "Treeview.field",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Treeview.padding",
                                {
                                    "sticky": "nswe",
                                    "children": [
                                        ("Treeview.treearea", {"sticky": "nswe"})
                                    ],
                                },
                            )
                        ],
                    },
                )
            ],
        )

        self.tree = ttk.Treeview(tree_container, show="tree", style="ProjectTreeview.Treeview")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self._populate_tree("", self.tree_data)

    def _populate_tree(self, parent, nodes):
        for node in nodes:
            node_id = self.tree.insert(parent, "end", text=node["name"], open=False)
            if node["type"] == "dir" and node.get("children"):
                self._populate_tree(node_id, node["children"])
