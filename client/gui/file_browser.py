import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog


class ProjectTreeFrame(tk.Frame):
    def __init__(self, parent, bg_color, tree_data, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.tree_data = tree_data or []
        self._build_contents()
    
    def _get_type(self, item):
        return self.tree.item(item, "values")[0] if self.tree.item(item, "values") else "dir"
   
    def _rename_item(self):
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        parent = self.tree.parent(item)
        old_name = self.tree.item(item, "text")

        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=old_name, parent=self)
        if not new_name:
            return

        if self._name_exists(parent, new_name, exclude_item=item):
            messagebox.showerror("Error", "Name already exists!", parent=self)
            return

        self.tree.item(item, text=new_name)
    
    def _name_exists(self, parent, name, exclude_item=None):
        children = self.tree.get_children(parent)
        
        for child in children:
            if exclude_item and child == exclude_item:
                continue
            if self.tree.item(child, "text") == name:
                return True
        return False
    
    def _create_file(self):
        selected = self.tree.selection()

        parent = selected[0] if selected else ""
        if parent and self._get_type(parent) == "file":
            parent = self.tree.parent(parent)
        file_name = simpledialog.askstring("New File", "File name:", parent=self)
        if not file_name:
            return

        if self._name_exists(parent, file_name):
            messagebox.showerror("Error", "File name already exists!", parent=self)
            return

        self.tree.insert(parent, "end", text=file_name, values=("file",))
    
    
    def _delete_item(self):
        selected = self.tree.selection()
        if selected:
            confirm = messagebox.askyesno("Confirm", "Delete selected item?", parent=self)
            if confirm:
                for item in selected:
                    self.tree.delete(item)

    def _create_folder(self):
        selected = self.tree.selection()

        parent = selected[0] if selected else ""
        if parent and self._get_type(parent) == "file":
            parent = self.tree.parent(parent)
        folder_name = simpledialog.askstring("New Folder", "Folder name:", parent=self)
        if not folder_name:
            return
        if self._name_exists(parent, folder_name):
            messagebox.showerror("Error", "Folder name already exists!", parent=self)
            return
        self.tree.insert(parent, "end", text=folder_name, open=True, values=("dir",))    
    
    
    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.tk_popup(event.x_root, event.y_root)
        
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
        
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="New File", command=self._create_file)
        self.menu.add_command(label="New Folder", command=self._create_folder)
        self.menu.add_separator()
        self.menu.add_command(label="Rename", command=self._rename_item)
        self.menu.add_command(label="Delete", command=self._delete_item)
        self.tree.bind("<Button-3>", self._show_context_menu)

        scrollbar = tk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self._populate_tree("", self.tree_data)

    def _populate_tree(self, parent, nodes):
        for node in nodes:
            node_type = node["type"]
            node_id = self.tree.insert(
                parent,
                "end",
                text=node["name"],
                open=False,
                values=(node_type,)
            )
            if node_type == "dir" and node.get("children"):
                self._populate_tree(node_id, node["children"])
