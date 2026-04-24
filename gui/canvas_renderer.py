import tkinter as tk

import cv2
from PIL import Image, ImageTk

from extractor.regions import (
    OvertakingAllowedRegion,
)
from spline import velocity_to_color


class CanvasRenderer:
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

    def update_display(self):
        self.gui.canvas.delete("all")

        if self.gui.map_image is not None:
            self.draw_map()

        if self.gui.raceline_points:
            self.draw_raceline()
            self.gui.spline_ops.update_spline()

    def draw_map(self):
        height, width = self.gui.map_image.shape[:2]
        scaled_width = int(width * self.gui.scale_factor)
        scaled_height = int(height * self.gui.scale_factor)
        resized_image = cv2.resize(self.gui.map_image, (scaled_width, scaled_height))
        pil_image = Image.fromarray(resized_image)
        self.gui.photo = ImageTk.PhotoImage(pil_image)
        self.gui.canvas.create_image(
            self.gui.offset_x, self.gui.offset_y, anchor=tk.NW, image=self.gui.photo
        )

    def draw_raceline(self):
        if len(self.gui.raceline_points) < 2:
            return

        for index in range(len(self.gui.raceline_points)):
            current_point = self.gui.raceline_points[index]
            next_point = self.gui.raceline_points[
                (index + 1) % len(self.gui.raceline_points)
            ]
            x1, y1 = self.world_to_canvas_coords(current_point[0], current_point[1])
            x2, y2 = self.world_to_canvas_coords(next_point[0], next_point[1])
            self.gui.canvas.create_line(
                x1, y1, x2, y2, fill="red", width=2, tags="raceline"
            )

        self.draw_regions()
        self.draw_region_preview()

        for index, point in enumerate(self.gui.raceline_points):
            x, y = self.world_to_canvas_coords(point[0], point[1])
            color = self.point_fill_color(index)
            size = 8 if index == self.gui.selected_point_idx else 6
            self.gui.canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=color,
                outline="black",
                width=2,
                tags=f"point_{index}",
            )

            if index == self.gui.selected_point_idx or (
                index % 5 == 0 and self.gui.scale_factor > 0.5
            ):
                effective_velocity = self.gui.point_ops.get_effective_velocity(index)
                text_color = "black" if index == self.gui.selected_point_idx else "gray"
                self.gui.canvas.create_text(
                    x + 12,
                    y - 12,
                    text=f"v:{effective_velocity:.2f}",
                    fill=text_color,
                    font=("Arial", 8),
                    tags="velocity_label",
                )

    def draw_regions(self):
        for region_index, region in enumerate(self.gui.regions):
            color = self.region_color(region_index)
            width = 6 if region_index == self.gui.selected_region_idx else 4
            if region_index == self.gui.selected_region_idx:
                dash = None
            elif isinstance(region, OvertakingAllowedRegion):
                dash = (2, 3)
            else:
                dash = (6, 4)

            for point_index in range(region.start_index, region.end_index):
                point_a = self.gui.raceline_points[point_index]
                point_b = self.gui.raceline_points[point_index + 1]
                x1, y1 = self.world_to_canvas_coords(point_a[0], point_a[1])
                x2, y2 = self.world_to_canvas_coords(point_b[0], point_b[1])
                self.gui.canvas.create_line(
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
                self.gui.raceline_points[region.start_index][0],
                self.gui.raceline_points[region.start_index][1],
            )
            end_x, end_y = self.world_to_canvas_coords(
                self.gui.raceline_points[region.end_index][0],
                self.gui.raceline_points[region.end_index][1],
            )
            self.gui.canvas.create_oval(
                start_x - 10,
                start_y - 10,
                start_x + 10,
                start_y + 10,
                outline=color,
                width=3,
                tags="region",
            )
            self.gui.canvas.create_rectangle(
                end_x - 8,
                end_y - 8,
                end_x + 8,
                end_y + 8,
                outline=color,
                width=3,
                tags="region",
            )

            label_index = (region.start_index + region.end_index) // 2
            label_point = self.gui.raceline_points[label_index]
            label_x, label_y = self.world_to_canvas_coords(
                label_point[0], label_point[1]
            )
            self.gui.canvas.create_text(
                label_x + 18,
                label_y + 16,
                text=(
                    f"{self.gui.region_ops.region_name_for_display(region, region_index)} "
                    f"{self.gui.region_ops.region_value_text(region)}"
                ),
                fill=color,
                font=("Arial", 9, "bold"),
                anchor=tk.W,
                tags="region",
            )

    def draw_region_preview(self):
        if not self.gui.region_preview_range:
            return

        start_index, end_index = self.gui.region_preview_range
        preview_color = "#00c2ff"

        for point_index in range(start_index, end_index):
            point_a = self.gui.raceline_points[point_index]
            point_b = self.gui.raceline_points[point_index + 1]
            x1, y1 = self.world_to_canvas_coords(point_a[0], point_a[1])
            x2, y2 = self.world_to_canvas_coords(point_b[0], point_b[1])
            self.gui.canvas.create_line(
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
            point = self.gui.raceline_points[boundary_index]
            x, y = self.world_to_canvas_coords(point[0], point[1])
            self.gui.canvas.create_oval(
                x - 10,
                y - 10,
                x + 10,
                y + 10,
                outline=preview_color,
                width=3,
                tags="region_preview",
            )

    def draw_spline(self):
        for index in range(len(self.gui.spline_points) - 1):
            x1, y1 = self.world_to_canvas_coords(
                self.gui.spline_points[index][0], self.gui.spline_points[index][1]
            )
            x2, y2 = self.world_to_canvas_coords(
                self.gui.spline_points[index + 1][0],
                self.gui.spline_points[index + 1][1],
            )
            avg_velocity = (
                self.gui.spline_points[index][2] + self.gui.spline_points[index + 1][2]
            ) / 2
            color = velocity_to_color(
                avg_velocity, self.gui.min_velocity, self.gui.max_velocity
            )
            self.gui.canvas.create_line(
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
            color = velocity_to_color(
                avg_velocity, self.gui.min_velocity, self.gui.max_velocity
            )
            self.gui.canvas.create_line(
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

    def world_to_canvas_coords(self, x, y):
        if not self.gui.map_metadata:
            return x, y

        resolution = self.gui.map_metadata["resolution"]
        origin = self.gui.map_metadata["origin"]
        pixel_x = (x - origin[0]) / resolution
        pixel_y = self.gui.map_image.shape[0] - (y - origin[1]) / resolution

        canvas_x = pixel_x * self.gui.scale_factor + self.gui.offset_x
        canvas_y = pixel_y * self.gui.scale_factor + self.gui.offset_y
        return canvas_x, canvas_y

    def canvas_to_world_coords(self, canvas_x, canvas_y):
        if not self.gui.map_metadata:
            return canvas_x, canvas_y

        resolution = self.gui.map_metadata["resolution"]
        origin = self.gui.map_metadata["origin"]
        pixel_x = (canvas_x - self.gui.offset_x) / self.gui.scale_factor
        pixel_y = (canvas_y - self.gui.offset_y) / self.gui.scale_factor

        world_x = pixel_x * resolution + origin[0]
        world_y = (self.gui.map_image.shape[0] - pixel_y) * resolution + origin[1]
        return world_x, world_y

    def point_fill_color(self, point_index):
        if point_index == self.gui.selected_point_idx:
            return "yellow"
        if (
            self.gui.region_preview_range
            and self.gui.region_preview_range[0]
            <= point_index
            <= self.gui.region_preview_range[1]
        ):
            return "#00c2ff"
        region_index = self.last_region_covering_point(point_index)
        if region_index is not None:
            return self.region_color(region_index)
        return "blue"

    def last_region_covering_point(self, point_index):
        for region_index in range(len(self.gui.regions) - 1, -1, -1):
            region = self.gui.regions[region_index]
            if region.start_index <= point_index <= region.end_index:
                return region_index
        return None

    def region_color(self, region_index):
        return self.REGION_COLORS[region_index % len(self.REGION_COLORS)]

    def reset_view(self):
        if self.gui.map_image is not None:
            height, width = self.gui.map_image.shape[:2]
            scale_x = self.gui.canvas_width / width
            scale_y = self.gui.canvas_height / height
            self.gui.scale_factor = min(scale_x, scale_y) * 0.9
            self.gui.offset_x = (
                self.gui.canvas_width - width * self.gui.scale_factor
            ) // 2
            self.gui.offset_y = (
                self.gui.canvas_height - height * self.gui.scale_factor
            ) // 2

        self.update_display()
