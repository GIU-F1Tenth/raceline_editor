import tkinter as tk

from extractor.regions import (
    ConstantSpeedMultiplierRegion,
    OvertakingAllowedRegion,
)
from extractor.utils import (
    apply_regions_to_points,
    can_overtake_for_index,
    region_multiplier_for_index,
)


class PointOperations:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    def update_info_display(self):
        self.gui.info_text.delete(1.0, tk.END)

        speed_region_count = sum(
            isinstance(region, ConstantSpeedMultiplierRegion)
            for region in self.gui.regions
        )
        overtaking_region_count = sum(
            isinstance(region, OvertakingAllowedRegion) for region in self.gui.regions
        )
        info = f"Total Points: {len(self.gui.raceline_points)}\n"
        info += (
            f"Regions: {len(self.gui.regions)} "
            f"(speed={speed_region_count}, overtaking={overtaking_region_count})\n\n"
        )

        if self.gui.selected_point_idx is not None:
            point = self.gui.raceline_points[self.gui.selected_point_idx]
            multiplier = region_multiplier_for_index(
                self.gui.selected_point_idx, self.gui.regions
            )
            can_overtake = can_overtake_for_index(
                self.gui.selected_point_idx, self.gui.regions
            )
            effective_velocity = point[2] * multiplier
            info += f"Selected Point #{self.gui.selected_point_idx}\n"
            info += f"X: {point[0]:.6f}\n"
            info += f"Y: {point[1]:.6f}\n"
            info += f"Base Velocity: {point[2]:.3f}\n"
            info += f"Region Multiplier: {multiplier:.3f}\n"
            info += f"Can Overtake: {'Yes' if can_overtake else 'No'}\n"
            info += f"Effective Velocity: {effective_velocity:.3f}\n\n"

            self.gui.velocity_var.set(point[2])
            self.gui.x_var.set(point[0])
            self.gui.y_var.set(point[1])
            self.gui.velocity_entry.config(state="normal")
            self.gui.x_entry.config(state="normal")
            self.gui.y_entry.config(state="normal")
        else:
            self.gui.velocity_entry.config(state="disabled")
            self.gui.x_entry.config(state="disabled")
            self.gui.y_entry.config(state="disabled")

        if (
            self.gui.selected_region_idx is not None
            and self.gui.selected_region_idx < len(self.gui.regions)
        ):
            region = self.gui.regions[self.gui.selected_region_idx]
            region_name = self.gui.region_ops.region_name_for_display(
                region, self.gui.selected_region_idx
            )
            info += f"Selected Region: {region_name}\n"
            info += f"Type: {self.gui.region_ops.region_type_for_region(region)}\n"
            info += f"Range: {region.start_index} - {region.end_index}\n"
            if isinstance(region, ConstantSpeedMultiplierRegion):
                info += f"Multiplier: {region.multiplier:.3f}\n\n"
            elif isinstance(region, OvertakingAllowedRegion):
                info += f"Can Overtake: {'Yes' if region.can_overtake else 'No'}\n\n"

        if self.gui.spline_points:
            info += f"Spline Points: {len(self.gui.spline_points)}\n"

        self.gui.info_text.insert(1.0, info)

    def update_selected_point_velocity(self, event=None):
        if self.gui.selected_point_idx is None:
            return

        try:
            new_velocity = self.gui.velocity_var.get()
            self.gui.raceline_points[self.gui.selected_point_idx][2] = new_velocity
            self.refresh_velocity_bounds()
            self.gui.canvas_renderer.update_display()
            self.update_info_display()
            self.gui.status_var.set(f"Updated base velocity to {new_velocity:.3f}")
        except Exception as e:
            self.gui.status_var.set(f"Error updating velocity: {str(e)}")

    def update_selected_point_coords(self, event=None):
        if self.gui.selected_point_idx is None:
            return

        try:
            new_x = self.gui.x_var.get()
            new_y = self.gui.y_var.get()
            self.gui.raceline_points[self.gui.selected_point_idx][0] = new_x
            self.gui.raceline_points[self.gui.selected_point_idx][1] = new_y
            self.gui.canvas_renderer.update_display()
            self.update_info_display()
            self.gui.status_var.set(
                f"Updated coordinates to ({new_x:.6f}, {new_y:.6f})"
            )
        except Exception as e:
            self.gui.status_var.set(f"Error updating coordinates: {str(e)}")

    def set_quick_velocity(self, velocity):
        if self.gui.selected_point_idx is not None:
            self.gui.velocity_var.set(velocity)
            self.update_selected_point_velocity()

    def delete_selected_point(self):
        if self.gui.selected_point_idx is None or len(self.gui.raceline_points) <= 3:
            self.gui.status_var.set("Cannot delete point (need at least 3 points)")
            return

        delete_index = self.gui.selected_point_idx
        del self.gui.raceline_points[delete_index]
        self.gui.region_ops.shift_regions_for_delete(delete_index)
        self.gui.selected_point_idx = None
        self.gui.selected_region_idx = None
        self.gui.region_ops.refresh_region_ui()
        self.refresh_velocity_bounds()
        self.gui.canvas_renderer.update_display()
        self.update_info_display()
        self.gui.status_var.set("Point deleted")

    def find_nearest_point_index(self, canvas_x, canvas_y, threshold=15):
        min_distance = float("inf")
        nearest_index = None

        for index, point in enumerate(self.gui.raceline_points):
            x, y = self.gui.canvas_renderer.world_to_canvas_coords(point[0], point[1])
            distance = ((canvas_x - x) ** 2 + (canvas_y - y) ** 2) ** 0.5
            if distance < min_distance and distance < threshold:
                min_distance = distance
                nearest_index = index

        return nearest_index

    def refresh_velocity_bounds(self):
        if not self.gui.raceline_points:
            self.gui.min_velocity = 0.5
            self.gui.max_velocity = 5.0
            return

        effective_points = self.get_effective_raceline_points()
        velocities = [point[2] for point in effective_points]
        self.gui.min_velocity = min(velocities)
        self.gui.max_velocity = max(velocities)
        if self.gui.min_velocity == self.gui.max_velocity:
            self.gui.max_velocity = self.gui.min_velocity + 1.0

    def get_effective_velocity(self, point_index):
        point = self.gui.raceline_points[point_index]
        return point[2] * region_multiplier_for_index(point_index, self.gui.regions)

    def get_effective_raceline_points(self):
        return apply_regions_to_points(self.gui.raceline_points, self.gui.regions)
