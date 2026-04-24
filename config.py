import os
from enum import Enum

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DrawerConfig(Enum):
    MAP_YAML = os.path.join(PROJECT_ROOT, "original_maps", "map.yaml")
    RACING_CSV = os.path.join(
        PROJECT_ROOT, "original_racinglines", "input_racingline.csv"
    )
    OUTPUT_MAP = os.path.join(PROJECT_ROOT, "mod_maps", "mod_map.png")
    # Yellow for the first and last points because they are the same
    FIRST_LAST_POINT_COLOR = "#f6ff00"
    OTHER_POINTS_COLOR = "#ff0000"  # Red for other points
