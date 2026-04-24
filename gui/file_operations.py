import os
from tkinter import filedialog, messagebox

from config import DrawerConfig
from extractor.utils import (
    default_metadata_path,
    find_metadata_path_for_raceline,
    load_map_from_yaml,
    load_raceline_from_csv,
    load_regions_from_json,
    remove_regions_from_points,
    save_overtaking_to_csv,
    save_raceline_to_csv,
    save_regions_to_json,
)


class FileOperations:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    def load_default_data(self):
        try:
            map_yaml_path = DrawerConfig.MAP_YAML.value
            if os.path.exists(map_yaml_path):
                self.gui.map_image, self.gui.map_metadata = load_map_from_yaml(
                    map_yaml_path
                )

            raceline_path = DrawerConfig.RACING_CSV.value
            if os.path.exists(raceline_path):
                self.load_raceline_file(raceline_path, show_status=False)

            if self.gui.map_image is not None:
                self.gui.canvas_renderer.reset_view()
            else:
                self.gui.canvas_renderer.update_display()
        except Exception as e:
            self.gui.status_var.set(f"Error loading default data: {str(e)}")

    def load_map(self):
        file_path = filedialog.askopenfilename(
            title="Load Map YAML",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
        )

        if file_path:
            try:
                self.gui.map_image, self.gui.map_metadata = load_map_from_yaml(
                    file_path
                )
                self.gui.canvas_renderer.reset_view()
                self.gui.status_var.set("Map loaded successfully")
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
        self.gui.raceline_points = load_raceline_from_csv(file_path)
        self.gui.current_file = file_path
        self.gui.current_metadata_file = None
        self.gui.selected_point_idx = None
        self.gui.selected_region_idx = None
        self.gui.dragging_point = False
        self.gui.region_drag_start_idx = None
        self.gui.region_preview_range = None
        self.gui.regions = []

        metadata_path = find_metadata_path_for_raceline(file_path)
        if metadata_path:
            self.load_region_metadata_from_file(
                metadata_path, normalize_loaded_points=True
            )
        else:
            self.gui.region_ops.refresh_region_ui()

        self.gui.point_ops.refresh_velocity_bounds()
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()

        if show_status:
            metadata_suffix = (
                f" with metadata {os.path.basename(self.gui.current_metadata_file)}"
                if self.gui.current_metadata_file
                else ""
            )
            self.gui.status_var.set(
                f"Loaded {len(self.gui.raceline_points)} points{metadata_suffix}"
            )

    def load_region_metadata(self):
        if not self.gui.raceline_points:
            messagebox.showwarning("Warning", "Load a raceline before loading metadata")
            return

        file_path = filedialog.askopenfilename(
            title="Load Region Metadata",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if file_path:
            try:
                normalize_loaded_points = self.gui.current_metadata_file is None
                self.load_region_metadata_from_file(
                    file_path, normalize_loaded_points=normalize_loaded_points
                )
                self.gui.status_var.set(
                    f"Loaded {len(self.gui.regions)} regions from {os.path.basename(file_path)}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load metadata: {str(e)}")

    def load_region_metadata_from_file(self, file_path, normalize_loaded_points=False):
        payload = load_regions_from_json(file_path)
        regions = payload["regions"]

        if normalize_loaded_points and payload["velocities_applied"]:
            self.gui.raceline_points = remove_regions_from_points(
                self.gui.raceline_points, regions
            )

        self.gui.regions = regions
        self.gui.current_metadata_file = file_path
        self.gui.selected_region_idx = None
        self.gui.region_preview_range = None
        self.gui.region_ops.refresh_region_ui()
        self.gui.point_ops.refresh_velocity_bounds()
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()

    def save_region_metadata(self):
        if not self.gui.raceline_points:
            messagebox.showwarning("Warning", "No raceline loaded")
            return

        file_path = self.prompt_metadata_save_path()
        if not file_path:
            return

        try:
            save_regions_to_json(file_path, self.gui.regions, velocities_applied=True)
            self.gui.current_metadata_file = file_path
            self.gui.region_ops.refresh_region_ui()
            self.gui.status_var.set(f"Saved metadata to {file_path}")
            messagebox.showinfo("Success", "Region metadata saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {str(e)}")

    def prompt_metadata_save_path(self, raceline_path=None):
        base_raceline_path = raceline_path or self.gui.current_file
        initial_path = self.gui.current_metadata_file
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

    def default_overtaking_filename(self):
        if not self.gui.current_file:
            return "overtaking.csv"
        file_stem, _ = os.path.splitext(os.path.basename(self.gui.current_file))
        return f"{file_stem}_overtaking.csv"

    def save_overtaking_csv(self):
        if not self.gui.raceline_points:
            messagebox.showwarning("Warning", "No raceline to save")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Overtaking CSV",
            defaultextension=".csv",
            initialfile=self.default_overtaking_filename(),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            self.gui.point_ops.refresh_velocity_bounds()
            self.gui.spline_ops.update_spline()
            save_overtaking_to_csv(
                file_path,
                self.gui.raceline_points,
                self.gui.regions,
                self.gui.spline_points,
                self.gui.save_from_spline,
            )
            self.gui.status_var.set(f"Saved overtaking CSV to {file_path}")
            messagebox.showinfo("Success", "Overtaking CSV saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save overtaking CSV: {str(e)}")

    def save_raceline(self):
        if not self.gui.raceline_points:
            messagebox.showwarning("Warning", "No raceline to save")
            return

        raceline_path = filedialog.asksaveasfilename(
            title="Save Raceline",
            defaultextension=".csv",
            initialfile=os.path.basename(self.gui.current_file)
            if self.gui.current_file
            else "raceline.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not raceline_path:
            return

        metadata_path = None
        if self.gui.regions or self.gui.current_metadata_file:
            metadata_path = self.prompt_metadata_save_path(raceline_path=raceline_path)
            if not metadata_path:
                return

        try:
            effective_points = self.gui.point_ops.get_effective_raceline_points()
            self.gui.point_ops.refresh_velocity_bounds()
            self.gui.spline_ops.update_spline()
            save_raceline_to_csv(
                raceline_path,
                effective_points,
                self.gui.spline_points,
                self.gui.save_from_spline,
            )

            if metadata_path:
                save_regions_to_json(
                    metadata_path, self.gui.regions, velocities_applied=True
                )
                self.gui.current_metadata_file = metadata_path

            self.gui.current_file = raceline_path
            self.gui.region_ops.refresh_region_ui()
            self.gui.status_var.set(f"Saved to {raceline_path}")
            messagebox.showinfo("Success", "Raceline saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save raceline: {str(e)}")
