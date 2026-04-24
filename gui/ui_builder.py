import tkinter as tk
from tkinter import ttk

from extractor.regions import (
    REGION_TYPES,
    ConstantSpeedMultiplierRegion,
)


class UIBuilder:
    REGION_COLORS = (
        "#11b5e4",
        "#ff6b35",
        "#00a676",
        "#8e6c88",
        "#ff9f1c",
        "#3a86ff",
    )

    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.root = gui_instance.root

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.gui.canvas = tk.Canvas(
            left_frame,
            width=self.gui.canvas_width,
            height=self.gui.canvas_height,
            bg="white",
            bd=2,
            relief=tk.SUNKEN,
        )
        self.gui.canvas.pack(pady=(0, 10))

        legend_frame = ttk.Frame(left_frame)
        legend_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(legend_frame, text="Velocity:", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Label(
            legend_frame,
            text="Spline colors use effective velocity after all active region multipliers.",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.gui.canvas.bind("<Button-1>", self.gui.event_handlers.on_canvas_click)
        self.gui.canvas.bind("<B1-Motion>", self.gui.event_handlers.on_canvas_drag)
        self.gui.canvas.bind(
            "<ButtonRelease-1>", self.gui.event_handlers.on_canvas_release
        )
        self.gui.canvas.bind("<MouseWheel>", self.gui.event_handlers.on_canvas_zoom)

        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X)

        ttk.Button(
            control_frame,
            text="Add Point",
            command=self.gui.event_handlers.add_point_mode,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            control_frame,
            text="Delete Point",
            command=self.gui.point_ops.delete_selected_point,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            control_frame,
            text="Reset View",
            command=self.gui.canvas_renderer.reset_view,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(
            control_frame, text="Save from Spline", command=self.toggle_save_from_spline
        ).pack(side=tk.LEFT, padx=2)
        self.gui.region_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            control_frame,
            text="Region Mode",
            variable=self.gui.region_mode_var,
            command=self.gui.region_ops.toggle_region_mode,
        ).pack(side=tk.LEFT, padx=(12, 2))

        right_frame = ttk.Frame(main_frame, width=420)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        right_scroll_container = ttk.Frame(right_frame)
        right_scroll_container.pack(fill=tk.BOTH, expand=True)

        self.gui.right_panel_canvas = tk.Canvas(
            right_scroll_container,
            highlightthickness=0,
            borderwidth=0,
        )
        self.gui.right_panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_scrollbar = ttk.Scrollbar(
            right_scroll_container,
            orient=tk.VERTICAL,
            command=self.gui.right_panel_canvas.yview,
        )
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.gui.right_panel_canvas.configure(yscrollcommand=right_scrollbar.set)

        right_content = ttk.Frame(self.gui.right_panel_canvas)
        self.gui.right_panel_canvas_window = self.gui.right_panel_canvas.create_window(
            (0, 0),
            window=right_content,
            anchor=tk.NW,
        )

        right_content.bind("<Configure>", self.on_right_panel_configure)
        self.gui.right_panel_canvas.bind(
            "<Configure>", self.on_right_panel_canvas_configure
        )

        for widget in (
            right_frame,
            right_scroll_container,
            self.gui.right_panel_canvas,
            right_content,
        ):
            widget.bind("<Enter>", self.bind_right_panel_mousewheel)
            widget.bind("<Leave>", self.unbind_right_panel_mousewheel)

        file_frame = ttk.LabelFrame(right_content, text="File Operations")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            file_frame, text="Load Raceline", command=self.gui.file_ops.load_raceline
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame, text="Save Raceline", command=self.gui.file_ops.save_raceline
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame,
            text="Save Overtaking CSV",
            command=self.gui.file_ops.save_overtaking_csv,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame, text="Load Map", command=self.gui.file_ops.load_map
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame,
            text="Load Region Metadata",
            command=self.gui.file_ops.load_region_metadata,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame,
            text="Save Region Metadata",
            command=self.gui.file_ops.save_region_metadata,
        ).pack(fill=tk.X, pady=2)

        info_frame = ttk.LabelFrame(right_content, text="Point Information")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.gui.info_text = tk.Text(info_frame, height=8, width=34)
        self.gui.info_text.pack(fill=tk.BOTH, expand=True)

        edit_frame = ttk.LabelFrame(right_content, text="Point Editing")
        edit_frame.pack(fill=tk.X, pady=(0, 10))

        velocity_frame = ttk.Frame(edit_frame)
        velocity_frame.pack(fill=tk.X, pady=2)
        ttk.Label(velocity_frame, text="Base Velocity:").pack(side=tk.LEFT)
        self.gui.velocity_var = tk.DoubleVar(value=1.0)
        self.gui.velocity_entry = ttk.Entry(
            velocity_frame, textvariable=self.gui.velocity_var, width=10
        )
        self.gui.velocity_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.gui.velocity_entry.bind(
            "<Return>", self.gui.point_ops.update_selected_point_velocity
        )
        self.gui.velocity_entry.bind(
            "<FocusOut>", self.gui.point_ops.update_selected_point_velocity
        )
        ttk.Button(
            velocity_frame,
            text="Apply",
            command=self.gui.point_ops.update_selected_point_velocity,
        ).pack(side=tk.LEFT, padx=2)

        quick_vel_frame = ttk.Frame(edit_frame)
        quick_vel_frame.pack(fill=tk.X, pady=2)
        ttk.Label(quick_vel_frame, text="Quick:").pack(side=tk.LEFT)
        for vel in [0.5, 1.0, 1.5, 2.0, 3.0]:
            ttk.Button(
                quick_vel_frame,
                text=f"{vel}",
                width=4,
                command=lambda value=vel: self.gui.point_ops.set_quick_velocity(value),
            ).pack(side=tk.LEFT, padx=1)

        coord_frame = ttk.Frame(edit_frame)
        coord_frame.pack(fill=tk.X, pady=2)
        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, sticky=tk.W)
        self.gui.x_var = tk.DoubleVar(value=0.0)
        self.gui.x_entry = ttk.Entry(coord_frame, textvariable=self.gui.x_var, width=12)
        self.gui.x_entry.grid(row=0, column=1, padx=(5, 5))
        self.gui.x_entry.bind(
            "<Return>", self.gui.point_ops.update_selected_point_coords
        )
        self.gui.x_entry.bind(
            "<FocusOut>", self.gui.point_ops.update_selected_point_coords
        )

        ttk.Label(coord_frame, text="Y:").grid(row=1, column=0, sticky=tk.W)
        self.gui.y_var = tk.DoubleVar(value=0.0)
        self.gui.y_entry = ttk.Entry(coord_frame, textvariable=self.gui.y_var, width=12)
        self.gui.y_entry.grid(row=1, column=1, padx=(5, 5))
        self.gui.y_entry.bind(
            "<Return>", self.gui.point_ops.update_selected_point_coords
        )
        self.gui.y_entry.bind(
            "<FocusOut>", self.gui.point_ops.update_selected_point_coords
        )

        ttk.Button(
            coord_frame,
            text="Update Coords",
            command=self.gui.point_ops.update_selected_point_coords,
        ).grid(row=0, column=2, rowspan=2, padx=5)

        self.gui.velocity_entry.config(state="disabled")
        self.gui.x_entry.config(state="disabled")
        self.gui.y_entry.config(state="disabled")

        region_frame = ttk.LabelFrame(right_content, text="Regions")
        region_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.gui.region_selection_var = tk.StringVar(value="Selection: -")
        ttk.Label(region_frame, textvariable=self.gui.region_selection_var).pack(
            fill=tk.X, pady=(0, 4)
        )

        self.gui.metadata_status_var = tk.StringVar(value="Metadata: none")
        ttk.Label(region_frame, textvariable=self.gui.metadata_status_var).pack(
            fill=tk.X, pady=(0, 6)
        )

        region_form = ttk.Frame(region_frame)
        region_form.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(region_form, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.gui.region_name_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.gui.region_name_var).grid(
            row=0, column=1, columnspan=3, sticky=tk.EW, padx=(5, 0)
        )

        ttk.Label(region_form, text="Type:").grid(
            row=1, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.gui.region_type_var = tk.StringVar(
            value=ConstantSpeedMultiplierRegion.REGION_TYPE
        )
        self.gui.region_type_combo = ttk.Combobox(
            region_form,
            textvariable=self.gui.region_type_var,
            values=list(REGION_TYPES.keys()),
            state="readonly",
        )
        self.gui.region_type_combo.grid(
            row=1, column=1, columnspan=3, sticky=tk.EW, padx=(5, 0), pady=(4, 0)
        )
        self.gui.region_type_combo.bind(
            "<<ComboboxSelected>>", self.update_region_type_controls
        )

        ttk.Label(region_form, text="Start:").grid(
            row=2, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.gui.region_start_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.gui.region_start_var, width=8).grid(
            row=2, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
        )

        ttk.Label(region_form, text="End:").grid(
            row=2, column=2, sticky=tk.W, pady=(4, 0)
        )
        self.gui.region_end_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.gui.region_end_var, width=8).grid(
            row=2, column=3, sticky=tk.W, pady=(4, 0)
        )

        self.gui.region_value_label = ttk.Label(region_form, text="Multiplier:")
        self.gui.region_value_label.grid(row=3, column=0, sticky=tk.W, pady=(4, 0))
        self.gui.region_multiplier_var = tk.StringVar(value="1.0")
        self.gui.region_multiplier_entry = ttk.Entry(
            region_form, textvariable=self.gui.region_multiplier_var, width=8
        )
        self.gui.region_multiplier_entry.grid(
            row=3, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
        )
        self.gui.region_true_value_label = ttk.Label(region_form, text="True")
        region_form.columnconfigure(1, weight=1)
        region_form.columnconfigure(3, weight=1)

        region_button_row = ttk.Frame(region_frame)
        region_button_row.pack(fill=tk.X, pady=(0, 8))
        self.gui.region_save_button = ttk.Button(
            region_button_row,
            text="Create Region",
            command=self.gui.region_ops.save_region_from_form,
        )
        self.gui.region_save_button.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            region_button_row,
            text="New",
            command=self.gui.region_ops.prepare_new_region,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            region_button_row,
            text="Delete",
            command=self.gui.region_ops.delete_selected_region,
        ).pack(side=tk.LEFT, padx=4)

        self.gui.region_listbox = tk.Listbox(
            region_frame, height=10, exportselection=False
        )
        self.gui.region_listbox.pack(fill=tk.BOTH, expand=True)
        self.gui.region_listbox.bind(
            "<<ListboxSelect>>", self.gui.event_handlers.on_region_list_select
        )
        self.update_region_type_controls()

        spline_frame = ttk.LabelFrame(right_content, text="Spline Settings")
        spline_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(spline_frame, text="Smoothness:").pack()
        self.gui.smoothness_var = tk.DoubleVar(value=0.1)
        smoothness_scale = ttk.Scale(
            spline_frame,
            from_=0.01,
            to=1.0,
            variable=self.gui.smoothness_var,
            orient=tk.HORIZONTAL,
        )
        smoothness_scale.pack(fill=tk.X, pady=2)
        smoothness_scale.bind(
            "<ButtonRelease-1>", self.gui.spline_ops.force_spline_update
        )
        smoothness_scale.bind("<Motion>", self.gui.spline_ops.force_spline_update)

        ttk.Label(spline_frame, text="Resolution:").pack()
        self.gui.resolution_var = tk.IntVar(value=100)
        resolution_scale = ttk.Scale(
            spline_frame,
            from_=50,
            to=500,
            variable=self.gui.resolution_var,
            orient=tk.HORIZONTAL,
        )
        resolution_scale.pack(fill=tk.X, pady=2)
        resolution_scale.bind(
            "<ButtonRelease-1>", self.gui.spline_ops.force_spline_update
        )
        resolution_scale.bind("<Motion>", self.gui.spline_ops.force_spline_update)

        self.gui.status_var = tk.StringVar(value="Ready")
        ttk.Label(right_frame, textvariable=self.gui.status_var, relief=tk.SUNKEN).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self.root.bind(
            "<Delete>", lambda event: self.gui.point_ops.delete_selected_point()
        )
        self.root.bind("<Control-s>", lambda event: self.gui.file_ops.save_raceline())
        self.root.bind("<Control-o>", lambda event: self.gui.file_ops.load_raceline())
        self.root.focus_set()

    def on_right_panel_configure(self, event):
        self.gui.right_panel_canvas.configure(
            scrollregion=self.gui.right_panel_canvas.bbox("all")
        )

    def on_right_panel_canvas_configure(self, event):
        self.gui.right_panel_canvas.itemconfigure(
            self.gui.right_panel_canvas_window,
            width=event.width,
        )

    def bind_right_panel_mousewheel(self, event=None):
        self.gui.right_panel_canvas.bind_all(
            "<MouseWheel>", self.on_right_panel_mousewheel
        )

    def unbind_right_panel_mousewheel(self, event=None):
        self.gui.right_panel_canvas.unbind_all("<MouseWheel>")

    def on_right_panel_mousewheel(self, event):
        if event.delta:
            self.gui.right_panel_canvas.yview_scroll(int(-event.delta / 120), "units")

    def toggle_save_from_spline(self):
        self.gui.save_from_spline = not self.gui.save_from_spline
        state = "enabled" if self.gui.save_from_spline else "disabled"
        self.gui.status_var.set(f"Save from spline {state}")

    def update_region_type_controls(self, event=None):
        is_speed_region = (
            self.gui.region_ops.current_region_type()
            == ConstantSpeedMultiplierRegion.REGION_TYPE
        )
        self.gui.region_value_label.config(
            text="Multiplier:" if is_speed_region else "Can Overtake:"
        )

        if is_speed_region:
            self.gui.region_true_value_label.grid_remove()
            self.gui.region_multiplier_entry.grid(
                row=3, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
            )
            if not self.gui.region_multiplier_var.get().strip():
                self.gui.region_multiplier_var.set("1.0")
        else:
            self.gui.region_multiplier_entry.grid_remove()
            self.gui.region_true_value_label.grid(
                row=3, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
            )
