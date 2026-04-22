import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from config import DrawerConfig
from extractor import (
    Region,
    apply_regions_to_points,
    default_metadata_path,
    find_metadata_path_for_raceline,
    load_map_from_yaml,
    load_raceline_from_csv,
    load_regions_from_json,
    region_multiplier_for_index,
    remove_regions_from_points,
    save_raceline_to_csv,
    save_regions_to_json,
)
from spline import generate_spline, velocity_to_color


class RacelineEditorGUI:
    REGION_COLORS = (
        "#11b5e4",
        "#ff6b35",
        "#00a676",
        "#8e6c88",
        "#ff9f1c",
        "#3a86ff",
    )

    def __init__(self, root):
        self.root = root
        self.root.title("F1Tenth Raceline Editor")
        self.root.geometry("1450x920")

        self.raceline_points = []
        self.regions = []
        self.map_image = None
        self.map_metadata = None
        self.current_file = None
        self.current_metadata_file = None
        self.selected_point_idx = None
        self.selected_region_idx = None
        self.spline_points = []
        self.min_velocity = 0.5
        self.max_velocity = 5.0

        self.canvas_width = 860
        self.canvas_height = 620
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.save_from_spline = False
        self.dragging_point = False
        self.region_mode = False
        self.region_drag_start_idx = None
        self.region_preview_range = None

        self.setup_ui()
        self.load_default_data()
        self.root.after(100, self.initialize_spline)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            left_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            bd=2,
            relief=tk.SUNKEN,
        )
        self.canvas.pack(pady=(0, 10))

        legend_frame = ttk.Frame(left_frame)
        legend_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(legend_frame, text="Velocity:", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Label(
            legend_frame,
            text="Spline colors use effective velocity after all active region multipliers.",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_canvas_zoom)

        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X)

        ttk.Button(control_frame, text="Add Point", command=self.add_point_mode).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            control_frame, text="Delete Point", command=self.delete_selected_point
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Reset View", command=self.reset_view).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Checkbutton(
            control_frame, text="Save from Spline", command=self.toggle_save_from_spline
        ).pack(side=tk.LEFT, padx=2)
        self.region_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            control_frame,
            text="Region Mode",
            variable=self.region_mode_var,
            command=self.toggle_region_mode,
        ).pack(side=tk.LEFT, padx=(12, 2))

        right_frame = ttk.Frame(main_frame, width=420)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        right_scroll_container = ttk.Frame(right_frame)
        right_scroll_container.pack(fill=tk.BOTH, expand=True)

        self.right_panel_canvas = tk.Canvas(
            right_scroll_container,
            highlightthickness=0,
            borderwidth=0,
        )
        self.right_panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_scrollbar = ttk.Scrollbar(
            right_scroll_container,
            orient=tk.VERTICAL,
            command=self.right_panel_canvas.yview,
        )
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel_canvas.configure(yscrollcommand=right_scrollbar.set)

        right_content = ttk.Frame(self.right_panel_canvas)
        self.right_panel_canvas_window = self.right_panel_canvas.create_window(
            (0, 0),
            window=right_content,
            anchor=tk.NW,
        )

        right_content.bind("<Configure>", self.on_right_panel_configure)
        self.right_panel_canvas.bind("<Configure>", self.on_right_panel_canvas_configure)

        for widget in (right_frame, right_scroll_container, self.right_panel_canvas, right_content):
            widget.bind("<Enter>", self.bind_right_panel_mousewheel)
            widget.bind("<Leave>", self.unbind_right_panel_mousewheel)

        file_frame = ttk.LabelFrame(right_content, text="File Operations")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(file_frame, text="Load Raceline", command=self.load_raceline).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(file_frame, text="Save Raceline", command=self.save_raceline).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(file_frame, text="Load Map", command=self.load_map).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(
            file_frame, text="Load Region Metadata", command=self.load_region_metadata
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            file_frame, text="Save Region Metadata", command=self.save_region_metadata
        ).pack(fill=tk.X, pady=2)

        info_frame = ttk.LabelFrame(right_content, text="Point Information")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_text = tk.Text(info_frame, height=8, width=34)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        edit_frame = ttk.LabelFrame(right_content, text="Point Editing")
        edit_frame.pack(fill=tk.X, pady=(0, 10))

        velocity_frame = ttk.Frame(edit_frame)
        velocity_frame.pack(fill=tk.X, pady=2)
        ttk.Label(velocity_frame, text="Base Velocity:").pack(side=tk.LEFT)
        self.velocity_var = tk.DoubleVar(value=1.0)
        self.velocity_entry = ttk.Entry(
            velocity_frame, textvariable=self.velocity_var, width=10
        )
        self.velocity_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.velocity_entry.bind("<Return>", self.update_selected_point_velocity)
        self.velocity_entry.bind("<FocusOut>", self.update_selected_point_velocity)
        ttk.Button(
            velocity_frame, text="Apply", command=self.update_selected_point_velocity
        ).pack(side=tk.LEFT, padx=2)

        quick_vel_frame = ttk.Frame(edit_frame)
        quick_vel_frame.pack(fill=tk.X, pady=2)
        ttk.Label(quick_vel_frame, text="Quick:").pack(side=tk.LEFT)
        for vel in [0.5, 1.0, 1.5, 2.0, 3.0]:
            ttk.Button(
                quick_vel_frame,
                text=f"{vel}",
                width=4,
                command=lambda value=vel: self.set_quick_velocity(value),
            ).pack(side=tk.LEFT, padx=1)

        coord_frame = ttk.Frame(edit_frame)
        coord_frame.pack(fill=tk.X, pady=2)
        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, sticky=tk.W)
        self.x_var = tk.DoubleVar(value=0.0)
        self.x_entry = ttk.Entry(coord_frame, textvariable=self.x_var, width=12)
        self.x_entry.grid(row=0, column=1, padx=(5, 5))
        self.x_entry.bind("<Return>", self.update_selected_point_coords)
        self.x_entry.bind("<FocusOut>", self.update_selected_point_coords)

        ttk.Label(coord_frame, text="Y:").grid(row=1, column=0, sticky=tk.W)
        self.y_var = tk.DoubleVar(value=0.0)
        self.y_entry = ttk.Entry(coord_frame, textvariable=self.y_var, width=12)
        self.y_entry.grid(row=1, column=1, padx=(5, 5))
        self.y_entry.bind("<Return>", self.update_selected_point_coords)
        self.y_entry.bind("<FocusOut>", self.update_selected_point_coords)

        ttk.Button(
            coord_frame, text="Update Coords", command=self.update_selected_point_coords
        ).grid(row=0, column=2, rowspan=2, padx=5)

        self.velocity_entry.config(state="disabled")
        self.x_entry.config(state="disabled")
        self.y_entry.config(state="disabled")

        region_frame = ttk.LabelFrame(right_content, text="Regions")
        region_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.region_selection_var = tk.StringVar(value="Selection: -")
        ttk.Label(region_frame, textvariable=self.region_selection_var).pack(
            fill=tk.X, pady=(0, 4)
        )

        self.metadata_status_var = tk.StringVar(value="Metadata: none")
        ttk.Label(region_frame, textvariable=self.metadata_status_var).pack(
            fill=tk.X, pady=(0, 6)
        )

        region_form = ttk.Frame(region_frame)
        region_form.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(region_form, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.region_name_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.region_name_var).grid(
            row=0, column=1, columnspan=3, sticky=tk.EW, padx=(5, 0)
        )

        ttk.Label(region_form, text="Start:").grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        self.region_start_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.region_start_var, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
        )

        ttk.Label(region_form, text="End:").grid(row=1, column=2, sticky=tk.W, pady=(4, 0))
        self.region_end_var = tk.StringVar()
        ttk.Entry(region_form, textvariable=self.region_end_var, width=8).grid(
            row=1, column=3, sticky=tk.W, pady=(4, 0)
        )

        ttk.Label(region_form, text="Multiplier:").grid(
            row=2, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.region_multiplier_var = tk.StringVar(value="1.0")
        ttk.Entry(region_form, textvariable=self.region_multiplier_var, width=8).grid(
            row=2, column=1, sticky=tk.W, padx=(5, 10), pady=(4, 0)
        )
        region_form.columnconfigure(1, weight=1)
        region_form.columnconfigure(3, weight=1)

        region_button_row = ttk.Frame(region_frame)
        region_button_row.pack(fill=tk.X, pady=(0, 8))
        self.region_save_button = ttk.Button(
            region_button_row, text="Create Region", command=self.save_region_from_form
        )
        self.region_save_button.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(region_button_row, text="New", command=self.prepare_new_region).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(
            region_button_row, text="Delete", command=self.delete_selected_region
        ).pack(side=tk.LEFT, padx=4)

        self.region_listbox = tk.Listbox(region_frame, height=10, exportselection=False)
        self.region_listbox.pack(fill=tk.BOTH, expand=True)
        self.region_listbox.bind("<<ListboxSelect>>", self.on_region_list_select)

        spline_frame = ttk.LabelFrame(right_content, text="Spline Settings")
        spline_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(spline_frame, text="Smoothness:").pack()
        self.smoothness_var = tk.DoubleVar(value=0.1)
        smoothness_scale = ttk.Scale(
            spline_frame,
            from_=0.01,
            to=1.0,
            variable=self.smoothness_var,
            orient=tk.HORIZONTAL,
        )
        smoothness_scale.pack(fill=tk.X, pady=2)
        smoothness_scale.bind("<ButtonRelease-1>", self.force_spline_update)
        smoothness_scale.bind("<Motion>", self.force_spline_update)

        ttk.Label(spline_frame, text="Resolution:").pack()
        self.resolution_var = tk.IntVar(value=100)
        resolution_scale = ttk.Scale(
            spline_frame,
            from_=50,
            to=500,
            variable=self.resolution_var,
            orient=tk.HORIZONTAL,
        )
        resolution_scale.pack(fill=tk.X, pady=2)
        resolution_scale.bind("<ButtonRelease-1>", self.force_spline_update)
        resolution_scale.bind("<Motion>", self.force_spline_update)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self.root.bind("<Delete>", lambda event: self.delete_selected_point())
        self.root.bind("<Control-s>", lambda event: self.save_raceline())
        self.root.bind("<Control-o>", lambda event: self.load_raceline())
        self.root.focus_set()

    def on_right_panel_configure(self, event):
        self.right_panel_canvas.configure(scrollregion=self.right_panel_canvas.bbox("all"))

    def on_right_panel_canvas_configure(self, event):
        self.right_panel_canvas.itemconfigure(
            self.right_panel_canvas_window,
            width=event.width,
        )

    def bind_right_panel_mousewheel(self, event=None):
        self.right_panel_canvas.bind_all("<MouseWheel>", self.on_right_panel_mousewheel)

    def unbind_right_panel_mousewheel(self, event=None):
        self.right_panel_canvas.unbind_all("<MouseWheel>")

    def on_right_panel_mousewheel(self, event):
        if event.delta:
            self.right_panel_canvas.yview_scroll(int(-event.delta / 120), "units")

    def toggle_save_from_spline(self):
        self.save_from_spline = not self.save_from_spline
        state = "enabled" if self.save_from_spline else "disabled"
        self.status_var.set(f"Save from spline {state}")

    def load_default_data(self):
        try:
            map_yaml_path = DrawerConfig.MAP_YAML.value
            if os.path.exists(map_yaml_path):
                self.map_image, self.map_metadata = load_map_from_yaml(map_yaml_path)

            raceline_path = DrawerConfig.RACING_CSV.value
            if os.path.exists(raceline_path):
                self.load_raceline_file(raceline_path, show_status=False)

            if self.map_image is not None:
                self.reset_view()
            else:
                self.update_display()
        except Exception as e:
            self.status_var.set(f"Error loading default data: {str(e)}")

    def initialize_spline(self):
        if len(self.raceline_points) >= 2:
            try:
                self.update_spline()
                self.status_var.set(
                    f"Ready - {len(self.raceline_points)} points loaded"
                )
            except Exception as e:
                self.status_var.set(f"Ready - spline init failed: {str(e)}")

    def load_map(self):
        file_path = filedialog.askopenfilename(
            title="Load Map YAML",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
        )

        if file_path:
            try:
                self.map_image, self.map_metadata = load_map_from_yaml(file_path)
                self.reset_view()
                self.status_var.set("Map loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load map: {str(e)}")

    def load_raceline(self):
        file_path = filedialog.askopenfilename(
            title="Load Raceline",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if file_path:
            try:
                self.load_raceline_file(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load raceline: {str(e)}")

    def load_raceline_file(self, file_path, show_status=True):
        self.raceline_points = load_raceline_from_csv(file_path)
        self.current_file = file_path
        self.current_metadata_file = None
        self.selected_point_idx = None
        self.selected_region_idx = None
        self.dragging_point = False
        self.region_drag_start_idx = None
        self.region_preview_range = None
        self.regions = []

        metadata_path = find_metadata_path_for_raceline(file_path)
        if metadata_path:
            self.load_region_metadata_from_file(metadata_path, normalize_loaded_points=True)
        else:
            self.refresh_region_ui()

        self.refresh_velocity_bounds()
        self.update_display()
        self.update_info_display()

        if show_status:
            metadata_suffix = (
                f" with metadata {os.path.basename(self.current_metadata_file)}"
                if self.current_metadata_file
                else ""
            )
            self.status_var.set(
                f"Loaded {len(self.raceline_points)} points{metadata_suffix}"
            )

    def load_region_metadata(self):
        if not self.raceline_points:
            messagebox.showwarning("Warning", "Load a raceline before loading metadata")
            return

        file_path = filedialog.askopenfilename(
            title="Load Region Metadata",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if file_path:
            try:
                normalize_loaded_points = self.current_metadata_file is None
                self.load_region_metadata_from_file(
                    file_path, normalize_loaded_points=normalize_loaded_points
                )
                self.status_var.set(
                    f"Loaded {len(self.regions)} regions from {os.path.basename(file_path)}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load metadata: {str(e)}")

    def load_region_metadata_from_file(self, file_path, normalize_loaded_points=False):
        payload = load_regions_from_json(file_path)
        regions = payload["regions"]

        if normalize_loaded_points and payload["velocities_applied"]:
            self.raceline_points = remove_regions_from_points(self.raceline_points, regions)

        self.regions = regions
        self.current_metadata_file = file_path
        self.selected_region_idx = None
        self.region_preview_range = None
        self.refresh_region_ui()
        self.refresh_velocity_bounds()
        self.update_display()
        self.update_info_display()

    def save_region_metadata(self):
        if not self.raceline_points:
            messagebox.showwarning("Warning", "No raceline loaded")
            return

        file_path = self.prompt_metadata_save_path()
        if not file_path:
            return

        try:
            save_regions_to_json(file_path, self.regions, velocities_applied=True)
            self.current_metadata_file = file_path
            self.refresh_region_ui()
            self.status_var.set(f"Saved metadata to {file_path}")
            messagebox.showinfo("Success", "Region metadata saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {str(e)}")

    def prompt_metadata_save_path(self, raceline_path=None):
        base_raceline_path = raceline_path or self.current_file
        initial_path = self.current_metadata_file
        if not initial_path and base_raceline_path:
            initial_path = default_metadata_path(base_raceline_path)

        initial_dir = os.getcwd()
        initial_file = "regions.json"
        if initial_path:
            initial_dir = os.path.dirname(initial_path) or initial_dir
            initial_file = os.path.basename(initial_path)

        return filedialog.asksaveasfilename(
            title="Save Region Metadata",
            defaultextension=".json",
            initialdir=initial_dir,
            initialfile=initial_file,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

    def world_to_canvas_coords(self, x, y):
        if not self.map_metadata:
            return x, y

        resolution = self.map_metadata["resolution"]
        origin = self.map_metadata["origin"]
        pixel_x = (x - origin[0]) / resolution
        pixel_y = self.map_image.shape[0] - (y - origin[1]) / resolution

        canvas_x = pixel_x * self.scale_factor + self.offset_x
        canvas_y = pixel_y * self.scale_factor + self.offset_y
        return canvas_x, canvas_y

    def canvas_to_world_coords(self, canvas_x, canvas_y):
        if not self.map_metadata:
            return canvas_x, canvas_y

        resolution = self.map_metadata["resolution"]
        origin = self.map_metadata["origin"]
        pixel_x = (canvas_x - self.offset_x) / self.scale_factor
        pixel_y = (canvas_y - self.offset_y) / self.scale_factor

        world_x = pixel_x * resolution + origin[0]
        world_y = (self.map_image.shape[0] - pixel_y) * resolution + origin[1]
        return world_x, world_y

    def update_display(self):
        self.canvas.delete("all")

        if self.map_image is not None:
            self.draw_map()

        if self.raceline_points:
            self.draw_raceline()
            self.update_spline()

    def draw_map(self):
        height, width = self.map_image.shape[:2]
        scaled_width = int(width * self.scale_factor)
        scaled_height = int(height * self.scale_factor)
        resized_image = cv2.resize(self.map_image, (scaled_width, scaled_height))
        pil_image = Image.fromarray(resized_image)
        self.photo = ImageTk.PhotoImage(pil_image)
        self.canvas.create_image(
            self.offset_x, self.offset_y, anchor=tk.NW, image=self.photo
        )

    def draw_raceline(self):
        if len(self.raceline_points) < 2:
            return

        for index in range(len(self.raceline_points)):
            current_point = self.raceline_points[index]
            next_point = self.raceline_points[(index + 1) % len(self.raceline_points)]
            x1, y1 = self.world_to_canvas_coords(current_point[0], current_point[1])
            x2, y2 = self.world_to_canvas_coords(next_point[0], next_point[1])
            self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2, tags="raceline")

        self.draw_regions()
        self.draw_region_preview()

        for index, point in enumerate(self.raceline_points):
            x, y = self.world_to_canvas_coords(point[0], point[1])
            color = self.point_fill_color(index)
            size = 8 if index == self.selected_point_idx else 6
            self.canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=color,
                outline="black",
                width=2,
                tags=f"point_{index}",
            )

            if index == self.selected_point_idx or (index % 5 == 0 and self.scale_factor > 0.5):
                effective_velocity = self.get_effective_velocity(index)
                text_color = "black" if index == self.selected_point_idx else "gray"
                self.canvas.create_text(
                    x + 12,
                    y - 12,
                    text=f"v:{effective_velocity:.2f}",
                    fill=text_color,
                    font=("Arial", 8),
                    tags="velocity_label",
                )

    def draw_regions(self):
        for region_index, region in enumerate(self.regions):
            color = self.region_color(region_index)
            width = 6 if region_index == self.selected_region_idx else 4
            dash = None if region_index == self.selected_region_idx else (6, 4)

            for point_index in range(region.start_index, region.end_index):
                point_a = self.raceline_points[point_index]
                point_b = self.raceline_points[point_index + 1]
                x1, y1 = self.world_to_canvas_coords(point_a[0], point_a[1])
                x2, y2 = self.world_to_canvas_coords(point_b[0], point_b[1])
                self.canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    width=width,
                    dash=dash,
                    tags="region",
                )

            start_x, start_y = self.world_to_canvas_coords(
                self.raceline_points[region.start_index][0],
                self.raceline_points[region.start_index][1],
            )
            end_x, end_y = self.world_to_canvas_coords(
                self.raceline_points[region.end_index][0],
                self.raceline_points[region.end_index][1],
            )
            self.canvas.create_oval(
                start_x - 10,
                start_y - 10,
                start_x + 10,
                start_y + 10,
                outline=color,
                width=3,
                tags="region",
            )
            self.canvas.create_rectangle(
                end_x - 8,
                end_y - 8,
                end_x + 8,
                end_y + 8,
                outline=color,
                width=3,
                tags="region",
            )

            label_index = (region.start_index + region.end_index) // 2
            label_point = self.raceline_points[label_index]
            label_x, label_y = self.world_to_canvas_coords(label_point[0], label_point[1])
            region_name = region.name or f"Zone {region_index + 1}"
            self.canvas.create_text(
                label_x + 18,
                label_y + 16,
                text=f"{region_name} x{region.multiplier:.2f}",
                fill=color,
                font=("Arial", 9, "bold"),
                anchor=tk.W,
                tags="region",
            )

    def draw_region_preview(self):
        if not self.region_preview_range:
            return

        start_index, end_index = self.region_preview_range
        preview_color = "#00c2ff"

        for point_index in range(start_index, end_index):
            point_a = self.raceline_points[point_index]
            point_b = self.raceline_points[point_index + 1]
            x1, y1 = self.world_to_canvas_coords(point_a[0], point_a[1])
            x2, y2 = self.world_to_canvas_coords(point_b[0], point_b[1])
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=preview_color,
                width=5,
                dash=(3, 3),
                tags="region_preview",
            )

        for boundary_index in {start_index, end_index}:
            point = self.raceline_points[boundary_index]
            x, y = self.world_to_canvas_coords(point[0], point[1])
            self.canvas.create_oval(
                x - 10,
                y - 10,
                x + 10,
                y + 10,
                outline=preview_color,
                width=3,
                tags="region_preview",
            )

    def point_fill_color(self, point_index):
        if point_index == self.selected_point_idx:
            return "yellow"
        if self.region_preview_range and self.region_preview_range[0] <= point_index <= self.region_preview_range[1]:
            return "#00c2ff"
        region_index = self.last_region_covering_point(point_index)
        if region_index is not None:
            return self.region_color(region_index)
        return "blue"

    def last_region_covering_point(self, point_index):
        for region_index in range(len(self.regions) - 1, -1, -1):
            region = self.regions[region_index]
            if region.start_index <= point_index <= region.end_index:
                return region_index
        return None

    def region_color(self, region_index):
        return self.REGION_COLORS[region_index % len(self.REGION_COLORS)]

    def get_effective_velocity(self, point_index):
        point = self.raceline_points[point_index]
        return point[2] * region_multiplier_for_index(point_index, self.regions)

    def get_effective_raceline_points(self):
        return apply_regions_to_points(self.raceline_points, self.regions)

    def refresh_velocity_bounds(self):
        if not self.raceline_points:
            self.min_velocity = 0.5
            self.max_velocity = 5.0
            return

        effective_points = self.get_effective_raceline_points()
        velocities = [point[2] for point in effective_points]
        self.min_velocity = min(velocities)
        self.max_velocity = max(velocities)
        if self.min_velocity == self.max_velocity:
            self.max_velocity = self.min_velocity + 1.0

    def update_spline(self, event=None):
        self.canvas.delete("spline")

        effective_points = self.get_effective_raceline_points()
        if len(effective_points) < 3:
            self.spline_points = []
            return

        try:
            smoothness = max(0.0, self.smoothness_var.get())
            resolution = max(50, int(self.resolution_var.get()))
            self.spline_points = generate_spline(effective_points, smoothness, resolution)

            if self.spline_points is None:
                self.spline_points = []
                self.draw_simple_spline_fallback(effective_points)
                return

            self.draw_spline()
        except Exception as e:
            self.spline_points = []
            self.status_var.set(f"Spline error - using simple curve: {str(e)}")
            self.draw_simple_spline_fallback(effective_points)

    def draw_spline(self):
        for index in range(len(self.spline_points) - 1):
            x1, y1 = self.world_to_canvas_coords(
                self.spline_points[index][0], self.spline_points[index][1]
            )
            x2, y2 = self.world_to_canvas_coords(
                self.spline_points[index + 1][0], self.spline_points[index + 1][1]
            )
            avg_velocity = (self.spline_points[index][2] + self.spline_points[index + 1][2]) / 2
            color = velocity_to_color(avg_velocity, self.min_velocity, self.max_velocity)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                width=3,
                tags="spline",
                smooth=True,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

    def draw_simple_spline_fallback(self, points):
        if len(points) < 2:
            return

        for index in range(len(points)):
            current_point = points[index]
            next_point = points[(index + 1) % len(points)]
            x1, y1 = self.world_to_canvas_coords(current_point[0], current_point[1])
            x2, y2 = self.world_to_canvas_coords(next_point[0], next_point[1])
            avg_velocity = (current_point[2] + next_point[2]) / 2
            color = velocity_to_color(avg_velocity, self.min_velocity, self.max_velocity)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                width=3,
                tags="spline",
                smooth=True,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

    def force_spline_update(self, event=None):
        if len(self.raceline_points) >= 2:
            self.root.after_idle(self.update_display)

    def find_nearest_point_index(self, canvas_x, canvas_y, threshold=15):
        min_distance = float("inf")
        nearest_index = None

        for index, point in enumerate(self.raceline_points):
            x, y = self.world_to_canvas_coords(point[0], point[1])
            distance = ((canvas_x - x) ** 2 + (canvas_y - y) ** 2) ** 0.5
            if distance < min_distance and distance < threshold:
                min_distance = distance
                nearest_index = index

        return nearest_index

    def on_canvas_click(self, event):
        if self.region_mode:
            self.start_region_selection(event)
            return

        nearest_index = self.find_nearest_point_index(event.x, event.y)
        self.selected_point_idx = nearest_index
        self.dragging_point = nearest_index is not None
        self.update_display()
        self.update_info_display()

    def on_canvas_drag(self, event):
        if self.region_mode:
            self.update_region_selection(event)
            return

        if self.selected_point_idx is not None and self.dragging_point:
            world_x, world_y = self.canvas_to_world_coords(event.x, event.y)
            self.raceline_points[self.selected_point_idx][0] = world_x
            self.raceline_points[self.selected_point_idx][1] = world_y
            self.update_display()
            self.update_info_display()

    def on_canvas_release(self, event):
        if self.region_mode:
            self.finish_region_selection(event)
            return
        self.dragging_point = False

    def start_region_selection(self, event):
        nearest_index = self.find_nearest_point_index(event.x, event.y)
        if nearest_index is None:
            self.region_drag_start_idx = None
            self.region_preview_range = None
            self.region_selection_var.set("Selection: -")
            self.update_display()
            return

        self.region_drag_start_idx = nearest_index
        self.region_preview_range = (nearest_index, nearest_index)
        self.region_selection_var.set(f"Selection: {nearest_index} - {nearest_index}")
        self.update_display()

    def update_region_selection(self, event):
        if self.region_drag_start_idx is None:
            return

        nearest_index = self.find_nearest_point_index(event.x, event.y, threshold=25)
        if nearest_index is None:
            return

        start_index = min(self.region_drag_start_idx, nearest_index)
        end_index = max(self.region_drag_start_idx, nearest_index)
        self.region_preview_range = (start_index, end_index)
        self.region_selection_var.set(f"Selection: {start_index} - {end_index}")
        self.update_display()

    def finish_region_selection(self, event):
        if self.region_drag_start_idx is None:
            return

        nearest_index = self.find_nearest_point_index(event.x, event.y, threshold=25)
        if nearest_index is None:
            nearest_index = self.region_drag_start_idx

        start_index = min(self.region_drag_start_idx, nearest_index)
        end_index = max(self.region_drag_start_idx, nearest_index)
        self.region_preview_range = (start_index, end_index)
        self.region_start_var.set(str(start_index))
        self.region_end_var.set(str(end_index))
        if not self.region_name_var.get().strip():
            self.region_name_var.set(self.next_region_name())

        self.region_selection_var.set(f"Selection: {start_index} - {end_index}")
        self.region_drag_start_idx = None
        self.update_display()

    def on_canvas_zoom(self, event):
        if event.delta > 0:
            self.scale_factor *= 1.1
        else:
            self.scale_factor /= 1.1

        self.scale_factor = max(0.1, min(5.0, self.scale_factor))
        self.update_display()

    def reset_view(self):
        if self.map_image is not None:
            height, width = self.map_image.shape[:2]
            scale_x = self.canvas_width / width
            scale_y = self.canvas_height / height
            self.scale_factor = min(scale_x, scale_y) * 0.9
            self.offset_x = (self.canvas_width - width * self.scale_factor) // 2
            self.offset_y = (self.canvas_height - height * self.scale_factor) // 2

        self.update_display()

    def add_point_mode(self):
        self.set_region_mode(False)
        self.status_var.set("Click on the canvas to add a new point")
        self.canvas.bind("<Button-1>", self.add_point_click)

    def add_point_click(self, event):
        world_x, world_y = self.canvas_to_world_coords(event.x, event.y)
        new_point = [world_x, world_y, 1.0]

        if self.selected_point_idx is not None:
            insert_index = self.selected_point_idx + 1
            self.raceline_points.insert(insert_index, new_point)
            self.shift_regions_for_insert(insert_index)
            self.selected_point_idx = insert_index
        else:
            insert_index = len(self.raceline_points)
            self.raceline_points.append(new_point)
            self.selected_point_idx = insert_index

        self.refresh_velocity_bounds()
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.update_display()
        self.update_info_display()
        self.status_var.set("Point added")

    def delete_selected_point(self):
        if self.selected_point_idx is None or len(self.raceline_points) <= 3:
            self.status_var.set("Cannot delete point (need at least 3 points)")
            return

        delete_index = self.selected_point_idx
        del self.raceline_points[delete_index]
        self.shift_regions_for_delete(delete_index)
        self.selected_point_idx = None
        self.selected_region_idx = None
        self.refresh_region_ui()
        self.refresh_velocity_bounds()
        self.update_display()
        self.update_info_display()
        self.status_var.set("Point deleted")

    def shift_regions_for_insert(self, insert_index):
        updated_regions = []
        for region in self.regions:
            start_index = region.start_index
            end_index = region.end_index
            if insert_index <= start_index:
                start_index += 1
                end_index += 1
            elif start_index < insert_index <= end_index:
                end_index += 1
            updated_regions.append(
                Region(start_index, end_index, region.multiplier, region.name)
            )
        self.regions = updated_regions
        self.refresh_region_ui()

    def shift_regions_for_delete(self, delete_index):
        updated_regions = []
        for region in self.regions:
            start_index = region.start_index
            end_index = region.end_index

            if delete_index < start_index:
                start_index -= 1
                end_index -= 1
            elif start_index <= delete_index <= end_index:
                end_index -= 1

            if start_index <= end_index:
                updated_regions.append(
                    Region(start_index, end_index, region.multiplier, region.name)
                )

        self.regions = updated_regions

    def update_info_display(self):
        self.info_text.delete(1.0, tk.END)

        info = f"Total Points: {len(self.raceline_points)}\n"
        info += f"Regions: {len(self.regions)}\n\n"

        if self.selected_point_idx is not None:
            point = self.raceline_points[self.selected_point_idx]
            multiplier = region_multiplier_for_index(self.selected_point_idx, self.regions)
            effective_velocity = point[2] * multiplier
            info += f"Selected Point #{self.selected_point_idx}\n"
            info += f"X: {point[0]:.6f}\n"
            info += f"Y: {point[1]:.6f}\n"
            info += f"Base Velocity: {point[2]:.3f}\n"
            info += f"Region Multiplier: {multiplier:.3f}\n"
            info += f"Effective Velocity: {effective_velocity:.3f}\n\n"

            self.velocity_var.set(point[2])
            self.x_var.set(point[0])
            self.y_var.set(point[1])
            self.velocity_entry.config(state="normal")
            self.x_entry.config(state="normal")
            self.y_entry.config(state="normal")
        else:
            self.velocity_entry.config(state="disabled")
            self.x_entry.config(state="disabled")
            self.y_entry.config(state="disabled")

        if self.selected_region_idx is not None and self.selected_region_idx < len(self.regions):
            region = self.regions[self.selected_region_idx]
            region_name = region.name or f"Zone {self.selected_region_idx + 1}"
            info += f"Selected Region: {region_name}\n"
            info += f"Range: {region.start_index} - {region.end_index}\n"
            info += f"Multiplier: {region.multiplier:.3f}\n\n"

        if self.spline_points:
            info += f"Spline Points: {len(self.spline_points)}\n"

        self.info_text.insert(1.0, info)

    def update_selected_point_velocity(self, event=None):
        if self.selected_point_idx is None:
            return

        try:
            new_velocity = self.velocity_var.get()
            self.raceline_points[self.selected_point_idx][2] = new_velocity
            self.refresh_velocity_bounds()
            self.update_display()
            self.update_info_display()
            self.status_var.set(f"Updated base velocity to {new_velocity:.3f}")
        except Exception as e:
            self.status_var.set(f"Error updating velocity: {str(e)}")

    def set_quick_velocity(self, velocity):
        if self.selected_point_idx is not None:
            self.velocity_var.set(velocity)
            self.update_selected_point_velocity()

    def update_selected_point_coords(self, event=None):
        if self.selected_point_idx is None:
            return

        try:
            new_x = self.x_var.get()
            new_y = self.y_var.get()
            self.raceline_points[self.selected_point_idx][0] = new_x
            self.raceline_points[self.selected_point_idx][1] = new_y
            self.update_display()
            self.update_info_display()
            self.status_var.set(f"Updated coordinates to ({new_x:.6f}, {new_y:.6f})")
        except Exception as e:
            self.status_var.set(f"Error updating coordinates: {str(e)}")

    def toggle_region_mode(self):
        self.set_region_mode(self.region_mode_var.get())
        state = "enabled" if self.save_from_spline else "disabled"
        self.status_var.set(f"Region mode {state}")

    def set_region_mode(self, enabled):
        self.region_mode = enabled
        self.region_mode_var.set(enabled)
        self.canvas.config(cursor="crosshair" if enabled else "")
        if not enabled:
            self.region_drag_start_idx = None
            self.region_preview_range = None
            if not self.region_start_var.get() or not self.region_end_var.get():
                self.region_selection_var.set("Selection: -")
            self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.update_display()

    def prepare_new_region(self):
        self.selected_region_idx = None
        self.region_listbox.selection_clear(0, tk.END)
        self.region_name_var.set(self.next_region_name())
        if self.region_preview_range:
            self.region_start_var.set(str(self.region_preview_range[0]))
            self.region_end_var.set(str(self.region_preview_range[1]))
            self.region_selection_var.set(
                f"Selection: {self.region_preview_range[0]} - {self.region_preview_range[1]}"
            )
        else:
            self.region_start_var.set("")
            self.region_end_var.set("")
            self.region_selection_var.set("Selection: -")
        self.region_multiplier_var.set("1.0")
        self.update_region_save_button()
        self.update_info_display()
        self.update_display()

    def save_region_from_form(self):
        if not self.raceline_points:
            messagebox.showwarning("Warning", "Load a raceline before creating regions")
            return

        try:
            start_index = int(self.region_start_var.get())
            end_index = int(self.region_end_var.get())
            multiplier = float(self.region_multiplier_var.get())
        except ValueError:
            messagebox.showerror("Error", "Start, end, and multiplier must be valid numbers")
            return

        if multiplier <= 0:
            messagebox.showerror("Error", "Multiplier must be greater than zero")
            return

        start_index, end_index = sorted((start_index, end_index))

        if start_index < 0 or end_index >= len(self.raceline_points):
            messagebox.showerror(
                "Error",
                f"Region indices must stay within 0 and {len(self.raceline_points) - 1}",
            )
            return

        name = self.region_name_var.get().strip() or self.next_region_name()
        region = Region(start_index, end_index, multiplier, name)

        if self.selected_region_idx is None:
            self.regions.append(region)
            self.selected_region_idx = len(self.regions) - 1
        else:
            self.regions[self.selected_region_idx] = region

        self.region_preview_range = (region.start_index, region.end_index)
        self.region_selection_var.set(
            f"Selection: {region.start_index} - {region.end_index}"
        )
        self.refresh_region_ui()
        self.refresh_velocity_bounds()
        self.update_display()
        self.update_info_display()
        self.status_var.set(
            f"Saved region {region.name or f'Zone {self.selected_region_idx + 1}'}"
        )

    def delete_selected_region(self):
        if self.selected_region_idx is None or self.selected_region_idx >= len(self.regions):
            self.status_var.set("Select a region to delete")
            return

        del self.regions[self.selected_region_idx]
        self.selected_region_idx = None
        self.region_preview_range = None
        self.region_name_var.set(self.next_region_name())
        self.region_start_var.set("")
        self.region_end_var.set("")
        self.region_multiplier_var.set("1.0")
        self.region_selection_var.set("Selection: -")
        self.refresh_region_ui()
        self.refresh_velocity_bounds()
        self.update_display()
        self.update_info_display()
        self.status_var.set("Region deleted")

    def on_region_list_select(self, event=None):
        selection = self.region_listbox.curselection()
        if not selection:
            return

        self.selected_region_idx = selection[0]
        region = self.regions[self.selected_region_idx]
        self.region_name_var.set(region.name)
        self.region_start_var.set(str(region.start_index))
        self.region_end_var.set(str(region.end_index))
        self.region_multiplier_var.set(f"{region.multiplier:.3f}")
        self.region_preview_range = (region.start_index, region.end_index)
        self.region_selection_var.set(
            f"Selection: {region.start_index} - {region.end_index}"
        )
        self.update_region_save_button()
        self.update_display()
        self.update_info_display()

    def next_region_name(self):
        return f"Zone {len(self.regions) + 1}"

    def refresh_region_ui(self):
        self.region_listbox.delete(0, tk.END)
        for region_index, region in enumerate(self.regions):
            name = region.name or f"Zone {region_index + 1}"
            self.region_listbox.insert(
                tk.END,
                f"{name}: {region.start_index}-{region.end_index} x{region.multiplier:.3f}",
            )

        if self.selected_region_idx is not None and self.selected_region_idx < len(self.regions):
            self.region_listbox.selection_set(self.selected_region_idx)
        else:
            self.selected_region_idx = None
            if not self.region_preview_range:
                self.region_selection_var.set("Selection: -")

        metadata_label = self.current_metadata_file or "none"
        self.metadata_status_var.set(f"Metadata: {metadata_label}")
        self.update_region_save_button()

    def update_region_save_button(self):
        button_text = "Update Region" if self.selected_region_idx is not None else "Create Region"
        self.region_save_button.config(text=button_text)

    def save_raceline(self):
        if not self.raceline_points:
            messagebox.showwarning("Warning", "No raceline to save")
            return

        raceline_path = filedialog.asksaveasfilename(
            title="Save Raceline",
            defaultextension=".csv",
            initialfile=os.path.basename(self.current_file) if self.current_file else "raceline.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not raceline_path:
            return

        metadata_path = None
        if self.regions or self.current_metadata_file:
            metadata_path = self.prompt_metadata_save_path(raceline_path=raceline_path)
            if not metadata_path:
                return

        try:
            effective_points = self.get_effective_raceline_points()
            self.refresh_velocity_bounds()
            self.update_spline()
            save_raceline_to_csv(
                raceline_path,
                effective_points,
                self.spline_points,
                self.save_from_spline,
            )

            if metadata_path:
                save_regions_to_json(metadata_path, self.regions, velocities_applied=True)
                self.current_metadata_file = metadata_path

            self.current_file = raceline_path
            self.refresh_region_ui()
            self.status_var.set(f"Saved to {raceline_path}")
            messagebox.showinfo("Success", "Raceline saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save raceline: {str(e)}")


def main():
    root = tk.Tk()
    RacelineEditorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
