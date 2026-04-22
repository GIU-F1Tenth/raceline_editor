import csv
import os
import yaml
import cv2


def load_map_from_yaml(yaml_path):
    try:
        with open(yaml_path, 'r') as f:
            map_metadata = yaml.safe_load(f)

        image_path = os.path.join(os.path.dirname(yaml_path), map_metadata['image'])
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
        with open(csv_path, 'r') as f:
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
        with open(file_path, 'w', newline='') as f:
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