import re
import tkinter as tk
from tkinter import colorchooser, messagebox, filedialog
from tkinter import ttk
import base64
import json
from urllib import request as urlrequest, error as urlerror
import threading

# ---------------------------------------------------------------------
# Constants / Theme
# ---------------------------------------------------------------------

LOGICAL_WIDTH = 320
LOGICAL_HEIGHT = 240

BG_MAIN   = "#101010"
BG_TITLE  = "#181818"
BG_PANEL  = "#1e1e1e"
BG_CANVAS = "#000000"
BG_ENTRY  = "#242424"

FG_TEXT   = "#ffffff"
FG_MUTED  = "#bbbbbb"

ACCENT    = "#ff9800"
ACCENT_D  = "#f57c00"

# Syntax highlight colors (updated)
_SYM_KEYWORD  = "#D84D7B"   # raspberry red (leans magenta)
_SYM_STRING   = "#B39CFF"   # soft lavender
_SYM_COMMENT  = "#6B6B6B"   # neutral grey
_SYM_FUNCTION = "#6FC1FF"   # pale cyan to separate funcs from keywords


def hex_from_rgb(rgb):
    """(R,G,B) -> #RRGGBB for Tk."""
    r, g, b = rgb
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


# ---------------------------------------------------------------------
# Startup dialog – App metadata
# ---------------------------------------------------------------------

def ask_initial_app_metadata(root):
    """
    Show a startup dialog to collect app metadata.
    Returns a dict or None if cancelled.
    """
    dlg = tk.Toplevel(root)
    dlg.title("Zeno UI Editor")
    dlg.configure(bg=BG_MAIN)
    dlg.transient(root)
    dlg.grab_set()

    dlg.geometry("480x220")
    dlg.resizable(False, False)

    container = tk.Frame(dlg, bg=BG_MAIN, padx=12, pady=12)
    container.pack(fill="both", expand=True)

    title_lbl = tk.Label(
        container,
        text="Zeno UI – New Application",
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=("Segoe UI", 12, "bold"),
        anchor="w",
    )
    title_lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    name_var    = tk.StringVar(value="")
    author_var  = tk.StringVar(value="")
    version_var = tk.StringVar(value="")

    def mk_row(row, label_text, var, width=28):
        tk.Label(
            container,
            text=label_text,
            bg=BG_MAIN,
            fg=FG_TEXT,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(
            container,
            textvariable=var,
            width=width,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
        )
        e.grid(row=row, column=1, sticky="ew", pady=3)
        return e

    container.columnconfigure(1, weight=1)
    mk_row(1, "App name:", name_var)
    mk_row(2, "Author:",   author_var)
    mk_row(3, "Version:",  version_var)

    btn_frame = tk.Frame(container, bg=BG_MAIN)
    btn_frame.grid(row=5, column=0, columnspan=2, pady=(16, 0), sticky="e")

    result = {"value": None}

    def do_ok():
        app_name = name_var.get().strip()
        if not app_name:
            messagebox.showwarning("Missing name", "Please enter an app name.")
            return

        result["value"] = {
            "app_name": app_name,
            "author":   author_var.get().strip()  or "Phoenix",
            "version":  version_var.get().strip() or "1.0.0",
        }
        dlg.destroy()

    def do_cancel():
        result["value"] = None
        dlg.destroy()

    ok_btn = tk.Button(
        btn_frame,
        text="Create",
        command=do_ok,
        bg=ACCENT,
        fg=FG_TEXT,
        activebackground=ACCENT_D,
        activeforeground=FG_TEXT,
        relief="flat",
        width=10,
    )
    ok_btn.pack(side="right", padx=(8, 0))

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=do_cancel,
        bg="#333333",
        fg=FG_TEXT,
        activebackground="#4a4a4a",
        activeforeground=FG_TEXT,
        relief="flat",
        width=10,
    )
    cancel_btn.pack(side="right")

    dlg.bind("<Return>", lambda e: do_ok())
    dlg.bind("<Escape>", lambda e: do_cancel())

    dlg.after(100, lambda: dlg.focus_force())
    dlg.wait_window(dlg)

    return result["value"]


# ---------------------------------------------------------------------
# Widget Data Model
# ---------------------------------------------------------------------

class Widget:
    def __init__(self, type_name, x, y, label="Label"):
        self.type = type_name
        self.label = label
        self.x = x
        self.y = y
        self.width = 0
        self.height = 0
        self.margin = 0
        self.fg_color = (255, 255, 255)
        self.bg_color = (51, 51, 51)
        self.action = ""


class ButtonWidget(Widget):
    def __init__(self, x, y, label="Button"):
        super().__init__("Button", x, y, label)
        self.width = 100
        self.height = 30
        self.margin = 5
        self.fg_color = (255, 255, 255)
        self.bg_color = (50, 50, 200)
        self.action = f"on_{label.lower().replace(' ', '_')}_click"


class TextWidget(Widget):
    def __init__(self, x, y, label="Text"):
        super().__init__("Text", x, y, label)
        self.width = 0
        self.height = 0
        self.fg_color = (255, 255, 255)
        self.bg_color = (0, 0, 0)
        self.action = ""


class LayerWidget(Widget):
    """
    Layer = colored rectangle, matches UIScreen.layer(x, y, w, h, color)
    """
    def __init__(self, x, y, width=100, height=40, label="Layer"):
        super().__init__("Layer", x, y, label)
        self.width = width
        self.height = height
        self.margin = 0
        self.fg_color = (0, 0, 0)       # unused
        self.bg_color = (80, 80, 80)    # default layer color
        self.action = ""                # no action

class SliderWidget(Widget):
    def __init__(self, x, y):
        super().__init__("Slider", x, y, "Slider")
        self.width = 120
        self.height = 20

        self.value = 50          # 0–100
        self.track_color = (120, 120, 120)
        self.fill_color = (0, 200, 255)
        self.knob_color = (255, 255, 255)

        self.knob_radius = 6     # smaller ball


class ToggleWidget(Widget):
    def __init__(self, x, y):
        super().__init__("Toggle", x, y, "Toggle")
        self.width = 50
        self.height = 24
        self.state = False


class ProgressBarWidget(Widget):
    def __init__(self, x, y):
        super().__init__("ProgressBar", x, y, "Progress")
        self.width = 120
        self.height = 20
        self.value = 40


class PanelWidget(Widget):
    def __init__(self, x, y):
        super().__init__("Panel", x, y, "Panel")
        self.width = 150
        self.height = 100
# ---------------------------------------------------------------------
# Zeno UI Editor
# ---------------------------------------------------------------------

class ZenoUIEditor:
    """
    Zeno Micro PC UI Builder – single-screen editor.
    """

    def __init__(self, root: tk.Tk, initial_meta=None):
        self.root = root
        self.root.title("Zeno UI Editor – Single Screen")
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1200x720")
        self.root.minsize(1000, 600)

        self._apply_style()

        # --- Meta info from startup dialog ---
        if initial_meta is None:
            app_name_initial = ""
            author_initial   = "Phoenix"
            version_initial  = "1.0.0"
        else:
            app_name_initial = initial_meta.get("app_name", "")
            author_initial   = initial_meta.get("author", "Phoenix")
            version_initial  = initial_meta.get("version", "1.0.0")

        self.app_name    = tk.StringVar(value=app_name_initial)
        self.app_author  = tk.StringVar(value=author_initial)
        self.app_version = tk.StringVar(value=version_initial)
        self.func_name   = tk.StringVar(value="main")

        # Screen-level properties
        self.screen_bg          = (0, 0, 0)
        self.taskbar_color      = (50, 50, 50)
        self.taskbar_text_color = (255, 255, 255)
        self.taskbar_text       = tk.StringVar(value=self.app_name.get() or "Home")
        self.screen_has_exit    = tk.BooleanVar(value=True)

        # GitHub config (fill your PAT locally)
        self.github_token  = "secret"
        self.github_repo   = "repo"
        self.github_branch = "main"

        # Widgets
        self.widgets = []
        self.selected_widget = None

        # Interaction state
        self.mode = None         # "add_button", "add_text", "add_layer", or None
        self.dragging_widget = None
        self.drag_offset_px = (0, 0)

        # Resizing state (for Button or Layer)
        self.resize_target = None
        self.resize_handle = None  # "tl", "tr", "bl", "br"

        # Preview scaling
        self.scale = 2.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Sketch / logic editor
        self.sketch_text = None

        # Code editor editable state variable (switch)
        self.code_editable = tk.BooleanVar(value=True)

        # Throttled sash placement
        self._resize_job = None

        self._build_layout()
        self._set_pane_ratio()
        self.redraw_canvas()

    # -----------------------------------------------------------------
    # Styling
    # -----------------------------------------------------------------

    def _apply_style(self):
        try:
            style = ttk.Style()
            style.theme_use("clam")
            self.root.configure(bg=BG_MAIN)
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------

    def _build_layout(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Title bar
        title_bar = tk.Frame(self.root, bg=BG_TITLE, height=28)
        title_bar.grid(row=0, column=0, sticky="ew")
        title_bar.grid_propagate(False)

        tk.Label(
            title_bar,
            text="Zeno UI Editor – Single Screen",
            bg=BG_TITLE,
            fg=FG_TEXT,
            anchor="w",
            padx=10,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", fill="y")

        tk.Label(
            title_bar,
            textvariable=self.app_name,
            bg=BG_TITLE,
            fg=FG_MUTED,
            anchor="e",
            padx=10,
            font=("Segoe UI", 9),
        ).pack(side="right", fill="y")

        # ---------- NOTE: Notebook with Design, Code & API tabs ----------
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        design_tab = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(design_tab, text="Design")
        code_tab = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(code_tab, text="Code")
        # Add API tab (read-only documentation)
        api_tab = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(api_tab, text="API")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Paned window (originally attached to root) now attached to design_tab
        self.main_pane = tk.PanedWindow(
            design_tab,
            orient="horizontal",
            sashrelief="raised",
            bg=BG_MAIN,
            bd=0,
            sashwidth=4,
        )
        self.main_pane.pack(fill="both", expand=True)

        left_frame = tk.Frame(self.main_pane, bg=BG_MAIN)
        right_frame = tk.Frame(self.main_pane, bg=BG_MAIN)
        self.main_pane.add(left_frame, minsize=500)
        self.main_pane.add(right_frame, minsize=340)

        self.root.bind("<Configure>", self._on_root_configure)

        # Left = preview
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            left_frame,
            bg=BG_CANVAS,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Configure>", self.on_preview_resize)

        # Right panels
        right_frame.rowconfigure(3, weight=1)
        right_frame.columnconfigure(0, weight=1)

        file_frame = tk.LabelFrame(
            right_frame, text="File / GitHub",
            bg=BG_PANEL, fg=FG_TEXT, padx=4, pady=4
        )
        screen_frame = tk.LabelFrame(
            right_frame, text="Screen",
            bg=BG_PANEL, fg=FG_TEXT, padx=4, pady=4
        )
        widgets_frame = tk.LabelFrame(
            right_frame, text="Widgets",
            bg=BG_PANEL, fg=FG_TEXT, padx=4, pady=4
        )
        sketch_frame = tk.LabelFrame(
            right_frame, text="Sketch / Logic",
            bg=BG_PANEL, fg=FG_TEXT, padx=4, pady=4
        )

        file_frame.grid(row=0, column=0, sticky="ew",  padx=4, pady=4)
        screen_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        widgets_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        sketch_frame.grid(row=3, column=0, sticky="nsew", padx=4, pady=4)

        # File frame
        def mk_entry(parent, label_text, var, row):
            tk.Label(parent, text=label_text, bg=BG_PANEL, fg=FG_TEXT).grid(
                row=row, column=0, sticky="w"
            )
            e = tk.Entry(
                parent,
                textvariable=var,
                width=18,
                bg=BG_ENTRY,
                fg=FG_TEXT,
                insertbackground=FG_TEXT,
                relief="flat",
            )
            e.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2, padx=2)
            parent.columnconfigure(1, weight=1)

        mk_entry(file_frame, "Name:",      self.app_name,    0)
        mk_entry(file_frame, "Author:",    self.app_author,  1)
        mk_entry(file_frame, "Version:",   self.app_version, 2)
        mk_entry(file_frame, "Func name:", self.func_name,   3)

        tk.Label(
            file_frame,
            text="GitHub path:",
            bg=BG_PANEL,
            fg=FG_TEXT,
            anchor="w"
        ).grid(row=4, column=0, sticky="w", pady=2)
        self.github_path_label = tk.Label(
            file_frame,
            text=self._current_repo_path_preview(),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="w"
        )
        self.github_path_label.grid(row=4, column=1, columnspan=2, sticky="w", pady=2)

        # update preview when app name changes
        self.app_name.trace_add("write", lambda *_: self._update_github_path_label())

        file_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=1)

        tk.Button(
            file_frame,
            text="Save Code",
            command=self.save_generated_code,
            bg=ACCENT,
            fg=FG_TEXT,
            relief="flat"
        ).grid(row=10, column=0, sticky="ew", pady=(8, 2), padx=(0,2))

        tk.Button(
            file_frame,
            text="Upload",
            command=self.upload_to_github,
            bg="#242424",
            fg=FG_TEXT,
            relief="flat"
        ).grid(row=10, column=1, sticky="ew", pady=(8, 2), padx=(2,0))        # Screen frame
        tk.Checkbutton(
            screen_frame,
            text="Show exit button",
            variable=self.screen_has_exit,
            command=self.redraw_canvas,
            anchor="w",
            bg=BG_PANEL,
            fg=FG_TEXT,
            activebackground=BG_PANEL,
            activeforeground=FG_TEXT,
            selectcolor=BG_PANEL,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Button(
            screen_frame, text="Screen BG",
            command=self.pick_screen_bg,
            bg="#333333", fg=FG_TEXT,
            activebackground="#4a4a4a", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        tk.Button(
            screen_frame, text="Taskbar Color",
            command=self.pick_taskbar_color,
            bg="#333333", fg=FG_TEXT,
            activebackground="#4a4a4a", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        tk.Button(
            screen_frame, text="Taskbar Text Color",
            command=self.pick_taskbar_text_color,
            bg="#333333", fg=FG_TEXT,
            activebackground="#4a4a4a", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

        tk.Label(screen_frame, text="Taskbar Text:", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=3, column=0, sticky="w", padx=2, pady=2
        )
        tb_entry = tk.Entry(
            screen_frame, textvariable=self.taskbar_text,
            bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT,
            relief="flat"
        )
        tb_entry.grid(row=3, column=1, sticky="ew", padx=2, pady=2)
        tb_entry.bind("<KeyRelease>", lambda e: self.redraw_canvas())
        screen_frame.columnconfigure(1, weight=1)

        # Widgets frame
        widgets_frame.rowconfigure(2, weight=1)
        widgets_frame.columnconfigure(0, weight=1)

        add_frame = tk.Frame(widgets_frame, bg=BG_PANEL)
        add_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        add_frame.columnconfigure(0, weight=1)
        add_frame.columnconfigure(1, weight=1)
        add_frame.columnconfigure(2, weight=1)
        widgets_frame.rowconfigure(0, weight=0)
        widgets_frame.rowconfigure(1, weight=0)
        widgets_frame.rowconfigure(2, weight=1)
        widgets_frame.columnconfigure(0, weight=1)

        # Row 0
        tk.Button(
            add_frame, text="+ Button",
            command=self.mode_add_button,
            bg=ACCENT, fg=FG_TEXT,
            relief="flat"
        ).grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        tk.Button(
            add_frame, text="+ Text",
            command=self.mode_add_text,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        tk.Button(
            add_frame, text="+ Layer",
            command=self.mode_add_layer,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=0, column=2, padx=2, pady=2, sticky="ew")


        # Row 1
        tk.Button(
            add_frame, text="+ Slider",
            command=self.mode_add_slider,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=1, column=0, padx=2, pady=2, sticky="ew")

        tk.Button(
            add_frame, text="+ Toggle",
            command=self.mode_add_toggle,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        tk.Button(
            add_frame, text="+ Progress",
            command=self.mode_add_progress,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=1, column=2, padx=2, pady=2, sticky="ew")


        # Row 2
        tk.Button(
            add_frame, text="+ Panel",
            command=self.mode_add_panel,
            bg="#333333", fg=FG_TEXT,
            relief="flat"
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=2, pady=2)

        tk.Label(widgets_frame, text="List:", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=1, column=0, sticky="w"
        )

        self.widget_list = tk.Listbox(
            widgets_frame,
            height=4,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            selectbackground=ACCENT,
            selectforeground=FG_TEXT,
            relief="flat",
            highlightthickness=0,
        )
        self.widget_list.grid(row=2, column=0, sticky="nsew", pady=(2, 4))
        self.widget_list.bind("<<ListboxSelect>>", self.on_widget_list_select)

        prop_frame = tk.LabelFrame(
            widgets_frame, text="Widget Properties",
            bg=BG_PANEL, fg=FG_TEXT, padx=4, pady=4
        )
        prop_frame.grid(row=3, column=0, sticky="ew")
        prop_frame.columnconfigure(1, weight=1)

        self.widget_type_var = tk.StringVar(value="")

        tk.Label(prop_frame, text="Type:", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(prop_frame, textvariable=self.widget_type_var, bg=BG_PANEL, fg=ACCENT).grid(
            row=0, column=1, sticky="w"
        )

        tk.Label(prop_frame, text="Label/Text:", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=1, column=0, sticky="w"
        )
        self.entry_label = tk.Entry(
            prop_frame, width=18,
            bg=BG_ENTRY, fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat"
        )
        self.entry_label.grid(row=1, column=1, sticky="ew", pady=1)
        self.entry_label.bind("<KeyRelease>", lambda e: self.apply_widget_props(live=True))

        def mk_small_entry(row, label_text):
            tk.Label(prop_frame, text=label_text, bg=BG_PANEL, fg=FG_TEXT).grid(
                row=row, column=0, sticky="w"
            )
            e = tk.Entry(
                prop_frame, width=6,
                bg=BG_ENTRY, fg=FG_TEXT,
                insertbackground=FG_TEXT,
                relief="flat"
            )
            e.grid(row=row, column=1, sticky="w", pady=1)
            e.bind("<KeyRelease>", lambda event: self.apply_widget_props(live=True))
            return e

        self.entry_x      = mk_small_entry(2, "X:")
        self.entry_y      = mk_small_entry(3, "Y:")
        self.entry_w      = mk_small_entry(4, "W (btn/layer):")
        self.entry_h      = mk_small_entry(5, "H (btn/layer):")
        self.entry_margin = mk_small_entry(6, "Margin:")
        self.entry_value = mk_small_entry(7, "Value (0-100):")

        tk.Label(prop_frame, text="Action name:", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=8, column=0, sticky="w"
        )
        self.entry_action = tk.Entry(
            prop_frame, width=18,
            bg=BG_ENTRY, fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat"
        )
        self.entry_action.grid(row=8, column=1, sticky="ew", pady=1)
        self.entry_action.bind("<KeyRelease>", lambda e: self.apply_widget_props(live=True))

        tk.Button(
            prop_frame, text="Text Color",
            command=self.pick_widget_fg,
            bg="#333333", fg=FG_TEXT,
            activebackground="#4a4a4a", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=8, column=0, sticky="ew", pady=2)

        tk.Button(
            prop_frame, text="BG Color",
            command=self.pick_widget_bg,
            bg="#333333", fg=FG_TEXT,
            activebackground="#4a4a4a", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=8, column=1, sticky="ew", pady=2)

        tk.Button(
            prop_frame, text="Delete",
            command=self.delete_selected_widget,
            bg="#552222", fg=FG_TEXT,
            activebackground="#773333", activeforeground=FG_TEXT,
            relief="flat"
        ).grid(row=10, column=0, columnspan=2, sticky="ew", pady=4)

        # Sketch frame (simple text editor)
        tk.Label(sketch_frame, text="App logic (optional):", bg=BG_PANEL, fg=FG_TEXT).grid(
            row=0, column=0, sticky="w"
        )

        self.sketch_text = tk.Text(
            sketch_frame,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
            wrap="none",
            height=8
        )
        scroll = tk.Scrollbar(
            sketch_frame,
            orient="vertical",
            command=self.sketch_text.yview
        )
        self.sketch_text.configure(yscrollcommand=scroll.set)
        self.sketch_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        scroll.grid(row=1, column=1, sticky="ns", pady=(4, 0))

        sketch_frame.rowconfigure(1, weight=1)
        sketch_frame.columnconfigure(0, weight=1)

        # Status bar
        self.status = tk.Label(
            self.root,
            text="Ready.",
            anchor="w",
            relief="sunken",
            bg=BG_TITLE,
            fg=FG_MUTED,
        )
        self.status.grid(row=2, column=0, sticky="ew")

        # ---------- build the Code tab UI (with Editable switch) ----------
        self._build_code_tab(code_tab)

        # ---------- build the API tab (read-only) ----------
        self._build_api_tab(api_tab)

    def _build_code_tab(self, parent_frame):
        """
        Code tab UI:
        - 'Update Code' populates the text widget with generate_micropython_code()
        - 'Editable' switch toggles read-only mode for the editor
        - Basic syntax highlighting applied on update & edits
        """
        toolbar = tk.Frame(parent_frame, bg=BG_PANEL)
        toolbar.pack(fill="x", padx=4, pady=4)

        btn_update = tk.Button(toolbar, text="Update Code", bg=ACCENT, fg=FG_TEXT, relief="flat",
                               command=self._update_code_tab)
        btn_update.pack(side="left", padx=(0,6))

        # Editable switch (Checkbutton) instead of a Save button
        editable_chk = tk.Checkbutton(
            toolbar,
            text="Editable",
            variable=self.code_editable,
            indicatoron=False,
            relief="raised",
            bg=BG_PANEL,
            fg=FG_TEXT,
            activebackground=ACCENT_D,
            activeforeground=FG_TEXT,
            selectcolor=ACCENT,
            command=self._apply_editable_state
        )
        # configure visual sizing
        editable_chk.pack(side="left", padx=(0,6))

        # Save button remains available on toolbar (left) for manual save action
        btn_save_disk = tk.Button(toolbar, text="Save File...", bg="#333333", fg=FG_TEXT, relief="flat",
                             command=self.save_generated_code)
        btn_save_disk.pack(side="left")

        text_frame = tk.Frame(parent_frame, bg=BG_MAIN)
        text_frame.pack(fill="both", expand=True, padx=6, pady=(0,6))

        self.code_text = tk.Text(text_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, wrap="none")
        self.code_text.pack(side="left", fill="both", expand=True)

        vscroll = tk.Scrollbar(text_frame, orient="vertical", command=self.code_text.yview)
        vscroll.pack(side="right", fill="y")
        self.code_text.config(yscrollcommand=vscroll.set)

        hscroll = tk.Scrollbar(parent_frame, orient="horizontal", command=self.code_text.xview)
        hscroll.pack(fill="x")
        self.code_text.config(xscrollcommand=hscroll.set)

        # configure tags for highlighting
        self.code_text.tag_configure("kw", foreground=_SYM_KEYWORD)
        self.code_text.tag_configure("str", foreground=_SYM_STRING)
        self.code_text.tag_configure("cmt", foreground=_SYM_COMMENT)
        # function name tag (new)
        self.code_text.tag_configure("fn", foreground=_SYM_FUNCTION)

        # initially populate
        try:
            code = self.generate_micropython_code()
        except Exception:
            code = "# Error generating code. Press Update Code."
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", code)

        # highlight on edits & updates
        self.code_text.bind("<KeyRelease>", lambda e: self._syntax_highlight_code())
        self._syntax_highlight_code()

        # apply initial editable state
        self._apply_editable_state()

    def _build_api_tab(self, parent_frame):
        """
        Builds the API tab with the provided documentation text inserted in read-only mode.
        Also applies simple syntax highlighting (headings, separators, quoted strings).
        """
        parent_frame.rowconfigure(0, weight=1)
        parent_frame.columnconfigure(0, weight=1)

        api_frame = tk.Frame(parent_frame, bg=BG_MAIN)
        api_frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Text widget for API doc (readonly)
        self.api_text = tk.Text(
            api_frame,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
            wrap="word"
        )
        self.api_text.pack(side="left", fill="both", expand=True)

        api_vscroll = tk.Scrollbar(api_frame, orient="vertical", command=self.api_text.yview)
        api_vscroll.pack(side="right", fill="y")
        self.api_text.config(yscrollcommand=api_vscroll.set)

        # Use a monospace font for neat alignment if available
        try:
            self.api_text.configure(font=("Consolas", 10))
        except Exception:
            pass

        # configure tags for API highlighting (reuse same colors as code)
        self.api_text.tag_configure("kw", foreground=_SYM_KEYWORD)
        self.api_text.tag_configure("str", foreground=_SYM_STRING)
        self.api_text.tag_configure("cmt", foreground=_SYM_COMMENT)
        self.api_text.tag_configure("title", foreground=_SYM_KEYWORD, underline=True)
        # function name tag for API items like restart(), connect(), etc. (new)
        self.api_text.tag_configure("fn", foreground=_SYM_FUNCTION)

        # Insert the provided documentation text exactly as given
        api_doc = """API DOCUMENTATION FOR FIRMWARE

zencmd()
Purpose:
  Launches the ZenCMD interactive terminal environment.

CLASS: system
Constructor:
  system(opt_level=0, debug=False)

Methods:
  restart()
    Purpose: Perform a controlled soft reboot.

  optlevel(level)
    Parameters:
      level (int): new optimization level
    Purpose: Update runtime optimization profile.

  info()
    Purpose: Return firmware/system diagnostic information.

  memconfig(percent=25)
    Parameters:
      percent (int): RAM reservation percentage
    Purpose: Configure memory allocation policy.

  force_mem()
    Purpose: Apply memory configuration immediately.

  mem_usage()
    Purpose: Return memory usage breakdown.

  perf_test()
    Purpose: Execute micro-benchmarks and performance checks.

  mode(m)
    Parameters:
      m (str/int): mode identifier
    Purpose: Switch system operational mode.

  firmware_update()
    Purpose: Perform firmware update sequence.

  boot_update()
    Purpose: Update bootloader / boot configuration.

  help()
    Purpose: Show usage information for system manager.

------------------------------------------------------------

CLASS: Logger
Constructor:
  Logger(log_file_system="/LOGS/system_log.txt", log_file_user="/user_log.txt", boot=False)

Public Methods:
  log(level, message, source="GENERAL")
    Purpose: Write a formatted log entry.

  error(message, source="GENERAL")
    Purpose: Log error-level messages.

  warning(message, source="GENERAL")
    Purpose: Log warning-level messages.

  debug(message, source="GENERAL")
    Purpose: Log debug messages.

  boot_complete()
    Purpose: Mark boot as complete in logs.

  viewlogs(lines=None)
    Purpose: Return recent log entries.

  clear_logs()
    Purpose: Clear both system and user logs.

  help()
    Purpose: Show Logger API usage.

------------------------------------------------------------

CLASS: Network
Constructor:
  Network(wifi_path="/wifi.json", tz_offset_sec=19800, key=b"2006")

Methods:
  connect(ssid=None, password=None, timeout=15)
    Purpose: Connect to Wi-Fi.

  disconnect()
    Purpose: Disconnect from access point.

  update_wifi_credentials(ssid, password)
    Purpose: Save new Wi-Fi credentials.

  sync_time()
    Purpose: Sync real-time clock using network time.

  ip_addr()
    Purpose: Return current IP address.

  get_rtc_time()
    Purpose: Return RTC time struct.

  print_rtc_time()
    Purpose: Print RTC time to console/log.

  ping(url="http://example.com", timeout=5)
    Purpose: Test network reachability.

  help()
    Purpose: Show Network API usage.

------------------------------------------------------------

CLASS: Task
Constructor:
  Task(name, func, args=(), kwargs=None, priority=1, mode="periodic", period=1.0, threaded=True, logger=None)

Public Methods:
  to_meta()
    Purpose: Export task metadata.

  load_meta(meta)
    Purpose: Restore task from metadata dict.

  start_loop_threaded()
    Purpose: Start task execution loop in a worker thread.

  stop()
    Purpose: Stop the task cleanly.

  runtime()
    Purpose: Return task runtime statistics.

------------------------------------------------------------

CLASS: TaskManager
Constructor:
  TaskManager(logger=None, max_workers=4, persist_path="/LOGS/task_state.json")

Public Methods:
  run(name, func, *args, priority=1, mode="periodic", period=1.0, threaded=True, **kwargs)
    Purpose: Create and schedule a task.

  run_loop(name, func, *args, priority=1, threaded=True, **kwargs)
    Purpose: Create a continuous loop task.

  stop(name)
    Purpose: Stop task by name.

  delete(name)
    Purpose: Stop and remove task.

  clear()
    Purpose: Remove all tasks.

  list()
    Purpose: Return formatted task list.

  get_load()
    Purpose: Return CPU-load summary per task.

  start_scheduler(interval_ms=100)
    Purpose: Start global scheduler.

  stop_scheduler()
    Purpose: Stop scheduler.

  clean_memory()
    Purpose: Cleanup memory and persistence state.

------------------------------------------------------------

CLASS: HUIModule
Constructor:
  HUIModule(background=color565(0,0,0))

Public Methods:
  begin()
    Purpose: Initialize display/UI system.

  clear(color=None)
    Purpose: Clear screen with color.

  add_block(block)
    Purpose: Add UI block (button, text, etc.).

  _read_axis(cmd)
    Purpose: Low-level ADC touch read.

  _get_raw_touch()
    Purpose: Return raw (x, y) touch values.

  map_touch(raw_x, raw_y)
    Purpose: Convert raw touch to calibrated coordinates.

  get_touch()
    Purpose: Return processed touch event.

  calibrate()
    Purpose: Run touch calibration routine.

  boot_screen(text="ZENO MICRO PC", duration=5)
    Purpose: Show boot splash.

  on()
    Purpose: Power on screen/backlight.

  off()
    Purpose: Power off screen/backlight.

  fade_in(pin_num=14, fade_time=0.5, freq=1000)
    Purpose: Smooth backlight fade-in.

  fade_out(pin_num=14, fade_time=0.5, freq=1000)
    Purpose: Smooth backlight fade-out.

  draw_bmp(x, y, path)
    Purpose: Fast BMP renderer for display.

------------------------------------------------------------

CLASS: UIButton
Constructor:
  UIButton(x, y, w, h, label, color=None, text_color=None, margin=5, action=None)

Methods:
  draw(ui)
    Purpose: Draw button to UI context.

  get_touch(ui)
    Purpose: Detect press, execute action() if set.

------------------------------------------------------------

CLASS: UIText
Constructor:
  UIText(x, y, text, fg=None, bg=None)

Methods:
  draw(ui)
    Purpose: Draw text on screen.

------------------------------------------------------------

CLASS: UIScreen
Constructor:
  UIScreen(ui, fg=None, background=None, on_exit=None, taskbarcolor=None, taskbar_text=None, taskbar_text_color=None, *args, **kwargs)

Methods:
  show()
    Purpose: Render screen and widgets.

  close()
    Purpose: Close screen, call on_exit if provided.

  draw()
    Purpose: Update/redraw screen.

  check()
    Purpose: Process events/touches.

  add_widget(widget)
    Purpose: Add widget (UIButton/UIText).

  remove_widget(widget)
    Purpose: Remove widget.

------------------------------------------------------------

CLASS: Disk
Constructor:
  Disk(mount_point="/SYSTEM32")

Methods:
  check(retries=5, delay=0.2)
    Purpose: Probe for storage.

  begin()
    Purpose: Mount filesystem.

  listfiles(target_path="/SYSTEM32/Admin/ROM")
    Purpose: List files in a directory.

  mkdir(path)
    Purpose: Create directory.

  info(path=None)
    Purpose: Return filesystem or file info.

  delete(p)
    Purpose: Delete file.

  del_folder(p)
    Purpose: Recursively delete folder.

  help()
    Purpose: Show Disk API usage.

------------------------------------------------------------

CLASS: Git
Constructor:
  Git(base_raw=None, default_branch="main")

Methods:
  download(user, repo, path, branch="main")
    Purpose: Fetch raw file from GitHub.

  help()
    Purpose: Show Git helper usage.

------------------------------------------------------------

CLASS: AppInstaller
Constructor:
  AppInstaller()

Methods:
  prompt_and_install()
    Purpose: Interactive install prompt.

  _build_remote_path(app_name)
    Purpose: Build GitHub raw URL for app.

  install(app_name)
    Purpose: Download and install application.

  uninstall(name)
    Purpose: Remove installed app.

  listapps()
    Purpose: List installed apps.

------------------------------------------------------------
END OF DOCUMENT
------------------------------------------------------------

"""
        # Insert and lock
        self.api_text.delete("1.0", "end")
        self.api_text.insert("1.0", api_doc)
        # Apply highlighting immediately
        self._syntax_highlight_api()
        # Lock content (read-only)
        self.api_text.config(state="disabled")

    def _syntax_highlight_api(self):
        """
        Lightweight highlighting for the API doc:
         - Title / ALL-CAPS headings → 'title' tag
         - 'CLASS:' and 'Constructor' / 'Methods' lines → 'kw' tag
         - Separator lines (----...) → 'cmt' tag
         - Strings in quotes → 'str' tag
         - Function names followed by parentheses → 'fn' tag (API functions)
        This runs against the api_text widget.
        """
        # temporarily enable for tagging
        was_disabled = False
        if str(self.api_text['state']) == 'disabled':
            was_disabled = True
            self.api_text.config(state="normal")

        text = self.api_text.get("1.0", "end-1c")
        # clear previous tags
        for tag in ("kw", "str", "cmt", "title", "fn"):
            self.api_text.tag_remove(tag, "1.0", "end")

        if not text:
            if was_disabled:
                self.api_text.config(state="disabled")
            return

        # Title lines (very short heuristic: all caps and not too long)
        for m in re.finditer(r"(?m)^(API DOCUMENTATION FOR FIRMWARE|END OF DOCUMENT|CLASS:.*)$", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            # CLASS: lines are keywords, top title gets 'title'
            if m.group(1).startswith("API DOCUMENTATION"):
                self.api_text.tag_add("title", start, end)
            else:
                self.api_text.tag_add("kw", start, end)

        # Lines that are clearly section keywords
        for m in re.finditer(r"(?m)^(Constructor:|Methods:|Public Methods:|Purpose:|Parameters:|Returns:)", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.api_text.tag_add("kw", start, end)

        # Separator lines (dashes)
        for m in re.finditer(r"(?m)^[-]{10,}.*$", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.api_text.tag_add("cmt", start, end)

        # Quoted strings (single or double)
        for m in re.finditer(r"('(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\")", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.api_text.tag_add("str", start, end)

        # Short headings in ALL CAPS (like 'CLASS: XYZ' already handled, but extra)
        for m in re.finditer(r"(?m)^[A-Z0-9][A-Z0-9 _:,-]{2,}$", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.api_text.tag_add("title", start, end)

        # API function names: highlight the name before '(' for constructs like restart(), connect(url), etc.
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?=\()", text):
            name_start = m.start(1)
            name_end = m.end(1)
            start = f"1.0 + {name_start} chars"
            end   = f"1.0 + {name_end} chars"
            # skip if inside an existing quoted string or separator area
            tags = self.api_text.tag_names(start)
            if "str" in tags or "cmt" in tags:
                continue
            self.api_text.tag_add("fn", start, end)

        # restore read-only if needed
        if was_disabled:
            self.api_text.config(state="disabled")

    def _apply_editable_state(self):
        """Apply the self.code_editable state to the code text widget."""
        editable = bool(self.code_editable.get())
        if editable:
            self.code_text.config(state="normal")
            # re-apply highlight after enabling
            self._syntax_highlight_code()
            self.status.config(text="Editor unlocked for editing.")
        else:
            # make read-only by disabling widget
            # but ensure tags remain visible by keeping contents unchanged
            self.code_text.config(state="disabled")
            self.status.config(text="Editor locked (read-only).")

    def _update_code_tab(self):
        try:
            code = self.generate_micropython_code()
        except Exception as e:
            messagebox.showerror("Code generation error", str(e))
            return
        self.code_text.config(state="normal")
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", code)
        self._syntax_highlight_code()
        # respect editable switch: if switch is OFF, lock after update
        if not self.code_editable.get():
            self.code_text.config(state="disabled")
        self.status.config(text="Code updated.")

    def _on_tab_changed(self, event):
        try:
            tab_text = event.widget.tab(event.widget.select(), "text")
            if tab_text == "Code":
                self._update_code_tab()
            elif tab_text == "API":
                # re-run API highlighting in case font/size changed or user updated doc externally
                try:
                    self._syntax_highlight_api()
                except Exception:
                    pass
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Lightweight Python syntax highlighter (keywords, strings, comments)
    # -----------------------------------------------------------------
    _py_keywords = set("""
    False None True and as assert async await break class continue def del elif else
    except finally for from global if import in is lambda nonlocal not or pass
    raise return try while with yield    """.split())
 
    def _syntax_highlight_code(self):
        # if widget disabled, temporarily enable for tagging then restore state
        was_disabled = False
        if str(self.code_text['state']) == 'disabled':
            was_disabled = True
            self.code_text.config(state="normal")

        text = self.code_text.get("1.0", "end-1c")
        # clear previous tags
        self.code_text.tag_remove("kw", "1.0", "end")
        self.code_text.tag_remove("str", "1.0", "end")
        self.code_text.tag_remove("cmt", "1.0", "end")
        self.code_text.tag_remove("fn", "1.0", "end")

        if not text:
            if was_disabled:
                self.code_text.config(state="disabled")
            return

        # comments
        for m in re.finditer(r"#.*", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.code_text.tag_add("cmt", start, end)

        # strings (single, double, triple)
        for m in re.finditer(r"(?s)('''.*?'''|\"\"\".*?\"\"\"|'.*?'|\".*?\")", text):
            start = f"1.0 + {m.start()} chars"
            end   = f"1.0 + {m.end()} chars"
            self.code_text.tag_add("str", start, end)

        # keywords — avoid matching inside identifiers; skip areas already tagged as strings/comments
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", text):
            word = m.group(1)
            if word in self._py_keywords:
                idx = m.start()
                pos = f"1.0 + {idx} chars"
                tags = self.code_text.tag_names(pos)
                if "str" in tags or "cmt" in tags:
                    continue
                start = f"1.0 + {m.start()} chars"
                end   = f"1.0 + {m.end()} chars"
                self.code_text.tag_add("kw", start, end)

        # function definitions: highlight the function name after 'def '
        for m in re.finditer(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\b", text):
            name_start = m.start(1)
            name_end = m.end(1)
            pos = f"1.0 + {name_start} chars"
            tags = self.code_text.tag_names(pos)
            if "str" in tags or "cmt" in tags:
                continue
            self.code_text.tag_add("fn", f"1.0 + {name_start} chars", f"1.0 + {name_end} chars")

        # function calls: word followed by '(' (skip keywords and inside strings/comments)
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?=\()", text):
            name = m.group(1)
            if name in self._py_keywords:
                continue
            name_start = m.start(1)
            pos = f"1.0 + {name_start} chars"
            tags = self.code_text.tag_names(pos)
            if "str" in tags or "cmt" in tags:
                continue
            self.code_text.tag_add("fn", f"1.0 + {m.start(1)} chars", f"1.0 + {m.end(1)} chars")

        if was_disabled:
            self.code_text.config(state="disabled")

    def _current_repo_path_preview(self):
        app_name = self.app_name.get().strip() or "MyApp"
        fname = app_name.replace(" ", "_") + ".py"
        return f"APPS/{fname}"

    def _update_github_path_label(self):
        self.github_path_label.config(text=self._current_repo_path_preview())

    # -----------------------------------------------------------------
    # Widget properties panel helpers
    # -----------------------------------------------------------------

    def populate_widget_props(self):
        widget = self.selected_widget

        self.widget_type_var.set("")

        # Clear all entries first
        for e in (
        self.entry_label,
        self.entry_action,
        self.entry_x,
        self.entry_y,
        self.entry_w,
        self.entry_h,
        self.entry_margin,
        self.entry_value,   # <-- added
        ):
            e.config(state="normal")
            e.delete(0, tk.END)

    # Width/Height editable types
        if widget and widget.type in ("Button", "Layer", "Slider", "ProgressBar", "Panel"):
            state_wh = "normal"
        else:
            state_wh = "disabled"

        state_margin = "normal" if widget and widget.type == "Button" else "disabled"
        state_action = "normal" if widget and widget.type == "Button" else "disabled"
        state_value  = "normal" if widget and widget.type == "Slider" else "disabled"

        self.entry_w.config(state=state_wh)
        self.entry_h.config(state=state_wh)
        self.entry_margin.config(state=state_margin)
        self.entry_action.config(state=state_action)
        self.entry_value.config(state=state_value)

        if widget is None:
            return

        self.widget_type_var.set(widget.type)
        self.entry_label.insert(0, widget.label)
        self.entry_x.insert(0, str(widget.x))
        self.entry_y.insert(0, str(widget.y))

        if widget.type in ("Button", "Layer", "Slider", "ProgressBar", "Panel"):
            self.entry_w.insert(0, str(widget.width))
            self.entry_h.insert(0, str(widget.height))

        if widget.type == "Button":
            self.entry_margin.insert(0, str(widget.margin))
            self.entry_action.insert(0, widget.action)

        if widget.type == "Slider":
            self.entry_value.insert(0, str(widget.value))

    def apply_widget_props(self, live=False):
        widget = self.selected_widget
        if widget is None:
            return

        widget.label = self.entry_label.get()

        try:
            widget.x = int(self.entry_x.get())
            widget.y = int(self.entry_y.get())

            if widget.type in ("Button", "Layer"):
                w_new = int(self.entry_w.get())
                h_new = int(self.entry_h.get())
                if w_new > 0:
                    widget.width = w_new
                if h_new > 0:
                    widget.height = h_new

            if widget.type == "Button":
                m_new = int(self.entry_margin.get())
                if m_new >= 0:
                    widget.margin = m_new
                widget.action = self.entry_action.get()

            self.status.config(text=f"Updated {widget.type}: {widget.label}")
        except ValueError:
            self.status.config(text="Warning: X, Y, W, H, and Margin must be integers.")
            return

        if live:
            self.redraw_canvas()

    def select_widget(self, widget):
        self.selected_widget = widget
        self.widget_list.selection_clear(0, tk.END)
        try:
            index = self.widgets.index(widget)
            self.widget_list.selection_set(index)
            self.widget_list.activate(index)
        except (ValueError, TypeError):
            pass
        self.populate_widget_props()
        self.redraw_canvas()

    def on_widget_list_select(self, event):
        selection = self.widget_list.curselection()
        if selection:
            index = selection[0]
            if index < len(self.widgets):
                widget = self.widgets[index]
                self.select_widget(widget)
            else:
                self.selected_widget = None
                self.populate_widget_props()
                self.redraw_canvas()
        else:
            self.selected_widget = None
            self.populate_widget_props()
            self.redraw_canvas()

    def delete_selected_widget(self):
        if self.selected_widget:
            self.widgets.remove(self.selected_widget)
            self.selected_widget = None
            self.update_widget_list()
            self.populate_widget_props()
            self.redraw_canvas()
            self.status.config(text="Widget deleted.")
        else:
            self.status.config(text="No widget selected to delete.")

    def update_widget_list(self):
        self.widget_list.delete(0, tk.END)
        for widget in self.widgets:
            self.widget_list.insert(
                tk.END,
                f"[{widget.type}] {widget.label} ({widget.x}, {widget.y})"
            )

    # -----------------------------------------------------------------
    # Canvas interaction
    # -----------------------------------------------------------------

    def mode_add_button(self):
        self.mode = "add_button"
        self.status.config(text="Mode: Click on the screen to place a Button.")
        self.canvas.config(cursor="crosshair")
        self.select_widget(None)

    def mode_add_text(self):
        self.mode = "add_text"
        self.status.config(text="Mode: Click on the screen to place a Text.")
        self.canvas.config(cursor="crosshair")
        self.select_widget(None)

    def mode_add_layer(self):
        self.mode = "add_layer"
        self.status.config(text="Mode: Click on the screen to place a Layer.")
        self.canvas.config(cursor="crosshair")
        self.select_widget(None)
    def mode_add_slider(self):
        self.mode = "add_slider"
        self.canvas.config(cursor="crosshair")

    def mode_add_toggle(self):
        self.mode = "add_toggle"
        self.canvas.config(cursor="crosshair")

    def mode_add_progress(self):
        self.mode = "add_progress"
        self.canvas.config(cursor="crosshair")

    def mode_add_panel(self):
        self.mode = "add_panel"
        self.canvas.config(cursor="crosshair")
    def get_widget_at_click(self, sx, sy):
        for widget in reversed(self.widgets):
            if widget.type in ("Button", "Layer", "Slider", "ProgressBar", "Panel"):
                if widget.x <= sx < widget.x + widget.width and \
                   widget.y <= sy < widget.y + widget.height:
                    return widget
            elif widget.type == "Text":
                if widget.x - 5 <= sx < widget.x + 5 and \
                   widget.y - 5 <= sy < widget.y + 5:
                    return widget
        return None

    # --- Resize handles (for Button & Layer) ---

    def _hit_resize_handle(self, widget, sx, sy, radius=5):
        """
        Given logical coords (sx, sy), return which corner was hit:
        'tl', 'tr', 'bl', 'br' or None.
        """
        if widget.type not in ("Button", "Layer", "Slider", "ProgressBar", "Panel"):
            return None

        x1 = widget.x
        y1 = widget.y
        x2 = widget.x + widget.width
        y2 = widget.y + widget.height

        corners = {
            "tl": (x1, y1),
            "tr": (x2, y1),
            "bl": (x1, y2),
            "br": (x2, y2),
        }

        for name, (cx, cy) in corners.items():
            if abs(sx - cx) <= radius and abs(sy - cy) <= radius:
                return name
        return None

    def _find_resize_handle_at(self, sx, sy):
        """
        Check all Button/Layer widgets (topmost first) for a resize handle hit.
        Returns (widget, handle_name) or (None, None).
        """
        for widget in reversed(self.widgets):
            if widget.type not in ("Button", "Layer", "Slider", "ProgressBar", "Panel"):
                continue
            handle = self._hit_resize_handle(widget, sx, sy)
            if handle is not None:
                return widget, handle
        return None, None

    def on_canvas_press(self, event):
        sx, sy = self.logical_coords(event)
        if sx is None:
            return

        # Placement modes
        if self.mode == "add_button":
            new_widget = ButtonWidget(x=sx - 50, y=sy - 15)
            new_widget.label = f"Button {len(self.widgets) + 1}"
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return

        elif self.mode == "add_text":
            new_widget = TextWidget(x=sx, y=sy)
            new_widget.label = f"Text {len(self.widgets) + 1}"
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return

        elif self.mode == "add_layer":
            default_w = 100
            default_h = 40
            new_widget = LayerWidget(
                x=sx - default_w // 2,
                y=sy - default_h // 2,
                width=default_w,
                height=default_h,
            )
            new_widget.label = f"Layer {len(self.widgets) + 1}"
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return
        elif self.mode == "add_slider":
            new_widget = SliderWidget(sx - 60, sy - 10)
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return

        elif self.mode == "add_toggle":
            new_widget = ToggleWidget(sx - 25, sy - 12)
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return

        elif self.mode == "add_progress":
            new_widget = ProgressBarWidget(sx - 60, sy - 10)
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return
    
        elif self.mode == "add_panel":
            new_widget = PanelWidget(sx - 75, sy - 50)
            self.widgets.append(new_widget)
            self.mode = None
            self.canvas.config(cursor="")
            self.update_widget_list()
            self.select_widget(new_widget)
            return
            # Check resize handle (Button or Layer)
        widget, handle = self._find_resize_handle_at(sx, sy)
        if widget and handle:
            self.resize_target = widget
            self.resize_handle = handle
            self.dragging_widget = None
            self.select_widget(widget)
            self.status.config(text=f"Resizing {widget.type} ({handle.upper()} corner)")
            return

        # Normal selection / move
        widget = self.get_widget_at_click(sx, sy)
        if widget:
            self.select_widget(widget)
            self.dragging_widget = widget
            self.drag_offset_px = (sx - widget.x, sy - widget.y)
        else:
            self.select_widget(None)
            self.dragging_widget = None

    def _resize_with_handle(self, widget, handle, sx, sy):
        """
        Resize a Button/Layer by dragging one corner.
        """
        if widget.type not in ("Button", "Layer"):
            return

        min_w = 10
        min_h = 10

        x1 = widget.x
        y1 = widget.y
        x2 = widget.x + widget.width
        y2 = widget.y + widget.height

        sx = max(0, min(LOGICAL_WIDTH, sx))
        sy = max(0, min(LOGICAL_HEIGHT, sy))

        if handle == "tl":
            new_x1 = min(sx, x2 - min_w)
            new_y1 = min(sy, y2 - min_h)
            widget.x = new_x1
            widget.y = new_y1
            widget.width  = x2 - new_x1
            widget.height = y2 - new_y1
        elif handle == "tr":
            new_x2 = max(sx, x1 + min_w)
            new_y1 = min(sy, y2 - min_h)
            widget.y = new_y1
            widget.width  = new_x2 - x1
            widget.height = y2 - new_y1
        elif handle == "bl":
            new_x1 = min(sx, x2 - min_w)
            new_y2 = max(sy, y1 + min_h)
            widget.x = new_x1
            widget.width  = x2 - new_x1
            widget.height = new_y2 - y1
        elif handle == "br":
            new_x2 = max(sx, x1 + min_w)
            new_y2 = max(sy, y1 + min_h)
            widget.width  = new_x2 - x1
            widget.height = new_y2 - y1

    def on_canvas_drag(self, event):
        sx, sy = self.logical_coords(event)
        if sx is None:
            return

        # --- Slider value drag ---
        if self.selected_widget and self.selected_widget.type == "Slider":
            widget = self.selected_widget

            # Only update if dragging inside slider bounds
            if widget.x <= sx <= widget.x + widget.width:
                ratio = (sx - widget.x) / widget.width
                widget.value = max(0, min(100, int(ratio * 100)))

                self.populate_widget_props()  # update value field
                self.redraw_canvas()
                return

        # --- Resizing ---
        if self.resize_target is not None:
            self._resize_with_handle(self.resize_target, self.resize_handle, sx, sy)
            self.populate_widget_props()
            self.redraw_canvas()
            return

        # --- Moving ---
        if self.dragging_widget:
            new_x = sx - self.drag_offset_px[0]
            new_y = sy - self.drag_offset_px[1]

            if 0 <= new_x < LOGICAL_WIDTH and 0 <= new_y < LOGICAL_HEIGHT:
                self.dragging_widget.x = new_x
                self.dragging_widget.y = new_y
                self.populate_widget_props()
                self.redraw_canvas()

    def on_canvas_release(self, event):
        if self.resize_target is not None:
            self.status.config(
                text=f"Resized {self.resize_target.type} to {self.resize_target.width}x{self.resize_target.height}"
            )
        elif self.dragging_widget:
            self.status.config(
                text=f"Moved {self.dragging_widget.type} to ({self.dragging_widget.x}, {self.dragging_widget.y})"
            )

        self.dragging_widget = None
        self.drag_offset_px = (0, 0)
        self.resize_target = None
        self.resize_handle = None

    # -----------------------------------------------------------------
    # Preview scaling / drawing
    # -----------------------------------------------------------------

    def _on_root_configure(self, event):
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(100, self._set_pane_ratio)

    def _set_pane_ratio(self):
        try:
            w = self.main_pane.winfo_width()
            if w <= 0:
                return
            self.main_pane.sash_place(0, int(w * 0.75), 0)
        except Exception:
            pass

    def on_preview_resize(self, event):
        cw = event.width
        ch = event.height
        if cw <= 10 or ch <= 10:
            return

        avail_w = max(1, cw - 20)
        avail_h = max(1, ch - 20)

        scale_x = avail_w / LOGICAL_WIDTH
        scale_y = avail_h / LOGICAL_HEIGHT
        self.scale = max(0.1, min(scale_x, scale_y))
        self.redraw_canvas()

    def logical_coords(self, event):
        if self.scale <= 0:
            return None, None

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        screen_w = LOGICAL_WIDTH * self.scale
        screen_h = LOGICAL_HEIGHT * self.scale
        self.offset_x = (cw - screen_w) / 2
        self.offset_y = (ch - screen_h) / 2

        sx = (event.x - self.offset_x) / self.scale
        sy = (event.y - self.offset_y) / self.scale

        if sx < 0 or sy < 0 or sx >= LOGICAL_WIDTH or sy >= LOGICAL_HEIGHT:
            return None, None

        return int(sx), int(sy)

    def redraw_canvas(self):
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        # background
        self.canvas.create_rectangle(0, 0, cw, ch, fill="#202020", outline="")

        screen_w = LOGICAL_WIDTH * self.scale
        screen_h = LOGICAL_HEIGHT * self.scale
        self.offset_x = (cw - screen_w) / 2
        self.offset_y = (ch - screen_h) / 2

        x0 = self.offset_x
        y0 = self.offset_y
        x1 = x0 + screen_w
        y1 = y0 + screen_h

        # main screen rect
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill=hex_from_rgb(self.screen_bg),
            outline="#FFFFFF",
            width=2,
        )

        # taskbar
        tb_hex = hex_from_rgb(self.taskbar_color)
        tb_height = 35
        tb_y1 = y0 + tb_height * self.scale
        self.canvas.create_rectangle(
            x0, y0, x1, tb_y1,
            fill=tb_hex,
            outline=tb_hex,
        )

        text = self.taskbar_text.get().strip()
        if text:
            tt_hex = hex_from_rgb(self.taskbar_text_color)
            x_center = x0 + (screen_w / 2)
            y_center = y0 + (tb_height * self.scale / 2)
            self.canvas.create_text(x_center, y_center, text=text, fill=tt_hex)

        # Exit button – red square with white X
        if self.screen_has_exit.get():
            btn_size = 35  # logical
            btn_px = btn_size * self.scale

            ex_x1 = x1 - 4 * self.scale
            ex_y1 = y0 + btn_px
            ex_x0 = ex_x1 - btn_px
            ex_y0 = y0

            # red square
            self.canvas.create_rectangle(
                ex_x0, ex_y0, ex_x1, ex_y1,
                fill="#A00000",
                outline="#A00000",
                width=1,
            )

            # white X
            pad = 7 * self.scale
            x_left   = ex_x0 + pad
            x_right  = ex_x1 - pad
            y_top    = ex_y0 + pad
            y_bottom = ex_y1 - pad

            self.canvas.create_line(
                x_left,  y_top,
                x_right, y_bottom,
                fill="#FFFFFF",
                width=2 * self.scale,
            )
            self.canvas.create_line(
                x_right, y_top,
                x_left,  y_bottom,
                fill="#FFFFFF",
                width=2 * self.scale,
            )

        # Draw layers, then buttons, then text
        draw_order = ("Layer", "Panel", "ProgressBar", "Slider", "Button", "Toggle", "Text")

        for draw_type in draw_order:
            for widget in self.widgets:
                if widget.type != draw_type:
                    continue

                x_log, y_log = widget.x, widget.y
                w_log, h_log = widget.width, widget.height

                x0_scaled = self.offset_x + x_log * self.scale
                y0_scaled = self.offset_y + y_log * self.scale
                x1_scaled = self.offset_x + (x_log + w_log) * self.scale
                y1_scaled = self.offset_y + (y_log + h_log) * self.scale

                outline_color = "#FFFFFF" if widget is self.selected_widget else ""
                line_width = 1

                if widget.type == "Layer":
                    self.canvas.create_rectangle(
                        x0_scaled, y0_scaled, x1_scaled, y1_scaled,
                        fill=hex_from_rgb(widget.bg_color),
                        outline=outline_color,
                        width=line_width,
                        tag="widget"
                    )

                    # Only show resize handles when actively resizing
                    if widget is self.resize_target:
                        handle_size = 6 * self.scale
                        half = handle_size / 2
                        corners = [
                            (x0_scaled, y0_scaled),
                            (x1_scaled, y0_scaled),
                            (x0_scaled, y1_scaled),
                            (x1_scaled, y1_scaled),
                        ]
                        for cx, cy in corners:
                            self.canvas.create_rectangle(
                                cx - half, cy - half,
                                cx + half, cy + half,
                                fill="#ffffff",
                                outline="#000000",
                                width=1,
                                tag="handle"
                            )

                elif widget.type == "Button":
                    self.canvas.create_rectangle(
                        x0_scaled, y0_scaled, x1_scaled, y1_scaled,
                        fill=hex_from_rgb(widget.bg_color),
                        outline=outline_color,
                        width=line_width,
                        tag="widget"
                    )
                    text_x_center = x0_scaled + (w_log * self.scale) / 2
                    text_y_center = y0_scaled + (h_log * self.scale) / 2
                    self.canvas.create_text(
                        text_x_center, text_y_center,
                        text=widget.label,
                        fill=hex_from_rgb(widget.fg_color),
                        tag="widget"
                    )

                    # Only show handles when actively resizing this button
                    if widget is self.resize_target:
                        handle_size = 6 * self.scale
                        half = handle_size / 2
                        corners = [
                            (x0_scaled, y0_scaled),
                            (x1_scaled, y0_scaled),
                            (x0_scaled, y1_scaled),
                            (x1_scaled, y1_scaled),
                        ]
                        for cx, cy in corners:
                            self.canvas.create_rectangle(
                                cx - half, cy - half,
                                cx + half, cy + half,
                                fill="#ffffff",
                                outline="#000000",
                                width=1,
                                tag="handle"
                            )

                elif widget.type == "Text":
                    self.canvas.create_text(
                        x0_scaled, y0_scaled,
                        text=widget.label,
                        fill=hex_from_rgb(widget.fg_color),
                        anchor="nw",
                        tag="widget"
                    )
                    if widget is self.selected_widget:
                        self.canvas.create_rectangle(
                            x0_scaled, y0_scaled,
                            x0_scaled + 5, y0_scaled + 5,
                            outline="#FFFFFF",
                            width=1,
                            tag="selection"
                        )
                elif widget.type == "Slider":

                    track_y = y0_scaled + (widget.height * self.scale) / 2
                    track_thickness = 4

                     # Track
                    self.canvas.create_rectangle(
                    x0_scaled,
                    track_y - track_thickness,
                    x1_scaled,
                    track_y + track_thickness,
                    fill=hex_from_rgb(widget.track_color),
                    outline=""
                    )

                    # Fill
                    ratio = widget.value / 100
                    fill_x = x0_scaled + ratio * (widget.width * self.scale)

                    self.canvas.create_rectangle(
                    x0_scaled,
                    track_y - track_thickness,
                    fill_x,
                    track_y + track_thickness,
                    fill=hex_from_rgb(widget.fill_color),
                    outline=""
                    )

                    # Smaller knob
                    knob_r = widget.knob_radius * self.scale
                    knob_x = fill_x
                    knob_y = y0_scaled + (widget.height * self.scale) / 2

                    self.canvas.create_oval(
                    knob_x - knob_r,
                    knob_y - knob_r,
                    knob_x + knob_r,
                    knob_y + knob_r,
                    fill=hex_from_rgb(widget.knob_color),
                    outline="#000000"
                    )

                    # selection border
                    if widget is self.selected_widget:
                        self.canvas.create_rectangle(
                            x0_scaled, y0_scaled,
                            x1_scaled, y1_scaled,
                            outline="#FFFFFF"
                        )
                elif widget.type == "ProgressBar":

                    self.canvas.create_rectangle(
                    x0_scaled,
                    y0_scaled,
                    x1_scaled,
                    y1_scaled,
                    outline="#ffffff"
                    )

                    ratio = widget.value / 100
                    fill_w = ratio * (widget.width*self.scale)

                    self.canvas.create_rectangle(
                    x0_scaled,
                    y0_scaled,
                    x0_scaled + fill_w,
                    y1_scaled,
                    fill="#00c6ff",
                    outline=""
                    )
                elif widget.type == "Toggle":

                    color = "#00cc66" if widget.state else "#555555"

                    self.canvas.create_rectangle(
                    x0_scaled,
                    y0_scaled,
                    x1_scaled,
                    y1_scaled,
                    fill=color,
                    outline=""
                    )

                    knob_radius = widget.height*self.scale/2 - 2

                    if widget.state:
                        knob_x = x1_scaled - knob_radius - 2
                    else:
                        knob_x = x0_scaled + knob_radius + 2

                    self.canvas.create_oval(
                    knob_x - knob_radius,
                    y0_scaled + 2,
                    knob_x + knob_radius,
                    y1_scaled - 2,
                    fill="#ffffff"
                    )
                elif widget.type == "Panel":

                    self.canvas.create_rectangle(
                    x0_scaled,
                    y0_scaled,
                    x1_scaled,
                    y1_scaled,
                    fill="#2b2b2b",
                    outline="#555555"
                    )
    # -----------------------------------------------------------------
    # Color pickers (correct askcolor usage)
    # -----------------------------------------------------------------

    def pick_screen_bg(self):
        rgb_tuple, hex_code = colorchooser.askcolor(
            initialcolor=hex_from_rgb(self.screen_bg),
            title="Choose Screen Background"
        )
        if rgb_tuple:
            self.screen_bg = tuple(int(c) for c in rgb_tuple)
            self.redraw_canvas()

    def pick_taskbar_color(self):
        rgb_tuple, hex_code = colorchooser.askcolor(
            initialcolor=hex_from_rgb(self.taskbar_color),
            title="Choose Taskbar Color"
        )
        if rgb_tuple:
            self.taskbar_color = tuple(int(c) for c in rgb_tuple)
            self.redraw_canvas()

    def pick_taskbar_text_color(self):
        rgb_tuple, hex_code = colorchooser.askcolor(
            initialcolor=hex_from_rgb(self.taskbar_text_color),
            title="Choose Taskbar Text Color"
        )
        if rgb_tuple:
            self.taskbar_text_color = tuple(int(c) for c in rgb_tuple)
            self.redraw_canvas()

    def pick_widget_fg(self):
        if self.selected_widget:
            rgb_tuple, hex_code = colorchooser.askcolor(
                initialcolor=hex_from_rgb(self.selected_widget.fg_color),
                title="Choose Widget Text Color"
            )
            if rgb_tuple:
                self.selected_widget.fg_color = tuple(int(c) for c in rgb_tuple)
                self.redraw_canvas()
        else:
            messagebox.showwarning("No Widget Selected", "Please select a widget first.")

    def pick_widget_bg(self):
        if self.selected_widget and self.selected_widget.type in ("Button", "Layer", "Slider"):
            rgb_tuple, hex_code = colorchooser.askcolor(
                initialcolor=hex_from_rgb(self.selected_widget.bg_color),
                title="Choose Widget Background Color"
            )
        if self.selected_widget.type == "Slider":
            self.selected_widget.track_color = tuple(int(c) for c in rgb_tuple)
            if rgb_tuple:
                self.selected_widget.bg_color = tuple(int(c) for c in rgb_tuple)
                self.redraw_canvas()
        elif self.selected_widget and self.selected_widget.type == "Text":
            messagebox.showinfo("Text Widget", "Text widgets typically do not use a background color.")
        else:
            messagebox.showwarning("No Widget Selected", "Please select a widget first.")

    # -----------------------------------------------------------------
    # Code generation / GitHub upload
    # -----------------------------------------------------------------

    def generate_micropython_code(self):
        """
        Generates MicroPython code that:
        - imports HUIModule, UIScreen, UIButton, UIText (added)
        - creates screen, layers, text, buttons
        - runs a main loop checking button touches + user sketch
        Note: color565(...) uses B,G,R ordering per your API.
        """
        app_name = self.app_name.get().strip() or "MyApp"
        author   = self.app_author.get().strip() or "Phoenix"
        version  = self.app_version.get().strip() or "1.0.0"
        func     = self.func_name.get().strip() or "main"

        bg_r, bg_g, bg_b   = self.screen_bg
        tb_r, tb_g, tb_b   = self.taskbar_color
        tt_r, tt_g, tt_b   = self.taskbar_text_color
        tb_text            = self.taskbar_text.get().strip() or app_name
        lines = []
        lines.append("# Auto-generated Zeno UI screen")
        lines.append(f"# App: {app_name} (v{version}) by {author}")
        lines.append("")
        lines.append("import time")
        lines.append("from ili9341 import color565")
        # include UIText in imports so Text API present
        lines.append("from Graphics import UIScreen, UIButton, UIText, UISlider, UIToggleSwitch, UIProgressBar, UIPanel")
        lines.append("import zeno")
        lines.append(f"APP_NAME    = {app_name!r}")
        lines.append(f"APP_AUTHOR  = {author!r}")
        lines.append(f"APP_VERSION = {version!r}")
        lines.append("")
        lines.append("ui=zeno.ui")
        lines.append(
            "    screen = UIScreen("
            "ui, "
            f"background=color565({bg_b}, {bg_g}, {bg_r}), "
            f"taskbarcolor=color565({tb_b}, {tb_g}, {tb_r}), "
            f"taskbar_text={tb_text!r}, "
            f"taskbar_text_color=color565({tt_b}, {tt_g}, {tt_r}), "
            "on_exit=on_exit"
            ")"
        )
        lines.append("")
        if self.screen_has_exit.get():
            lines.append("    screen.start(ui)")
        else:
            lines.append("    screen.start_withoutexit(ui)")
        lines.append("")
        lines.append("    # Draw layers (colored rectangles)")
        for w in self.widgets:
            if w.type == "Layer":
                r, g, b = w.bg_color
                lines.append(
                    f"    screen.layer({w.x}, {w.y}, {w.width}, {w.height}, "
                    f"color565({b}, {g}, {r}))"
                )
        lines.append("")
        # Add texts (UIText) BEFORE buttons so layout matches preview order
        lines.append("    # Create and draw texts (UIText)")
        for w in self.widgets:
            if w.type == "Text":
                tr, tg, tb = w.fg_color
                label = w.label.replace("'", "\\'")
                # pass BGR order to color565, matching your firmware API
                lines.append(
                    f"    UIText({w.x}, {w.y}, '{label}', color=color565({tb}, {tg}, {tr})).draw(ui)"
                )
            if w.type == "Slider":
                lines.append(f"    UISlider({w.x}, {w.y}, {w.width}, value={w.value}).draw(ui)")
            if w.type == "Toggle":
                state = "True" if w.state else "False"
                lines.append(f"    UIToggleSwitch({w.x}, {w.y}, {w.width}, state={state}).draw(ui)")
            if w.type == "ProgressBar":
                lines.append( f"    UIProgressBar({w.x}, {w.y}, {w.width}, value={w.value}).draw(ui)")
            if w.type == "Panel":
                lines.append( f"    UIPanel({w.x}, {w.y}, {w.width}, {w.height}).draw(ui)")
        lines.append("")
        lines.append("    # Create and draw buttons")
        lines.append("    buttons = []")

        # Generate button creation + optional action stubs
        defined_actions = set()
        for w in self.widgets:
            if w.type == "Button":
                br, bgc, bb = w.bg_color
                tr, tg, tb = w.fg_color
                label = w.label.replace("'", "\\'")
                action_name = w.action.strip()

                if action_name and action_name not in defined_actions:
                    defined_actions.add(action_name)
                    lines.append(f"    def {action_name}():")
                    lines.append(f"        print('Button {label} pressed')")
                    lines.append("")

                action_expr = action_name if action_name else "None"

                lines.append(
                    "    buttons.append("
                    f"UIButton({w.x}, {w.y}, {w.width}, {w.height}, "
                    f"label='{label}', "
                    # BGR order
                    f"color=color565({bb}, {bgc}, {br}), "
                    f"text_color=color565({tb}, {tg}, {tr}), "
                    f"margin={w.margin}, "
                    f"action={action_expr}"
                    ")"
                    ")"
                )

        lines.append("")
        lines.append("    for btn in buttons:")
        lines.append("        btn.draw(ui)")
        lines.append("")
        lines.append("    ui.fade_in(fade_time=0.4)")
        lines.append("")

        sketch = self.sketch_text.get("1.0", "end").strip()
        if sketch:
            lines.append("    # User sketch logic inside main loop")

        lines.append("    while True:")
        lines.append("        # Handle button touches")
        lines.append("        for btn in buttons:")
        lines.append("            btn.get_touch(ui)")
        if sketch:
            for line in sketch.splitlines():
                if line.strip():
                    lines.append("        " + line)
        lines.append("        time.sleep(0.05)")
        lines.append("")
        lines.append("")
        lines.append(f"{func}()")

        return "\n".join(lines)

    def save_generated_code(self):
        code = self.generate_micropython_code()
        default_filename = f"{self.app_name.get().replace(' ', '_').lower()}.py" or "app.py"
        f = filedialog.asksaveasfile(
            mode="w",
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            initialfile=default_filename
        )
        if f:
            try:
                f.write(code)
                f.close()
                self.status.config(text=f"Code saved successfully to {f.name}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {e}")

    def upload_to_github(self):
        """
        Generate code and upload to GitHub as:

            APPS/<app_name>.py

        in the configured repo + branch.
        """
        # Build code
        try:
            code = self.generate_micropython_code()
        except Exception as e:
            messagebox.showerror("Code Generation Error", str(e))
            return

        app_name = self.app_name.get().strip() or "MyApp"
        fname = app_name.replace(" ", "_") + ".py"
        repo_path = f"APPS/{fname}"

        if not self.github_token or self.github_token == "YOUR_GITHUB_TOKEN_HERE":
            messagebox.showerror(
                "GitHub Token",
                "GitHub token not configured.\nSet self.github_token in ZenoUIEditor.__init__.",
            )
            return

        if not self.github_repo:
            messagebox.showerror(
                "GitHub Repo",
                "GitHub repo not configured.\nSet self.github_repo in ZenoUIEditor.__init__.",
            )
            return

        url = f"https://api.github.com/repos/{self.github_repo}/contents/{repo_path}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "User-Agent": "Zeno-UI-Editor",
            "Accept": "application/vnd.github+json",
        }

        self.status.config(text=f"Uploading {repo_path} ...")

        def worker():
            try:
                # Check if file exists to get SHA
                sha = None
                exists = False
                try:
                    req = urlrequest.Request(url, headers=headers, method="GET")
                    with urlrequest.urlopen(req) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        sha = data.get("sha")
                        exists = True
                except urlerror.HTTPError as e:
                    if e.code == 404:
                        exists = False
                        sha = None
                    else:
                        self.root.after(0, lambda: [
                            messagebox.showerror(
                                "Upload Error",
                                f"Error checking existing file:\nHTTP {e.code}: {e.reason}",
                            ),
                            self.status.config(text="Upload error (GitHub check).")
                        ])
                        return
                except Exception as e:
                    self.root.after(0, lambda: [
                        messagebox.showerror("Error", f"Error checking existing file:\n{e}"),
                        self.status.config(text="Upload error.")
                    ])
                    return

                commit_message = f"Update {repo_path} from Zeno UI Editor"
                content_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")

                payload = {
                    "message": commit_message,
                    "content": content_b64,
                    "branch": self.github_branch,
                }
                if exists and sha:
                    payload["sha"] = sha

                payload_bytes = json.dumps(payload).encode("utf-8")

                try:
                    req = urlrequest.Request(
                        url,
                        data=payload_bytes,
                        headers={**headers, "Content-Type": "application/json"},
                        method="PUT",
                    )
                    with urlrequest.urlopen(req) as resp:
                        _ = json.loads(resp.read().decode("utf-8"))

                    self.root.after(0, lambda: [
                        self.status.config(text=f"Uploaded to GitHub: {repo_path}"),
                        messagebox.showinfo(
                            "ZenStore Upload",
                            f"Uploaded to {repo_path} in {self.github_repo}",
                        )
                    ])
                except urlerror.HTTPError as e:
                    try:
                        err_body = e.read().decode("utf-8")
                    except Exception:
                        err_body = ""
                    self.root.after(0, lambda: [
                        messagebox.showerror(
                            "Upload Error",
                            f"HTTP {e.code}: {e.reason}\n{err_body}",
                        ),
                        self.status.config(text="Upload error")
                    ])
                except Exception as e:
                    self.root.after(0, lambda: [
                        messagebox.showerror("Upload Error", str(e)),
                        self.status.config(text="Upload error")
                    ])

            except Exception as e:
                self.root.after(0, lambda: [
                    messagebox.showerror("Upload Error", f"Unexpected error: {e}"),
                    self.status.config(text="Upload error")
                ])

        threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()

    # Optional: show Tk callback errors instead of silently killing the app
    def tk_error_handler(exc, val, tb):
        import traceback
        traceback.print_exception(exc, val, tb)
        messagebox.showerror(
            "UI Error",
            f"An internal error occurred:\n{val}"
        )

    root.report_callback_exception = tk_error_handler

    initial_metadata = ask_initial_app_metadata(root)

    if initial_metadata:
        root.deiconify()
        app = ZenoUIEditor(root, initial_metadata)
        root.mainloop()
    else:
        root.destroy()
