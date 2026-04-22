import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os

from PIL import Image, ImageTk

from config import DrawerConfig
from extractor import load_map_from_yaml, load_raceline_from_csv, save_raceline_to_csv
from spline import generate_spline, velocity_to_color


class RacelineEditorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("F1Tenth Raceline Editor")
        self.root.geometry("1400x900")

        # Data storage
        self.raceline_points = []  # World coordinates (x, y, velocity)
        self.map_image = None
        self.map_metadata = None
        self.current_file = None
        self.selected_point_idx = None
        self.spline_points = []
        self.min_velocity = 0.5
        self.max_velocity = 5.0

        # UI state
        self.canvas_width = 800
        self.canvas_height = 600
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.save_from_spline = False 

        self.setup_ui()
        self.load_default_data()

        # Ensure spline is initialized after a short delay
        self.root.after(100, self.initialize_spline)

    def setup_ui(self):
        """Setup the main UI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel for map display
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Map canvas
        self.canvas = tk.Canvas(left_frame, width=self.canvas_width, height=self.canvas_height,
                                bg='white', bd=2, relief=tk.SUNKEN)
        self.canvas.pack(pady=(0, 10))

        # Velocity legend
        legend_frame = ttk.Frame(left_frame)
        legend_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(legend_frame, text="Velocity:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))

        # Create gradient-like legend with colored labels
        legend_colors_frame = ttk.Frame(legend_frame)
        legend_colors_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_canvas_zoom)

        # Control buttons
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X)

        ttk.Button(control_frame, text="Add Point",
                   command=self.add_point_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Delete Point",
                   command=self.delete_selected_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Reset View",
                   command=self.reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Save from Spline",
                   command=self.set_save_from_spline).pack(side=tk.LEFT, padx=2)


        # Right panel for controls and info
        right_frame = ttk.Frame(main_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        # File operations
        file_frame = ttk.LabelFrame(right_frame, text="File Operations")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(file_frame, text="Load Raceline",
                   command=self.load_raceline).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="Save Raceline",
                   command=self.save_raceline).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="Load Map",
                   command=self.load_map).pack(fill=tk.X, pady=2)

        # Point information
        info_frame = ttk.LabelFrame(right_frame, text="Point Information")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_text = tk.Text(info_frame, height=6, width=30)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Point editing controls
        edit_frame = ttk.LabelFrame(right_frame, text="Point Editing")
        edit_frame.pack(fill=tk.X, pady=(0, 10))

        # Velocity editing
        velocity_frame = ttk.Frame(edit_frame)
        velocity_frame.pack(fill=tk.X, pady=2)

        ttk.Label(velocity_frame, text="Velocity:").pack(side=tk.LEFT)
        self.velocity_var = tk.DoubleVar(value=1.0)
        self.velocity_entry = ttk.Entry(
            velocity_frame, textvariable=self.velocity_var, width=10)
        self.velocity_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.velocity_entry.bind(
            '<Return>', self.update_selected_point_velocity)
        self.velocity_entry.bind(
            '<FocusOut>', self.update_selected_point_velocity)

        ttk.Button(velocity_frame, text="Apply",
                   command=self.update_selected_point_velocity).pack(side=tk.LEFT, padx=2)

        # Quick velocity buttons
        quick_vel_frame = ttk.Frame(edit_frame)
        quick_vel_frame.pack(fill=tk.X, pady=2)

        ttk.Label(quick_vel_frame, text="Quick:").pack(side=tk.LEFT)
        for vel in [0.5, 1.0, 1.5, 2.0, 3.0]:
            ttk.Button(quick_vel_frame, text=f"{vel}", width=4,
                       command=lambda v=vel: self.set_quick_velocity(v)).pack(side=tk.LEFT, padx=1)

        # Coordinate editing
        coord_frame = ttk.Frame(edit_frame)
        coord_frame.pack(fill=tk.X, pady=2)

        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, sticky=tk.W)
        self.x_var = tk.DoubleVar(value=0.0)
        self.x_entry = ttk.Entry(
            coord_frame, textvariable=self.x_var, width=12)
        self.x_entry.grid(row=0, column=1, padx=(5, 5))
        self.x_entry.bind('<Return>', self.update_selected_point_coords)
        self.x_entry.bind('<FocusOut>', self.update_selected_point_coords)

        ttk.Label(coord_frame, text="Y:").grid(row=1, column=0, sticky=tk.W)
        self.y_var = tk.DoubleVar(value=0.0)
        self.y_entry = ttk.Entry(
            coord_frame, textvariable=self.y_var, width=12)
        self.y_entry.grid(row=1, column=1, padx=(5, 5))
        self.y_entry.bind('<Return>', self.update_selected_point_coords)
        self.y_entry.bind('<FocusOut>', self.update_selected_point_coords)

        ttk.Button(coord_frame, text="Update Coords",
                   command=self.update_selected_point_coords).grid(row=0, column=2, rowspan=2, padx=5)

        # Initially disable editing controls
        self.velocity_entry.config(state='disabled')
        self.x_entry.config(state='disabled')
        self.y_entry.config(state='disabled')

        # Spline controls
        spline_frame = ttk.LabelFrame(right_frame, text="Spline Settings")
        spline_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(spline_frame, text="Smoothness:").pack()
        self.smoothness_var = tk.DoubleVar(value=0.1)
        smoothness_scale = ttk.Scale(spline_frame, from_=0.01, to=1.0,
                                     variable=self.smoothness_var, orient=tk.HORIZONTAL)
        smoothness_scale.pack(fill=tk.X, pady=2)
        smoothness_scale.bind("<ButtonRelease-1>", self.force_spline_update)
        smoothness_scale.bind("<Motion>", self.force_spline_update)

        ttk.Label(spline_frame, text="Resolution:").pack()
        self.resolution_var = tk.IntVar(value=100)
        resolution_scale = ttk.Scale(spline_frame, from_=50, to=500,
                                     variable=self.resolution_var, orient=tk.HORIZONTAL)
        resolution_scale.pack(fill=tk.X, pady=2)
        resolution_scale.bind("<ButtonRelease-1>", self.force_spline_update)
        resolution_scale.bind("<Motion>", self.force_spline_update)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Keyboard bindings
        self.root.bind('<Delete>', lambda e: self.delete_selected_point())
        self.root.bind('<Control-s>', lambda e: self.save_raceline())
        self.root.bind('<Control-o>', lambda e: self.load_raceline())
        self.root.focus_set()  # Allow root to receive key events

    def set_save_from_spline(self):
        """Toggle whether to save from spline points or original points"""
        self.save_from_spline = not self.save_from_spline
        state = "enabled" if self.save_from_spline else "disabled"
        self.status_var.set(f"Save from Spline {state}")
    
    def load_default_data(self):
        try:
            map_yaml_path = DrawerConfig.MAP_YAML.value
            if os.path.exists(map_yaml_path):
                self.map_image, self.map_metadata = load_map_from_yaml(map_yaml_path)

            raceline_path = DrawerConfig.RACING_CSV.value
            if os.path.exists(raceline_path):
                self.raceline_points = load_raceline_from_csv(raceline_path)
                self.min_velocity = min(p[2] for p in self.raceline_points)
                self.max_velocity = max(p[2] for p in self.raceline_points)

        except Exception as e:
            self.status_var.set(f"Error loading default data: {str(e)}")

    def initialize_spline(self):
        """Initialize spline display after loading data"""
        if self.raceline_points and len(self.raceline_points) >= 2:
            try:
                self.update_spline()
                self.status_var.set(
                    f"Ready - {len(self.raceline_points)} points loaded with spline")
            except Exception as e:
                print(f"Initial spline generation failed: {e}")
                self.status_var.set(
                    f"Ready - {len(self.raceline_points)} points loaded")

    def load_map(self):
        file_path = filedialog.askopenfilename(
            title="Load Map YAML",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
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
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            self.raceline_points = load_raceline_from_csv(file_path)
            self.min_velocity = min(p[2] for p in self.raceline_points)
            self.max_velocity = max(p[2] for p in self.raceline_points)
            self.current_file = file_path
            self.update_display()
            self.update_info_display()
            self.status_var.set(f"Loaded {len(self.raceline_points)} points")

    def world_to_canvas_coords(self, x, y):
        """Convert world coordinates to canvas coordinates"""
        if not self.map_metadata:
            return x, y

        resolution = self.map_metadata['resolution']
        origin = self.map_metadata['origin']

        # Convert to image coordinates
        pixel_x = (x - origin[0]) / resolution
        pixel_y = self.map_image.shape[0] - (y - origin[1]) / resolution

        # Scale and offset for canvas
        canvas_x = pixel_x * self.scale_factor + self.offset_x
        canvas_y = pixel_y * self.scale_factor + self.offset_y

        return canvas_x, canvas_y

    def canvas_to_world_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to world coordinates"""
        if not self.map_metadata:
            return canvas_x, canvas_y

        resolution = self.map_metadata['resolution']
        origin = self.map_metadata['origin']

        # Convert from canvas to image coordinates
        pixel_x = (canvas_x - self.offset_x) / self.scale_factor
        pixel_y = (canvas_y - self.offset_y) / self.scale_factor

        # Convert to world coordinates
        world_x = pixel_x * resolution + origin[0]
        world_y = (self.map_image.shape[0] - pixel_y) * resolution + origin[1]

        return world_x, world_y

    def update_display(self):
        """Update the canvas display with map and raceline"""
        self.canvas.delete("all")

        if self.map_image is not None:
            self.draw_map()

        if self.raceline_points:
            self.draw_raceline()
            self.update_spline()

    def draw_map(self):
        """Draw the map on canvas"""
        height, width = self.map_image.shape[:2]

        # Scale image to fit canvas
        scaled_width = int(width * self.scale_factor)
        scaled_height = int(height * self.scale_factor)

        # Resize image
        resized_image = cv2.resize(
            self.map_image, (scaled_width, scaled_height))

        # Convert to PIL and then to PhotoImage
        pil_image = Image.fromarray(resized_image)
        self.photo = ImageTk.PhotoImage(pil_image)

        # Draw on canvas
        self.canvas.create_image(
            self.offset_x, self.offset_y, anchor=tk.NW, image=self.photo)

    def draw_raceline(self):
        """Draw raceline points on canvas"""
        if len(self.raceline_points) < 2:
            return

        # Draw lines between consecutive points
        for i in range(len(self.raceline_points)):
            curr_point = self.raceline_points[i]
            next_point = self.raceline_points[(
                i + 1) % len(self.raceline_points)]

            x1, y1 = self.world_to_canvas_coords(curr_point[0], curr_point[1])
            x2, y2 = self.world_to_canvas_coords(next_point[0], next_point[1])

            self.canvas.create_line(
                x1, y1, x2, y2, fill="red", width=2, tags="raceline")

        # Draw points with velocity information
        for i, point in enumerate(self.raceline_points):
            x, y = self.world_to_canvas_coords(point[0], point[1])

            # Highlight selected point
            color = "yellow" if i == self.selected_point_idx else "blue"
            size = 8 if i == self.selected_point_idx else 6

            self.canvas.create_oval(x-size, y-size, x+size, y+size,
                                    fill=color, outline="black", width=2, tags=f"point_{i}")

            # Add velocity label for selected point or every 5th point to avoid clutter
            if i == self.selected_point_idx or (i % 5 == 0 and self.scale_factor > 0.5):
                velocity = point[2]
                text_color = "black" if i == self.selected_point_idx else "gray"
                self.canvas.create_text(x + 12, y - 12, text=f"v:{velocity:.2f}",
                                        fill=text_color, font=("Arial", 8), tags="velocity_label")

    def update_spline(self, event=None):
        self.canvas.delete("spline")

        if len(self.raceline_points) < 3:
            return

        try:
            smoothness = max(0.0, self.smoothness_var.get())
            resolution = max(50, int(self.resolution_var.get()))

            self.spline_points = generate_spline(self.raceline_points, smoothness, resolution)

            if self.spline_points is None:
                self.draw_simple_spline_fallback()
                return

            self.draw_spline()

        except Exception as e:
            print(f"Spline generation failed: {e}")
            self.status_var.set(f"Spline error - using simple curve")
            self.draw_simple_spline_fallback()

    def draw_spline(self):
        for i in range(len(self.spline_points) - 1):
            x1, y1 = self.world_to_canvas_coords(self.spline_points[i][0], self.spline_points[i][1])
            x2, y2 = self.world_to_canvas_coords(self.spline_points[i+1][0], self.spline_points[i+1][1])

            v1 = self.spline_points[i][2] if len(self.spline_points[i]) > 2 else 1.0
            v2 = self.spline_points[i+1][2] if len(self.spline_points[i+1]) > 2 else 1.0
            avg_velocity = (v1 + v2) / 2
            color = velocity_to_color(avg_velocity, self.min_velocity, self.max_velocity)

            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3, tags="spline",
                                    smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND)
    
    def draw_simple_spline_fallback(self):
        if len(self.raceline_points) < 2:
            return

        for i in range(len(self.raceline_points)):
            curr_point = self.raceline_points[i]
            next_point = self.raceline_points[(i + 1) % len(self.raceline_points)]

            x1, y1 = self.world_to_canvas_coords(curr_point[0], curr_point[1])
            x2, y2 = self.world_to_canvas_coords(next_point[0], next_point[1])

            v1 = curr_point[2] if len(curr_point) > 2 else 1.0
            v2 = next_point[2] if len(next_point) > 2 else 1.0
            avg_velocity = (v1 + v2) / 2
            color = velocity_to_color(avg_velocity, self.min_velocity, self.max_velocity)

            if (0 <= x1 <= self.canvas_width and 0 <= y1 <= self.canvas_height and
                    0 <= x2 <= self.canvas_width and 0 <= y2 <= self.canvas_height):
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3, tags="spline",
                                        smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND)

    def force_spline_update(self, event=None):
        """Force an immediate spline update - used for real-time slider updates"""
        if self.raceline_points and len(self.raceline_points) >= 2:
            # Small delay to avoid too many updates during dragging
            self.root.after_idle(self.update_spline)

    def on_canvas_click(self, event):
        """Handle mouse click on canvas"""
        # Find nearest point
        min_dist = float('inf')
        nearest_idx = None

        for i, point in enumerate(self.raceline_points):
            x, y = self.world_to_canvas_coords(point[0], point[1])
            dist = ((event.x - x) ** 2 + (event.y - y) ** 2) ** 0.5

            if dist < min_dist and dist < 15:  # 15 pixel threshold
                min_dist = dist
                nearest_idx = i

        self.selected_point_idx = nearest_idx
        self.update_display()
        self.update_info_display()

    def on_canvas_drag(self, event):
        """Handle mouse drag on canvas"""
        if self.selected_point_idx is not None:
            world_x, world_y = self.canvas_to_world_coords(event.x, event.y)
            self.raceline_points[self.selected_point_idx][0] = world_x
            self.raceline_points[self.selected_point_idx][1] = world_y
            self.update_display()
            self.update_info_display()

    def on_canvas_release(self, event):
        """Handle mouse release on canvas"""
        pass

    def on_canvas_zoom(self, event):
        """Handle mouse wheel zoom"""
        if event.delta > 0:
            self.scale_factor *= 1.1
        else:
            self.scale_factor /= 1.1

        self.scale_factor = max(0.1, min(5.0, self.scale_factor))
        self.update_display()

    def reset_view(self):
        """Reset view to default"""
        if self.map_image is not None:
            height, width = self.map_image.shape[:2]

            # Calculate scale to fit canvas
            scale_x = self.canvas_width / width
            scale_y = self.canvas_height / height
            self.scale_factor = min(scale_x, scale_y) * 0.9

            # Center the image
            self.offset_x = (self.canvas_width - width *
                             self.scale_factor) // 2
            self.offset_y = (self.canvas_height - height *
                             self.scale_factor) // 2

        self.update_display()

    def add_point_mode(self):
        """Enable add point mode"""
        self.status_var.set("Click on canvas to add a new point")
        self.canvas.bind("<Button-1>", self.add_point_click)

    def add_point_click(self, event):
        """Add a new point at click location"""
        world_x, world_y = self.canvas_to_world_coords(event.x, event.y)

        # Add point with default velocity
        new_point = [world_x, world_y, 1.0]

        # Insert at appropriate position (after selected point or at end)
        if self.selected_point_idx is not None:
            self.raceline_points.insert(self.selected_point_idx + 1, new_point)
        else:
            self.raceline_points.append(new_point)

        # Restore normal click behavior
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.update_display()
        self.update_info_display()
        self.status_var.set("Point added")

    def delete_selected_point(self):
        """Delete the currently selected point"""
        if self.selected_point_idx is not None and len(self.raceline_points) > 3:
            del self.raceline_points[self.selected_point_idx]
            self.selected_point_idx = None
            self.update_display()
            self.update_info_display()
            self.status_var.set("Point deleted")
        else:
            self.status_var.set("Cannot delete point (need at least 3 points)")

    def update_info_display(self):
        """Update the information display"""
        self.info_text.delete(1.0, tk.END)

        info = f"Total Points: {len(self.raceline_points)}\n\n"

        if self.selected_point_idx is not None:
            point = self.raceline_points[self.selected_point_idx]
            info += f"Selected Point #{self.selected_point_idx}:\n"
            info += f"X: {point[0]:.6f}\n"
            info += f"Y: {point[1]:.6f}\n"
            info += f"Velocity: {point[2]:.3f}\n\n"

            # Update editing controls
            self.velocity_var.set(point[2])
            self.x_var.set(point[0])
            self.y_var.set(point[1])

            # Enable editing controls
            self.velocity_entry.config(state='normal')
            self.x_entry.config(state='normal')
            self.y_entry.config(state='normal')
        else:
            # Disable editing controls when no point is selected
            self.velocity_entry.config(state='disabled')
            self.x_entry.config(state='disabled')
            self.y_entry.config(state='disabled')

        if self.spline_points:
            info += f"Spline Points: {len(self.spline_points)}\n"

        self.info_text.insert(1.0, info)

    def update_selected_point_velocity(self, event=None):
        """Update the velocity of the selected point"""
        if self.selected_point_idx is not None:
            try:
                new_velocity = self.velocity_var.get()
                self.raceline_points[self.selected_point_idx][2] = new_velocity
                self.update_info_display()
                # Update the display to show velocity changes in labels
                self.update_display()
                self.status_var.set(f"Updated velocity to {new_velocity:.3f}")
            except Exception as e:
                self.status_var.set(f"Error updating velocity: {str(e)}")

    def set_quick_velocity(self, velocity):
        """Set velocity using quick buttons"""
        if self.selected_point_idx is not None:
            self.velocity_var.set(velocity)
            self.update_selected_point_velocity()

    def update_selected_point_coords(self, event=None):
        """Update the coordinates of the selected point"""
        if self.selected_point_idx is not None:
            try:
                new_x = self.x_var.get()
                new_y = self.y_var.get()
                self.raceline_points[self.selected_point_idx][0] = new_x
                self.raceline_points[self.selected_point_idx][1] = new_y
                self.update_display()
                self.update_info_display()
                self.status_var.set(
                    f"Updated coordinates to ({new_x:.6f}, {new_y:.6f})")
            except Exception as e:
                self.status_var.set(f"Error updating coordinates: {str(e)}")



    def save_raceline(self):
        if not self.raceline_points:
            messagebox.showwarning("Warning", "No raceline to save")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Raceline",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            try:
                save_raceline_to_csv(file_path, self.raceline_points, self.spline_points, self.save_from_spline)
                self.current_file = file_path
                self.status_var.set(f"Saved to {file_path}")
                messagebox.showinfo("Success", "Raceline saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save raceline: {str(e)}")


def main():
    root = tk.Tk()
    app = RacelineEditorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
