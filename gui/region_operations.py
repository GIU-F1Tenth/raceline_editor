import tkinter as tk
from tkinter import messagebox

from extractor.regions import (
    ConstantSpeedMultiplierRegion,
    OvertakingAllowedRegion,
)


class RegionOperations:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    def current_region_type(self):
        return self.gui.region_type_var.get()

    def set_region_type_selection(self, region_type):
        self.gui.region_type_var.set(region_type)
        self.gui.ui_builder.update_region_type_controls()

    def region_type_for_region(self, region):
        if isinstance(region, ConstantSpeedMultiplierRegion):
            return ConstantSpeedMultiplierRegion.REGION_TYPE
        if isinstance(region, OvertakingAllowedRegion):
            return OvertakingAllowedRegion.REGION_TYPE
        return ""

    def region_name_for_display(self, region, region_index=None):
        if region.name:
            return region.name
        if region_index is not None:
            return f"Zone {region_index + 1}"
        return "Zone"

    def region_value_text(self, region):
        if isinstance(region, ConstantSpeedMultiplierRegion):
            return f"x{region.multiplier:.3f}"
        if isinstance(region, OvertakingAllowedRegion):
            return f"can_overtake={str(region.can_overtake).lower()}"
        return ""

    def region_list_text(self, region, region_index):
        name = self.region_name_for_display(region, region_index)
        region_type = self.region_type_for_region(region)
        value_text = self.region_value_text(region)
        return f"{name} [{region_type}]: {region.start_index}-{region.end_index} {value_text}"

    def prepare_new_region(self):
        self.gui.selected_region_idx = None
        self.gui.region_listbox.selection_clear(0, tk.END)
        self.gui.region_name_var.set(self.next_region_name())
        if self.gui.region_preview_range:
            self.gui.region_start_var.set(str(self.gui.region_preview_range[0]))
            self.gui.region_end_var.set(str(self.gui.region_preview_range[1]))
            self.gui.region_selection_var.set(
                f"Selection: {self.gui.region_preview_range[0]} - {self.gui.region_preview_range[1]}"
            )
        else:
            self.gui.region_start_var.set("")
            self.gui.region_end_var.set("")
            self.gui.region_selection_var.set("Selection: -")
        self.gui.region_multiplier_var.set("1.0")
        self.gui.ui_builder.update_region_type_controls()
        self.update_region_save_button()
        self.gui.point_ops.update_info_display()
        self.gui.canvas_renderer.update_display()

    def save_region_from_form(self):
        if not self.gui.raceline_points:
            messagebox.showwarning("Warning", "Load a raceline before creating regions")
            return

        try:
            start_index = int(self.gui.region_start_var.get())
            end_index = int(self.gui.region_end_var.get())
        except ValueError:
            messagebox.showerror("Error", "Start and end must be valid whole numbers")
            return

        start_index, end_index = sorted((start_index, end_index))

        if start_index < 0 or end_index >= len(self.gui.raceline_points):
            messagebox.showerror(
                "Error",
                f"Region indices must stay within 0 and {len(self.gui.raceline_points) - 1}",
            )
            return

        name = self.gui.region_name_var.get().strip() or self.next_region_name()
        region_type = self.current_region_type()
        if region_type == ConstantSpeedMultiplierRegion.REGION_TYPE:
            try:
                multiplier = float(self.gui.region_multiplier_var.get())
            except ValueError:
                messagebox.showerror("Error", "Multiplier must be a valid number")
                return

            if multiplier <= 0:
                messagebox.showerror("Error", "Multiplier must be greater than zero")
                return

            region = ConstantSpeedMultiplierRegion(
                start_index,
                end_index,
                multiplier,
                name=name,
            )
        else:
            region = OvertakingAllowedRegion(
                start_index,
                end_index,
                name=name,
                can_overtake=True,
            )

        if self.gui.selected_region_idx is None:
            self.gui.regions.append(region)
            self.gui.selected_region_idx = len(self.gui.regions) - 1
        else:
            self.gui.regions[self.gui.selected_region_idx] = region

        self.gui.region_preview_range = (region.start_index, region.end_index)
        self.gui.region_selection_var.set(
            f"Selection: {region.start_index} - {region.end_index}"
        )
        self.refresh_region_ui()
        self.gui.point_ops.refresh_velocity_bounds()
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()
        self.gui.status_var.set(
            f"Saved region {self.region_name_for_display(region, self.gui.selected_region_idx)}"
        )

    def delete_selected_region(self):
        if self.gui.selected_region_idx is None or self.gui.selected_region_idx >= len(
            self.gui.regions
        ):
            self.gui.status_var.set("Select a region to delete")
            return

        del self.gui.regions[self.gui.selected_region_idx]
        self.gui.selected_region_idx = None
        self.gui.region_preview_range = None
        self.gui.region_name_var.set(self.next_region_name())
        self.gui.region_start_var.set("")
        self.gui.region_end_var.set("")
        self.gui.region_multiplier_var.set("1.0")
        self.gui.region_selection_var.set("Selection: -")
        self.gui.ui_builder.update_region_type_controls()
        self.refresh_region_ui()
        self.gui.point_ops.refresh_velocity_bounds()
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()
        self.gui.status_var.set("Region deleted")

    def next_region_name(self):
        return f"Zone {len(self.gui.regions) + 1}"

    def refresh_region_ui(self):
        self.gui.region_listbox.delete(0, tk.END)
        for region_index, region in enumerate(self.gui.regions):
            self.gui.region_listbox.insert(
                tk.END, self.region_list_text(region, region_index)
            )

        if (
            self.gui.selected_region_idx is not None
            and self.gui.selected_region_idx < len(self.gui.regions)
        ):
            self.gui.region_listbox.selection_set(self.gui.selected_region_idx)
        else:
            self.gui.selected_region_idx = None
            if not self.gui.region_preview_range:
                self.gui.region_selection_var.set("Selection: -")

        metadata_label = self.gui.current_metadata_file or "none"
        self.gui.metadata_status_var.set(f"Metadata: {metadata_label}")
        self.update_region_save_button()

    def update_region_save_button(self):
        button_text = (
            "Update Region"
            if self.gui.selected_region_idx is not None
            else "Create Region"
        )
        self.gui.region_save_button.config(text=button_text)

    def toggle_region_mode(self):
        self.set_region_mode(self.gui.region_mode_var.get())
        state = "enabled" if self.gui.region_mode else "disabled"
        self.gui.status_var.set(f"Region mode {state}")

    def set_region_mode(self, enabled):
        self.gui.region_mode = enabled
        self.gui.region_mode_var.set(enabled)
        self.gui.canvas.config(cursor="crosshair" if enabled else "")
        if not enabled:
            self.gui.region_drag_start_idx = None
            self.gui.region_preview_range = None
            if not self.gui.region_start_var.get() or not self.gui.region_end_var.get():
                self.gui.region_selection_var.set("Selection: -")
            self.gui.canvas.bind("<Button-1>", self.gui.event_handlers.on_canvas_click)
        self.gui.canvas_renderer.update_display()

    def shift_regions_for_insert(self, insert_index):
        updated_regions = []
        for region in self.gui.regions:
            start_index = region.start_index
            end_index = region.end_index
            if insert_index <= start_index:
                start_index += 1
                end_index += 1
            elif start_index < insert_index <= end_index:
                end_index += 1
            updated_regions.append(region.with_indices(start_index, end_index))
        self.gui.regions = updated_regions
        self.refresh_region_ui()

    def shift_regions_for_delete(self, delete_index):
        updated_regions = []
        for region in self.gui.regions:
            start_index = region.start_index
            end_index = region.end_index

            if delete_index < start_index:
                start_index -= 1
                end_index -= 1
            elif start_index <= delete_index <= end_index:
                end_index -= 1

            if start_index <= end_index:
                updated_regions.append(region.with_indices(start_index, end_index))

        self.gui.regions = updated_regions
