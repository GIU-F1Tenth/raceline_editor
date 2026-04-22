import numpy as np
from scipy.interpolate import splprep, splev


def generate_spline(raceline_points, smoothness=0.1, resolution=100):
    if len(raceline_points) < 3:
        return None

    points = np.array(raceline_points)
    x_coords = points[:, 0]
    y_coords = points[:, 1]
    v_coords = points[:, 2]

    unique_indices = []
    for i in range(len(x_coords)):
        if i == 0 or (x_coords[i] != x_coords[i-1] or y_coords[i] != y_coords[i-1]):
            unique_indices.append(i)

    if len(unique_indices) < 3:
        return None

    x_coords = x_coords[unique_indices]
    y_coords = y_coords[unique_indices]
    v_coords = v_coords[unique_indices]

    x_coords_closed = np.append(x_coords, x_coords[0])
    y_coords_closed = np.append(y_coords, y_coords[0])
    v_coords_closed = np.append(v_coords, v_coords[0])

    num_points = len(x_coords_closed)
    if num_points >= 4:
        k = min(3, num_points - 1)
        use_periodic = True
    else:
        k = min(2, num_points - 1)
        use_periodic = False

    try:
        if use_periodic and num_points > 4:
            tck, u = splprep([x_coords_closed, y_coords_closed],
                             s=smoothness, per=True, k=k)
        else:
            tck, u = splprep([x_coords_closed, y_coords_closed],
                             s=smoothness, per=False, k=k)
    except Exception:
        k = min(2, num_points - 1)
        tck, u = splprep([x_coords_closed, y_coords_closed],
                         s=smoothness, per=False, k=k)

    new_t = np.linspace(0, 1, resolution)
    spline_coords = splev(new_t, tck)
    v_spline = np.interp(new_t, u, v_coords_closed)

    return list(zip(spline_coords[0], spline_coords[1], v_spline))


def velocity_to_color(velocity, min_velocity, max_velocity):
    v = max(min_velocity, min(max_velocity, velocity))
    t = (v - min_velocity) / (max_velocity - min_velocity) if max_velocity != min_velocity else 0

    if t < 0.5:
        r = int(0 + (255 * (t * 2)))
        g = int(255 - (255 * (t * 2)))
        b = 255
    else:
        r = 255
        g = int(255 - (255 * ((t - 0.5) * 2)))
        b = int(255 * (1 - ((t - 0.5) * 2)))
    return f'#{r:02x}{g:02x}{b:02x}'