from spline import generate_spline


class SplineOperations:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    def initialize_spline(self):
        if len(self.gui.raceline_points) >= 2:
            try:
                self.update_spline()
                self.gui.status_var.set(
                    f"Ready - {len(self.gui.raceline_points)} points loaded"
                )
            except Exception as e:
                self.gui.status_var.set(f"Ready - spline init failed: {str(e)}")

    def update_spline(self, event=None):
        self.gui.canvas.delete("spline")

        effective_points = self.gui.point_ops.get_effective_raceline_points()
        if len(effective_points) < 3:
            self.gui.spline_points = []
            return

        try:
            smoothness = max(0.0, self.gui.smoothness_var.get())
            resolution = max(50, int(self.gui.resolution_var.get()))
            self.gui.spline_points = generate_spline(
                effective_points, smoothness, resolution
            )

            if self.gui.spline_points is None:
                self.gui.spline_points = []
                self.gui.canvas_renderer.draw_simple_spline_fallback(effective_points)
                return

            self.gui.canvas_renderer.draw_spline()
        except Exception as e:
            self.gui.spline_points = []
            self.gui.status_var.set(f"Spline error - using simple curve: {str(e)}")
            self.gui.canvas_renderer.draw_simple_spline_fallback(effective_points)

    def force_spline_update(self, event=None):
        if len(self.gui.raceline_points) >= 2:
            self.gui.root.after_idle(self.gui.canvas_renderer.update_display)
