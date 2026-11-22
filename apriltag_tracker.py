import cv2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from itertools import combinations
from pygrabber.dshow_graph import FilterGraph

# --- CONFIGURATION ---
TAG_SIZE = 0.05  # 5cm physical size
FAMILY = cv2.aruco.DICT_APRILTAG_36h11

def get_available_cameras():
    """Lists USB cameras and asks user to select one."""
    graph = FilterGraph()
    devices = graph.get_input_devices()
    print("\n--- Available Cameras ---")
    for i, name in enumerate(devices):
        print(f"[{i}] {name}")
    
    while True:
        try:
            selection = input("\nEnter camera index number: ")
            index = int(selection)
            if 0 <= index < len(devices):
                return index
        except ValueError: pass
        print("Invalid selection.")

def get_camera_matrix(width, height):
    """Approximates Intrinsic Matrix (Focal length & Center)."""
    focal_length = width 
    center_x = width / 2
    center_y = height / 2
    # The Matrix K
    return np.array([
        [focal_length, 0, center_x],
        [0, focal_length, center_y],
        [0, 0, 1]
    ], dtype=np.float32), np.zeros((4, 1))

def draw_cube(img, camera_matrix, dist_coeffs, rvec, tvec, size):
    """
    Draws a 3D cube.
    ORIGIN: Center of the AprilTag surface.
    PROJECTION: Extrudes 'forward' (Negative Z) out of the tag.
    """
    half = size / 2
    
    # Define 3D coordinates relative to the Tag Center (0,0,0)
    # Z = 0 is the paper surface
    # Z = -size is sticking out of the paper (towards camera)
    points_3d = np.float32([
        # Base Face (On the tag surface)
        [-half, -half, 0],    # Bottom-Left
        [half, -half, 0],     # Bottom-Right
        [half, half, 0],      # Top-Right
        [-half, half, 0],     # Top-Left
        
        # Top Face (Extruded out)
        [-half, -half, -size], 
        [half, -half, -size], 
        [half, half, -size], 
        [-half, half, -size] 
    ])
    
    # Project 3D points -> 2D pixels
    img_points, _ = cv2.projectPoints(points_3d, rvec, tvec, camera_matrix, dist_coeffs)
    img_points = np.int32(img_points).reshape(-1, 2)
    
    # Draw The Base (Green - On the paper)
    cv2.polylines(img, [img_points[:4]], True, (0, 255, 0), 2) 
    
    # Draw The Pillars (Blue - Connecting base to top)
    for i, j in zip(range(4), range(4, 8)):
        cv2.line(img, tuple(img_points[i]), tuple(img_points[j]), (255, 0, 0), 2) 
        
    # Draw The Top (Red - The floating face)
    cv2.polylines(img, [img_points[4:]], True, (0, 0, 255), 2) 
    
    return img

def draw_link(img, camera_matrix, dist_coeffs, tvec1, tvec2, id1, id2):
    """Visualizes distance between two detected tags."""
    zero = np.zeros((3, 1), dtype=np.float32)
    
    # Project the center points (tvecs) to screen
    p1_img, _ = cv2.projectPoints(tvec1, zero, zero, camera_matrix, dist_coeffs)
    p2_img, _ = cv2.projectPoints(tvec2, zero, zero, camera_matrix, dist_coeffs)
    
    p1 = tuple(np.int32(p1_img).reshape(2))
    p2 = tuple(np.int32(p2_img).reshape(2))
    
    # Draw yellow line
    cv2.line(img, p1, p2, (0, 255, 255), 2)
    
    # Euclidean Distance Math: sqrt((x2-x1)^2 + ...)
    dist = np.linalg.norm(tvec1 - tvec2)
    
    mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
    cv2.putText(img, f"{dist*100:.1f}cm", mid, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

def main():
    # 1. SETUP
    cam_idx = get_available_cameras()
    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    
    ret, frame = cap.read()
    if not ret: return
    h, w = frame.shape[:2]
    K, D = get_camera_matrix(w, h)

    # 2. INIT DETECTOR
    aruco_dict = cv2.aruco.getPredefinedDictionary(FAMILY)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    # 3. INIT PLOTTING
    plt.ion()
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection='3d')

    # Define the physical tag corners (for PnP)
    half_tag = TAG_SIZE / 2
    # Z=0 because the tag is flat
    obj_points = np.array([
        [-half_tag, half_tag, 0], [half_tag, half_tag, 0], 
        [half_tag, -half_tag, 0], [-half_tag, -half_tag, 0]
    ], dtype=np.float32)

    print("Running... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)
        
        detected_tags = {} # Store found tags this frame

        # --- PROCESSING LOOP ---
        if ids is not None:
            ids = ids.flatten()
            for i, tag_id in enumerate(ids):
                # SOLVE PNP: The "Magic" Step
                success, rvec, tvec = cv2.solvePnP(obj_points, corners[i], K, D)
                
                if success:
                    detected_tags[tag_id] = tvec
                    # Visual: Draw the updated cube
                    draw_cube(frame, K, D, rvec, tvec, TAG_SIZE)
                    # Visual: Draw the tag outline
                    cv2.aruco.drawDetectedMarkers(frame, corners)

        # --- RELATIONSHIP LOOP ---
        pairs = list(combinations(detected_tags.keys(), 2))
        for id1, id2 in pairs:
            draw_link(frame, K, D, detected_tags[id1], detected_tags[id2], id1, id2)

        # --- MAPPING LOOP ---
        ax.clear()
        # Plot Camera at (0,0,0)
        ax.scatter([0], [0], [0], c='k', marker='^', s=100, label="Webcam")
        
        # Plot Tags
        for tag_id, tvec in detected_tags.items():
            x, y, z = tvec[0][0], tvec[1][0], tvec[2][0]
            # Mapping Note: We swap Y and Z for plotting because 
            # In 3D plots, 'Z' is up. In cameras, 'Y' is down/up.
            ax.scatter(x, z, y, s=50, label=f"ID {tag_id}") 
            ax.text(x, z, y, f"ID {tag_id}")

        # Draw Lines in 3D Plot
        for id1, id2 in pairs:
            p1 = detected_tags[id1]
            p2 = detected_tags[id2]
            ax.plot([p1[0][0], p2[0][0]], [p1[2][0], p2[2][0]], [p1[1][0], p2[1][0]], c='blue', alpha=0.5)

        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(0, 1.5) # Depth axis
        ax.set_zlim(-0.5, 0.5)
        ax.set_xlabel('X (Right/Left)')
        ax.set_ylabel('Z (Depth)')
        ax.set_zlabel('Y (Up/Down)')
        
        plt.draw()
        plt.pause(0.001)

        cv2.imshow('AprilTag 3D', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    plt.close()

if __name__ == "__main__":
    main()