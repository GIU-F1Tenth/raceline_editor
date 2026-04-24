# F1Tenth Raceline Editor

A comprehensive GUI tool for editing and modifying F1Tenth racing lines interactively with real-time spline visualization.

## 🚀 Quick Start

```bash
python main.py
```

The GUI editor will launch with default map and raceline files loaded.

## ✨ Features

### 🖥️ GUI Editor

- **Interactive Point Editing**: Click, drag, and modify raceline points in real-time
- **Real-time Spline Visualization**: See smooth cubic spline curves as you edit
- **Region Control for Velocity and Overtaking**: Edit individual point or region velocities and overtaking allowance with dedicated controls
- **Visual Map Overlay**: Work directly on top of track maps
- **Zoom & Pan**: Navigate large maps with mouse wheel zoom and pan
- **Flexible Point Management**: Add, delete, and reorder raceline points
- **Save/Load**: Export and import raceline CSV files

## 🛠️ Installation

### Prerequisites

- Python 3.6+
- pip (Python package manager)
- tkinter (usually included with Python)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/GIU-F1Tenth/raceline_editor.git
cd raceline_editor
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Launch the GUI:

```bash
python main.py
```

## 🎮 GUI Usage Guide

### Getting Started

1. **Launch**: Run `python main.py`
2. **Load Data**: The application automatically loads default map and raceline
3. **Start Editing**: Click on points to select and modify them

### Core Features

#### 🎯 Point Selection & Editing

- **Select Points**: Click near any raceline point to select it
- **Drag Points**: Click and drag selected points to new positions
- **Point Information**: View coordinates and velocity in the right panel

#### ⚡ Velocity Editing

- **Manual Entry**: Type velocity values in the input field
- **Quick Buttons**: Use preset velocity buttons (0.5, 1.0, 1.5, 2.0, 3.0)
- **Visual Feedback**: Selected points show velocity labels

#### 📍 Coordinate Editing

- **Precise Control**: Enter exact X,Y coordinates manually
- **Real-time Updates**: Changes reflect immediately on the map

#### ➕ Adding/Removing Points

- **Add Points**: Click "Add Point" button, then click on map
- **Delete Points**: Select a point and press Delete key or click "Delete Point"
- **Minimum Points**: Maintains at least 3 points for valid racelines

#### 🎨 Spline Visualization

- **Real-time Splines**: Green curves show smooth interpolated paths
- **Adjustable Smoothness**: Control spline smoothness (0.01 - 1.0)
- **Variable Resolution**: Adjust spline point density (50 - 500 points)

#### 🔍 Navigation

- **Zoom**: Mouse wheel to zoom in/out
- **Pan**: Automatic centering and manual offset adjustment
- **Reset View**: Button to restore default view

#### 💾 File Operations

- **Save**: Ctrl+S or "Save Raceline" button
- **Load**: Ctrl+O or "Load Raceline" button
- **Auto-format**: Saves with proper precision (7 decimal places)

## 📊 Data Format

### CSV Structure

Raceline files should be in CSV format with `x_coordinate`, `y_coordinate`, and `velocity` columns:

```csv
x_coordinate,y_coordinate,velocity
-0.2430698,0.2290873,2.0676071
-0.4212379,0.1221564,2.0178379
0.1523456,0.5678901,1.9234567
```

### YAML Map Metadata

Map metadata files should contain:

```yaml
image: map.png
resolution: 0.05
origin: [-7.5, -5.0, 0.0]
occupied_thresh: 0.65
free_thresh: 0.196
negate: 0
```

## 📝 License

[MIT](./LICENSE)

## 👥 Authors & Maintainers

Fam Shihata - fam@awadlouis.com  
GitHub: [FamALouiz](https://github.com/FamALouiz)
