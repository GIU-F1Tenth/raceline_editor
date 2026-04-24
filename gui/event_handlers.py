class EventHandlers:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    def on_canvas_click(self, event):
        if self.gui.region_mode:
            self.start_region_selection(event)
            return

        nearest_index = self.gui.point_ops.find_nearest_point_index(event.x, event.y)
        self.gui.selected_point_idx = nearest_index
        self.gui.dragging_point = nearest_index is not None
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()

    def on_canvas_drag(self, event):
        if self.gui.region_mode:
            self.update_region_selection(event)
            return

        if self.gui.selected_point_idx is not None and self.gui.dragging_point:
            world_x, world_y = self.gui.canvas_renderer.canvas_to_world_coords(
                event.x, event.y
            )
            self.gui.raceline_points[self.gui.selected_point_idx][0] = world_x
            self.gui.raceline_points[self.gui.selected_point_idx][1] = world_y
            self.gui.canvas_renderer.update_display()
            self.gui.point_ops.update_info_display()

    def on_canvas_release(self, event):
        if self.gui.region_mode:
            self.finish_region_selection(event)
            return
        self.gui.dragging_point = False

    def on_canvas_zoom(self, event):
        if event.delta > 0:
            self.gui.scale_factor *= 1.1
        else:
            self.gui.scale_factor /= 1.1

        self.gui.scale_factor = max(0.1, min(5.0, self.gui.scale_factor))
        self.gui.canvas_renderer.update_display()

    def start_region_selection(self, event):
        nearest_index = self.gui.point_ops.find_nearest_point_index(event.x, event.y)
        if nearest_index is None:
            self.gui.region_drag_start_idx = None
            self.gui.region_preview_range = None
            self.gui.region_selection_var.set("Selection: -")
            self.gui.canvas_renderer.update_display()
            return

        self.gui.region_drag_start_idx = nearest_index
        self.gui.region_preview_range = (nearest_index, nearest_index)
        self.gui.region_selection_var.set(
            f"Selection: {nearest_index} - {nearest_index}"
        )
        self.gui.canvas_renderer.update_display()

    def update_region_selection(self, event):
        if self.gui.region_drag_start_idx is None:
            return

        nearest_index = self.gui.point_ops.find_nearest_point_index(
            event.x, event.y, threshold=25
        )
        if nearest_index is None:
            return

        start_index = min(self.gui.region_drag_start_idx, nearest_index)
        end_index = max(self.gui.region_drag_start_idx, nearest_index)
        self.gui.region_preview_range = (start_index, end_index)
        self.gui.region_selection_var.set(f"Selection: {start_index} - {end_index}")
        self.gui.canvas_renderer.update_display()

    def finish_region_selection(self, event):
        if self.gui.region_drag_start_idx is None:
            return

        nearest_index = self.gui.point_ops.find_nearest_point_index(
            event.x, event.y, threshold=25
        )
        if nearest_index is None:
            nearest_index = self.gui.region_drag_start_idx

        start_index = min(self.gui.region_drag_start_idx, nearest_index)
        end_index = max(self.gui.region_drag_start_idx, nearest_index)
        self.gui.region_preview_range = (start_index, end_index)
        self.gui.region_start_var.set(str(start_index))
        self.gui.region_end_var.set(str(end_index))
        if not self.gui.region_name_var.get().strip():
            self.gui.region_name_var.set(self.gui.region_ops.next_region_name())

        self.gui.region_selection_var.set(f"Selection: {start_index} - {end_index}")
        self.gui.region_drag_start_idx = None
        self.gui.canvas_renderer.update_display()

    def add_point_mode(self):
        self.gui.region_ops.set_region_mode(False)
        self.gui.status_var.set("Click on the canvas to add a new point")
        self.gui.canvas.bind("<Button-1>", self.add_point_click)

    def add_point_click(self, event):
        world_x, world_y = self.gui.canvas_renderer.canvas_to_world_coords(
            event.x, event.y
        )
        new_point = [world_x, world_y, 1.0]

        if self.gui.selected_point_idx is not None:
            insert_index = self.gui.selected_point_idx + 1
            self.gui.raceline_points.insert(insert_index, new_point)
            self.gui.region_ops.shift_regions_for_insert(insert_index)
            self.gui.selected_point_idx = insert_index
        else:
            insert_index = len(self.gui.raceline_points)
            self.gui.raceline_points.append(new_point)
            self.gui.selected_point_idx = insert_index

        self.gui.point_ops.refresh_velocity_bounds()
        self.gui.canvas.bind("<Button-1>", self.on_canvas_click)
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()
        self.gui.status_var.set("Point added")

    def on_region_list_select(self, event=None):
        selection = self.gui.region_listbox.curselection()
        if not selection:
            return

        self.gui.selected_region_idx = selection[0]
        region = self.gui.regions[self.gui.selected_region_idx]
        self.gui.region_name_var.set(region.name)
        self.gui.region_start_var.set(str(region.start_index))
        self.gui.region_end_var.set(str(region.end_index))
        self.gui.region_ops.set_region_type_selection(
            self.gui.region_ops.region_type_for_region(region)
        )

        from extractor.regions import ConstantSpeedMultiplierRegion

        if isinstance(region, ConstantSpeedMultiplierRegion):
            self.gui.region_multiplier_var.set(f"{region.multiplier:.3f}")
        else:
            self.gui.region_multiplier_var.set("1.0")

        self.gui.region_preview_range = (region.start_index, region.end_index)
        self.gui.region_selection_var.set(
            f"Selection: {region.start_index} - {region.end_index}"
        )
        self.gui.region_ops.update_region_save_button()
        self.gui.canvas_renderer.update_display()
        self.gui.point_ops.update_info_display()
