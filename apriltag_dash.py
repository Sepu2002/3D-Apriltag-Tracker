import cv2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from itertools import combinations
from pygrabber.dshow_graph import FilterGraph
from collections import deque

# --- CONFIGURATION ---
TAG_SIZE = 0.05      # 5cm
TRAIL_LENGTH = 20    # How many past frames to remember
FAMILY = cv2.aruco.DICT_APRILTAG_36h11

def get_available_cameras():
    graph = FilterGraph()
    devices = graph.get_input_devices()
    print("\n--- Available Cameras ---")
    for i, name in enumerate(devices):
        print(f"[{i}] {name}")
    while True:
        try:
            selection = input("\nEnter camera index number: ")
            index = int(selection)
            if 0 <= index < len(devices): return index
        except ValueError: pass

def get_camera_matrix(width, height):
    focal_length = width 
    center_x = width / 2
    center_y = height / 2
    return np.array([[focal_length, 0, center_x], [0, focal_length, center_y], [0, 0, 1]], dtype=np.float32), np.zeros((4, 1))

def draw_cube_and_axes(img, rvec, tvec, K, D, size):
    """Draws wireframe cube AND the coordinate axes (RGB)."""
    # 1. Draw Axes (Red=X, Green=Y, Blue=Z)
    cv2.drawFrameAxes(img, K, D, rvec, tvec, size/1.5, 2)
    
    # 2. Draw Cube (Projecting Out)
    half = size / 2
    base = np.array([[-half, -half, 0], [half, -half, 0], [half, half, 0], [-half, half, 0]], dtype=np.float32)
    top = np.array([[-half, -half, size], [half, -half, size], [half, half, size], [-half, half, size]], dtype=np.float32)
    points_3d = np.vstack((base, top))
    img_points, _ = cv2.projectPoints(points_3d, rvec, tvec, K, D)
    pts = np.int32(img_points).reshape(-1, 2)
    
    cv2.polylines(img, [pts[:4]], True, (0, 255, 0), 1) # Base (Thin)
    for i in range(4):
        cv2.line(img, tuple(pts[i]), tuple(pts[i+4]), (255, 0, 0), 1) # Pillars (Thin)
    cv2.polylines(img, [pts[4:]], True, (0, 0, 255), 1) # Top (Thin)

def draw_info_text(img, tvec, rvec, K, D, tag_id):
    center_point, _ = cv2.projectPoints(np.array([[0.,0.,0.]]), rvec, tvec, K, D)
    center = tuple(np.int32(center_point).reshape(2))
    dist = np.linalg.norm(tvec)
    text = f"ID:{tag_id} Z:{dist*100:.0f}cm"
    
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
    cv2.rectangle(img, (center[0], center[1]-20), (center[0]+w, center[1]), (0,0,0), -1)
    cv2.putText(img, text, (center[0], center[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

def fig_to_numpy(fig):
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
    buf.shape = (w, h, 4)
    return np.roll(buf, 3, axis=2)[:, :, :3]

def main():
    cam_idx = get_available_cameras()
    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    
    ret, frame = cap.read()
    if not ret: return
    h, w = frame.shape[:2]
    K, D = get_camera_matrix(w, h)

    aruco_dict = cv2.aruco.getPredefinedDictionary(FAMILY)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    # HISTORY STORAGE: Dictionary of Deques { id : deque([(x,y,z), ...]) }
    tag_history = {}

    plt.style.use('dark_background')
    fig = plt.figure(figsize=(5, 5), dpi=100)
    ax = fig.add_subplot(111, projection='3d')

    half = TAG_SIZE / 2
    obj_points = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]], dtype=np.float32)

    print("\n--- LEVEL 3 DASHBOARD ---")
    print("Features: Trajectory Tracking, Axis Visualization, 3-Panel View")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)
        
        detected_tags = {}
        gray_display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) # For middle panel

        if ids is not None:
            ids = ids.flatten()
            cv2.aruco.drawDetectedMarkers(gray_display, corners, borderColor=(0, 255, 0))
            
            for i, tag_id in enumerate(ids):
                success, rvec, tvec = cv2.solvePnP(obj_points, corners[i], K, D)
                if success:
                    detected_tags[tag_id] = tvec
                    
                    # 1. Update History
                    if tag_id not in tag_history:
                        tag_history[tag_id] = deque(maxlen=TRAIL_LENGTH)
                    tag_history[tag_id].append(tvec)

                    # 2. Draw Advanced Visuals
                    draw_cube_and_axes(frame, rvec, tvec, K, D, TAG_SIZE)
                    draw_info_text(frame, tvec, rvec, K, D, tag_id)

        # Draw Lines between current tags
        pairs = list(combinations(detected_tags.keys(), 2))

        # --- UPDATE 3D MAP ---
        ax.clear()
        ax.set_facecolor((0.1, 0.1, 0.1))
        ax.scatter([0], [0], [0], c='white', marker='^', s=50, label="CAM")
        
        # Plot Current Positions
        for tag_id, tvec in detected_tags.items():
            x, y, z = tvec[0][0], tvec[1][0], tvec[2][0]
            ax.scatter(x, z, -y, s=100, c='red', marker='o') 
            ax.text(x, z, -y, f"ID{tag_id}", color='white', fontsize=9)

        # Plot Trajectories (The "Snake")
        for tag_id, history in tag_history.items():
            if len(history) > 1:
                # Convert deque to numpy array for plotting
                hist_arr = np.array(history)
                # Xs, Zs (depth), -Ys (height)
                ax.plot(hist_arr[:,0,0], hist_arr[:,2,0], -hist_arr[:,1,0], c='yellow', linewidth=1, alpha=0.6)

        # Plot Relationship Lines
        for id1, id2 in pairs:
            p1, p2 = detected_tags[id1], detected_tags[id2]
            ax.plot([p1[0][0], p2[0][0]], [p1[2][0], p2[2][0]], [-p1[1][0], -p2[1][0]], c='cyan', linewidth=2, linestyle='--')

        ax.set_xlim(-0.2, 0.2)
        ax.set_ylim(0, 0.5)
        ax.set_zlim(-0.2, 0.2)
        ax.set_xlabel('X')
        ax.set_ylabel('Depth')
        ax.set_zlabel('Height')
        # Remove grid for cleaner look (optional)
        #ax.grid(False) 
        # Hide pane backgrounds
        ax.xaxis.set_pane_color((0.1, 0.1, 0.1, 1.0))
        ax.yaxis.set_pane_color((0.1, 0.1, 0.1, 1.0))
        ax.zaxis.set_pane_color((0.1, 0.1, 0.1, 1.0))

        # --- COMPOSITE ---
        plot_img = fig_to_numpy(fig)
        plot_h, plot_w = plot_img.shape[:2]
        scale = h / plot_h
        plot_img_resized = cv2.resize(plot_img, (int(plot_w * scale), h))
        
        dashboard = cv2.hconcat([frame, gray_display, plot_img_resized])
        
        # Overlay Titles
        cv2.putText(dashboard, "Augmented Reality + Axes", (10, 30), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (100, 0, 255), 2)
        cv2.putText(dashboard, "Raw Computer Vision", (w + 10, 30), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (100, 0, 255), 2)
        cv2.putText(dashboard, "3D Trajectory Map", (w*2 + 10, 30), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (100, 0, 255), 2)
        
        cv2.imshow('AprilTag Ultimate Dashboard', dashboard)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
    plt.close()

if __name__ == "__main__":
    main()