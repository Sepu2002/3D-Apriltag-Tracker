# 3D AprilTag Tracker

Real-time 3D position tracking of [AprilTag](https://april.eecs.umich.edu/software/apriltag) fiducial markers with a regular USB webcam, built with Python and OpenCV.

The program finds AprilTags in the camera feed and works out each tag's **3D position and orientation** relative to the camera by solving the Perspective-n-Point (PnP) problem. It then:

- draws an augmented-reality cube and coordinate axes on top of each tag,
- measures the real-world distance between pairs of tags,
- plots every tag on a live 3D map, including a short trail of where each tag has been.

I built it as the final project for a *Perception Systems* (Sistemas de Percepción) course.

<!-- Tip: add a screenshot or GIF of the dashboard here, e.g. ![Dashboard](docs/dashboard.png) -->

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Printing the tags](#printing-the-tags)
- [Usage](#usage)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Building a standalone .exe](#building-a-standalone-exe)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)

---

## Features

The repo contains two programs:

### `apriltag_dash.py`: three-panel dashboard (recommended)

A single window with three panels side by side:

| Panel | What it shows |
|---|---|
| **Augmented Reality + Axes** | Camera feed with a wireframe cube and RGB coordinate axes (X = red, Y = green, Z = blue) on each tag, plus its ID and distance from the camera |
| **Raw Computer Vision** | The grayscale image the detector actually sees, with detected tag outlines |
| **3D Trajectory Map** | Live 3D plot of the camera and every tag, with a yellow trail of each tag's last 20 positions and dashed cyan lines between tags |

### `apriltag_tracker.py`: simple tracker

A simpler version with two windows:

- An OpenCV window with an AR cube on each tag and a yellow line between every pair of tags, labeled with the distance in centimeters.
- A separate Matplotlib window with an interactive 3D plot of the tag positions. You can rotate it with the mouse.

---

## Requirements

- **Windows 10/11.** The camera picker uses DirectShow through [`pygrabber`](https://github.com/andreasjansson/pygrabber), which only works on Windows. See [Troubleshooting](#running-on-linux--macos) for running on other systems.
- **Python 3.10 or newer.** It was developed and tested on Python 3.12.
- A **USB webcam** or built-in camera.
- One or more printed **AprilTags from the `tag36h11` family** (see [Printing the tags](#printing-the-tags)).

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Sepu2002/3D-Apriltag-Tracker.git
```

```bash
cd 3D-Apriltag-Tracker
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

In PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

In Command Prompt (cmd), run `venv\Scripts\activate.bat` instead.

> If PowerShell says running scripts is disabled, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

This installs OpenCV (the contrib build, which includes the ArUco/AprilTag module), NumPy, Matplotlib and pygrabber.

---

## Printing the tags

The program expects **AprilTag `36h11`** markers. Two ways to get them:

**Option A: generate them with OpenCV** (already installed in your venv):

```python
import cv2

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
for tag_id in range(4):                      # IDs 0, 1, 2, 3
    img = cv2.aruco.generateImageMarker(dictionary, tag_id, 600)
    img = cv2.copyMakeBorder(img, 100, 100, 100, 100,
                             cv2.BORDER_CONSTANT, value=255)  # white margin
    cv2.imwrite(f"tag36h11_{tag_id}.png", img)
```

**Option B: download them** from the official [AprilRobotics/apriltag-imgs](https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11) repository. Those images are tiny (10×10 px), so scale them up with *nearest-neighbor* interpolation so the edges stay sharp.

### Size matters

Distances are only correct if the program knows how big your tags really are. By default it assumes **5 cm**, measured along the **outer edge of the black square** (not counting the white margin).

1. Print the tags. Disable "fit to page" scaling, or just print and measure.
2. Measure the black square with a ruler.
3. If it isn't 5 cm, change `TAG_SIZE` in the script (see [Configuration](#configuration)).

Keep a white border around each tag and glue it to something flat. A bent tag gives a wobbly pose.

---

## Usage

With the virtual environment activated, run the dashboard:

```bash
python apriltag_dash.py
```

or the simple tracker:

```bash
python apriltag_tracker.py
```

When the program starts it lists the cameras it found:

```
--- Available Cameras ---
[0] Integrated Webcam
[1] USB Camera

Enter camera index number:
```

Type the number of the camera you want and press **Enter**. Hold one or more tags in front of the camera.

- Show **two or more tags** to see distance measurements between them.
- Press **`q`** with the video window focused to quit.

### Using the prebuilt .exe

If a `apriltag_dash.exe` is attached to this repository's [Releases](https://github.com/Sepu2002/3D-Apriltag-Tracker/releases) page, you can download it and double-click it. You don't need to install Python. A console window opens for the camera selection, then the dashboard appears.

> Windows SmartScreen may warn about an unrecognized app because the exe isn't signed. Click **More info → Run anyway**.

---

## Configuration

Settings are constants at the top of each script:

| Constant | Default | Meaning |
|---|---|---|
| `TAG_SIZE` | `0.05` | Side length of the black square of your printed tag, **in meters** |
| `FAMILY` | `cv2.aruco.DICT_APRILTAG_36h11` | Tag family to detect. Other OpenCV dictionaries such as `DICT_APRILTAG_25h9` or `DICT_4X4_50` also work. |
| `TRAIL_LENGTH` | `20` | *(dashboard only)* How many past positions to draw in each tag's trail |

The axis limits of the 3D plot (`ax.set_xlim`, `ax.set_ylim`, `ax.set_zlim`) are in meters. Widen them if your tags go out of view on the map. The dashboard shows ±20 cm sideways and up to 50 cm deep. The simple tracker shows ±50 cm and up to 1.5 m.

### Camera calibration (optional, for better accuracy)

To keep setup simple, the camera's intrinsic matrix is **estimated** from the image resolution (focal length ≈ image width, optical center at the middle of the image), and lens distortion is assumed to be zero. This is enough for a demo, but distances can be off by several percent depending on your webcam.

For accurate measurements, calibrate your camera with OpenCV's [camera calibration tutorial](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html). Then replace the values returned by `get_camera_matrix()` with your real camera matrix `K` and distortion coefficients `D`.

---

## How it works

1. **Capture and grayscale:** each frame is converted to grayscale, since color doesn't matter for geometry.
2. **Detection:** OpenCV's `ArucoDetector` uses adaptive thresholding, finds quadrilateral contours, unwarps each candidate with a homography and decodes its bits against the `36h11` dictionary. The result is each tag's ID and its 4 corner pixels.
3. **Pose estimation (PnP):** we know the real 3D coordinates of the 4 corners (a square of side `TAG_SIZE`) and where they appear in the image. `cv2.solvePnP` uses the pinhole camera model to find the rotation `rvec` and translation `tvec` that best explain that projection, by minimizing the reprojection error.
4. **Visualization:** the 3D cube corners are projected back onto the image with `cv2.projectPoints` to draw the AR overlay. `tvec` gives each tag's position in meters, which is plotted on the 3D map. The distance between two tags is `‖tvec₁ − tvec₂‖`.
5. **Tracking:** the dashboard keeps a fixed-length `deque` of recent positions for each tag and draws it as a trail.

On the 3D map the camera sits at the origin. Camera coordinates (Z forward, Y down) are remapped so that the plot shows **X = left/right, Y = depth, Z = height**.

There's a longer explanation (in Spanish) of the theory behind fiducial markers, the detection pipeline and the PnP problem in [`explicacion.md`](explicacion.md) and [`ExplicaciónSistema.pdf`](ExplicaciónSistema.pdf).

---

## Building a standalone .exe

You can package the dashboard into a single executable with [PyInstaller](https://pyinstaller.org/). The repo includes the spec file used to build it.

```bash
pip install pyinstaller
```

```bash
pyinstaller apriltag_dash.spec
```

The executable is written to `dist/apriltag_dash.exe`. It's around 80 MB, so don't commit it to the repository. Upload it as an asset on a [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) instead.

---

## Troubleshooting

**"No module named 'cv2.aruco'" or `ArucoDetector` not found**
You probably have the plain `opencv-python` package, or an old OpenCV version. Run:
```bash
pip uninstall opencv-python opencv-contrib-python
```
```bash
pip install -r requirements.txt
```
The code needs OpenCV **4.7 or newer**.

**The camera list is empty, or the window stays black**
Close any other app using the camera (Teams, Zoom, OBS, the browser). Also check *Windows Settings → Privacy & security → Camera* and make sure desktop apps are allowed to use it.

**Tags aren't detected**
Improve the lighting, avoid glare on glossy paper, keep the white border around the tag, and make sure you printed the `36h11` family. Tags that are very small in the frame, or seen at a steep angle, are harder to detect.

**Distances are wrong**
Check that `TAG_SIZE` matches the measured black square in meters. For better accuracy, calibrate your camera (see [Camera calibration](#camera-calibration-optional-for-better-accuracy)).

**The pose flips or jitters**
This is a known ambiguity of single-tag PnP when a small tag is seen almost head-on. Larger tags, better lighting and a calibrated camera all help.

### Running on Linux / macOS

`pygrabber` and the `cv2.CAP_DSHOW` backend only exist on Windows. To run elsewhere:

1. Remove `pygrabber` from `requirements.txt` and delete the `from pygrabber...` import.
2. Replace `get_available_cameras()` with something that just returns a camera index, e.g. `return int(input("Camera index (usually 0): "))`.
3. Change `cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)` to `cv2.VideoCapture(cam_idx)`.

---

## Project structure

```
3D-Apriltag-Tracker/
├── apriltag_dash.py         # Three-panel dashboard (AR + raw CV + 3D trajectory map)
├── apriltag_tracker.py      # Simple tracker (AR window + separate 3D plot)
├── apriltag_dash.spec       # PyInstaller build spec for the dashboard
├── requirements.txt         # Python dependencies
├── explicacion.md           # Theory write-up (Spanish)
├── explicacion.html         # Same write-up, rendered as HTML
└── ExplicaciónSistema.pdf   # Same write-up, as a PDF
```

---

## Acknowledgements

- [AprilTag](https://april.eecs.umich.edu/software/apriltag) by the APRIL Robotics Laboratory, University of Michigan
- [OpenCV](https://opencv.org/) ArUco module for detection and pose estimation
- [pygrabber](https://github.com/andreasjansson/pygrabber) for listing DirectShow cameras by name
