import csv
import json
import os
from dataclasses import dataclass

import cv2
import yaml


@dataclass
class Region(ABC):
    start_index: int
    end_index: int
    name: str = field(default="", kw_only=True)

    def __post_init__(self):
        start_index = min(self.start_index, self.end_index)
        end_index = max(self.start_index, self.end_index)
        self.start_index = start_index
        self.end_index = end_index

    def covers_index(self, point_index):
        return self.start_index <= point_index <= self.end_index

    @staticmethod
    @abstractmethod
    def from_dict(cls, data):
        raise NotImplementedError

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


@dataclass
class ConstantSpeedMultiplierRegion(Region):
    REGION_TYPE: ClassVar[str] = "speed_multiplier"

    multiplier: float = 1.0

    def to_dict(self):
        return {
            "type": self.REGION_TYPE,
            "name": self.name,
            "start": self.start_index,
            "end": self.end_index,
            "multiplier": float(self.multiplier),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            start_index=int(data["start"]),
            end_index=int(data["end"]),
            multiplier=float(data.get("multiplier", 1.0)),
            name=str(data.get("name", "")),
        )


@dataclass
class OvertakingAllowedRegion(Region):
    REGION_TYPE: ClassVar[str] = "overtaking_allowed"

    can_overtake: bool = field(default=True, kw_only=True)

    def to_dict(self):
        region = self.normalized()
        return {
            "type": self.REGION_TYPE,
            "name": self.name,
            "start": self.start_index,
            "end": self.end_index,
            "can_overtake": bool(self.can_overtake),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            start_index=int(data["start"]),
            end_index=int(data["end"]),
            name=str(data.get("name", "")),
            can_overtake=bool(data.get("can_overtake", True)),
        ).normalized()


def load_map_from_yaml(yaml_path):
    try:
        with open(yaml_path, "r") as f:
            map_metadata = yaml.safe_load(f)

        image_path = os.path.join(os.path.dirname(yaml_path), map_metadata["image"])
        map_image = cv2.imread(image_path)
        if map_image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        map_image = cv2.cvtColor(map_image, cv2.COLOR_BGR2RGB)
        return map_image, map_metadata
    except Exception as e:
        raise Exception(f"Failed to load map: {str(e)}")


def load_raceline_from_csv(csv_path):
    try:
        raceline_points = []
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    x, y = float(row[0]), float(row[1])
                    velocity = float(row[2]) if len(row) > 2 else 1.0
                    raceline_points.append([x, y, velocity])

        if len(raceline_points) < 2:
            raise ValueError("Need at least 2 points for a raceline")

        unique_points = []
        for point in raceline_points:
            is_duplicate = False
            for existing in unique_points:
                if abs(point[0] - existing[0]) < 1e-10 and abs(point[1] - existing[1]) < 1e-10:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_points.append(point)

        return unique_points
    except Exception as e:
        raise Exception(f"Failed to load raceline: {str(e)}")


def save_raceline_to_csv(file_path, raceline_points, spline_points=None, use_spline=False):
    try:
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)

            if not use_spline or not spline_points:
                for point in raceline_points:
                    writer.writerow([f"{point[0]:.7f}", f"{point[1]:.7f}", f"{point[2]:.7f}"])
            else:
                for point in spline_points:
                    writer.writerow([f"{point[0]:.7f}", f"{point[1]:.7f}", f"{point[2]:.7f}"])
        return True
    except Exception as e:
        raise Exception(f"Failed to save raceline: {str(e)}")


def region_multiplier_for_index(point_index, regions):
    multiplier = 1.0
    for region in regions:
        normalized_region = region.normalized()
        if normalized_region.start_index <= point_index <= normalized_region.end_index:
            multiplier *= normalized_region.multiplier
    return multiplier


def apply_regions_to_points(raceline_points, regions):
    return [
        [point[0], point[1], point[2] * region_multiplier_for_index(index, regions)]
        for index, point in enumerate(raceline_points)
    ]


def remove_regions_from_points(raceline_points, regions):
    restored_points = []
    for index, point in enumerate(raceline_points):
        multiplier = region_multiplier_for_index(index, regions)
        if multiplier == 0:
            raise ValueError(f"Cannot remove region effects for point {index} because multiplier is zero")
        restored_points.append([point[0], point[1], point[2] / multiplier])
    return restored_points


def default_metadata_path(csv_path):
    directory = os.path.dirname(csv_path)
    metadata_dir = os.path.join(directory, "metadata")
    file_stem = os.path.splitext(os.path.basename(csv_path))[0]
    return os.path.join(metadata_dir, f"{file_stem}.json")


def find_metadata_path_for_raceline(csv_path):
    candidates = [
        default_metadata_path(csv_path),
        f"{os.path.splitext(csv_path)[0]}.json",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def save_regions_to_json(json_path, regions, velocities_applied=True):
    try:
        directory = os.path.dirname(json_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        payload = {
            "version": 1,
            "velocities_applied": velocities_applied,
            "regions": [region.to_dict() for region in regions],
        }

        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception as e:
        raise Exception(f"Failed to save region metadata: {str(e)}")


def load_regions_from_json(json_path):
    try:
        with open(json_path, "r") as f:
            payload = json.load(f)

        regions = [Region.from_dict(region) for region in payload.get("regions", [])]
        return {
            "version": int(payload.get("version", 1)),
            "velocities_applied": bool(payload.get("velocities_applied", False)),
            "regions": regions,
        }
    except Exception as e:
        raise Exception(f"Failed to load region metadata: {str(e)}")
