import os
from enum import Enum

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DrawerConfig(Enum):
    MAP_YAML = os.path.join(PROJECT_ROOT, "original_maps", "map.yaml")
    RACING_CSV = os.path.join(
        PROJECT_ROOT, "original_racinglines", "input_racingline.csv")
    OUTPUT_MAP = os.path.join(PROJECT_ROOT, "mod_maps", "mod_map.png")
    # Yellow for the first and last points because they are the same
    FIRST_LAST_POINT_COLOR = "#f6ff00"
    OTHER_POINTS_COLOR = "#ff0000"  # Red for other points


class ExtractorConfig(Enum):
    MOD_MAP_PATH = os.path.join(PROJECT_ROOT, "mod_maps", "mod_map.png")
    MAP_YAML = os.path.join(PROJECT_ROOT, "original_maps", "map.yaml")
    RACING_CSV = os.path.join(
        PROJECT_ROOT, "original_racinglines", "input_racingline.csv")
    OUTPUT_CSV = os.path.join(
        PROJECT_ROOT, "output_racinglines", "output_racingline.csv")
    TEMP_RACING_CSV = os.path.join(
        PROJECT_ROOT, "path_extractor", "temp_csvs", "temp_racingline.csv")
    DISCRETIZATION_STEP = 5  # Optional discretization step for the path
    NOT_VELOCITY = -999  # Placeholder for velocity


class State(Enum):  # Node state for pathfinding algorithm
    """
    Enum representing the state of a node in a pathfinding algorithm.
    """
    START = "#11ff00"  # Example hex color for start
    END = "#0a00ff"  # Example hex color for end
    PATH = "#84367b"  # Example hex color for path

    def __str__(self):
        return self.name.lower()
