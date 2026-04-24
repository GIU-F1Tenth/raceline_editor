import tkinter as tk

from gui.ui_builder import UIBuilder
from gui.canvas_renderer import CanvasRenderer
from gui.event_handlers import EventHandlers
from gui.file_operations import FileOperations
from gui.region_operations import RegionOperations
from gui.point_operations import PointOperations
from gui.spline_operations import SplineOperations


class RacelineEditorGUI:
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

        self.ui_builder = UIBuilder(self)
        self.canvas_renderer = CanvasRenderer(self)
        self.event_handlers = EventHandlers(self)
        self.file_ops = FileOperations(self)
        self.region_ops = RegionOperations(self)
        self.point_ops = PointOperations(self)
        self.spline_ops = SplineOperations(self)

        self.ui_builder.setup_ui()
        self.file_ops.load_default_data()
        self.root.after(100, self.spline_ops.initialize_spline)


def main():
    root = tk.Tk()
    RacelineEditorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
