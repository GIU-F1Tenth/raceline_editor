import csv
import json
import os

import cv2
import yaml

from extractor.regions import (
    REGION_TYPES,
    ConstantSpeedMultiplierRegion,
    OvertakingAllowedRegion,
    CurvatureRegion,
)


def region_from_dict(data):
    region_type = str(data.get("type", ConstantSpeedMultiplierRegion.REGION_TYPE))
    region_cls = REGION_TYPES.get(region_type)
    if region_cls is None:
        raise ValueError(f"Unsupported region type: {region_type}")
    return region_cls.from_dict(data)


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
                if (
                    abs(point[0] - existing[0]) < 1e-10
                    and abs(point[1] - existing[1]) < 1e-10
                ):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_points.append(point)

        return unique_points
    except Exception as e:
        raise Exception(f"Failed to load raceline: {str(e)}")


def save_raceline_to_csv(
    file_path,
    raceline_points,
):
    try:
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            for point in raceline_points:
                writer.writerow(
                    [f"{point[0]:.7f}", f"{point[1]:.7f}", f"{point[2]:.7f}"]
                )

        return True
    except Exception as e:
        raise Exception(f"Failed to save raceline: {str(e)}")


def region_multiplier_for_index(point_index, regions):
    multiplier = 1.0
    for region in regions:
        if isinstance(region, ConstantSpeedMultiplierRegion) and region.covers_index(
            point_index
        ):
            multiplier *= float(region.multiplier)
    return multiplier


def _binary_flag_for_index(point_index, regions, region_class, attr_name):
    for region in regions:
        if (
            isinstance(region, region_class)
            and getattr(region, attr_name)
            and region.covers_index(point_index)
        ):
            return True
    return False


def can_overtake_for_index(point_index, regions):
    return _binary_flag_for_index(
        point_index, regions, OvertakingAllowedRegion, "can_overtake"
    )


def is_curved_for_index(point_index, regions):
    return _binary_flag_for_index(point_index, regions, CurvatureRegion, "is_curved")


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
            raise ValueError(
                f"Cannot remove region effects for point {index} because multiplier is zero"
            )
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
            "version": 2,
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

        regions = [region_from_dict(region) for region in payload.get("regions", [])]
        return {
            "version": int(payload.get("version", 1)),
            "velocities_applied": bool(payload.get("velocities_applied", False)),
            "regions": regions,
        }
    except Exception as e:
        raise Exception(f"Failed to load region metadata: {str(e)}")


def _binary_flags_for_path(
    base_point_count, regions, region_class, attr_name, output_point_count=None
):
    if base_point_count <= 0:
        return []

    base_flags = [
        _binary_flag_for_index(point_index, regions, region_class, attr_name)
        for point_index in range(base_point_count)
    ]
    if output_point_count is None or output_point_count == base_point_count:
        return base_flags

    if output_point_count <= 1:
        return [base_flags[0]]

    max_base_index = base_point_count - 1
    max_output_index = output_point_count - 1
    return [
        base_flags[int(round(output_index * max_base_index / max_output_index))]
        for output_index in range(output_point_count)
    ]


def overtaking_flags_for_path(base_point_count, regions, output_point_count=None):
    return _binary_flags_for_path(
        base_point_count,
        regions,
        OvertakingAllowedRegion,
        "can_overtake",
        output_point_count,
    )


def curvature_flags_for_path(base_point_count, regions, output_point_count=None):
    return _binary_flags_for_path(
        base_point_count, regions, CurvatureRegion, "is_curved", output_point_count
    )


def _binary_build_export_rows(
    raceline_points,
    regions,
    region_class,
    attr_name,
    spline_points=None,
    use_spline=False,
):
    export_points = spline_points if use_spline and spline_points else raceline_points
    flags = _binary_flags_for_path(
        len(raceline_points),
        regions,
        region_class,
        attr_name,
        output_point_count=len(export_points),
    )
    return [[point[0], point[1], flag] for point, flag in zip(export_points, flags)]


def build_overtaking_export_rows(
    raceline_points, regions, spline_points=None, use_spline=False
):
    return _binary_build_export_rows(
        raceline_points,
        regions,
        OvertakingAllowedRegion,
        "can_overtake",
        spline_points,
        use_spline,
    )


def build_curvature_export_rows(
    raceline_points, regions, spline_points=None, use_spline=False
):
    return _binary_build_export_rows(
        raceline_points,
        regions,
        CurvatureRegion,
        "is_curved",
        spline_points,
        use_spline,
    )


def _binary_save_to_csv(
    file_path,
    raceline_points,
    regions,
    region_class,
    attr_name,
    header,
    spline_points=None,
    use_spline=False,
):
    try:
        rows = _binary_build_export_rows(
            raceline_points,
            regions,
            region_class,
            attr_name,
            spline_points=spline_points,
            use_spline=use_spline,
        )
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for x_value, y_value, flag in rows:
                writer.writerow(
                    [
                        f"{x_value:.7f}",
                        f"{y_value:.7f}",
                        str(bool(flag)).lower(),
                    ]
                )
        return True
    except Exception as e:
        raise Exception(f"Failed to save {header[2]} CSV: {str(e)}")


def save_overtaking_to_csv(
    file_path, raceline_points, regions, spline_points=None, use_spline=False
):
    return _binary_save_to_csv(
        file_path,
        raceline_points,
        regions,
        OvertakingAllowedRegion,
        "can_overtake",
        ["x_m", "y_m", "can_overtake"],
        spline_points,
        use_spline,
    )


def save_curvature_to_csv(
    file_path, raceline_points, regions, spline_points=None, use_spline=False
):
    return _binary_save_to_csv(
        file_path,
        raceline_points,
        regions,
        CurvatureRegion,
        "is_curved",
        ["x_m", "y_m", "is_curved"],
        spline_points,
        use_spline,
    )
