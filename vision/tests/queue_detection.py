
import time
from collections import deque
from pathlib import Path

import cv2
import requests
from ultralytics import YOLO


# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIDEO_PATH = PROJECT_ROOT / "videos" / "V4.mp4"
MODEL_PATH = PROJECT_ROOT / "yolo11n.pt"

DEVICE = "cpu"
IMAGE_SIZE = 640
CONFIDENCE = 0.35

# Normalized queue region: x1, y1, x2, y2
QUEUE_REGION = (0.40, 0.35, 0.90, 0.98)

BASE_URL = "http://127.0.0.1:8000/api"
QUEUE_UPDATE_URL = f"{BASE_URL}/queue-status/2/update/"
CAMERA_STATUS_URL = f"{BASE_URL}/cameras/"
CAMERA_ID = 1
HEARTBEAT_URL = f"{BASE_URL}/cameras/{CAMERA_ID}/heartbeat/"

REQUEST_TIMEOUT = 3
QUEUE_UPDATE_INTERVAL = 2.0
CAMERA_CHECK_INTERVAL = 3.0
HEARTBEAT_INTERVAL = 5.0

HISTORY_SIZE = 8
MIN_INSIDE_FRAMES = 5

# Keep disabled until the entrance/exit line is calibrated.
ENABLE_ENTRY_RECORDING = False


def is_camera_enabled():
    """Check whether this camera is enabled in Django."""
    try:
        response = requests.get(
            CAMERA_STATUS_URL,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        cameras = response.json()
        for camera in cameras:
            if camera.get("id") == CAMERA_ID:
                return camera.get("is_enabled") is True

        print(f"Camera ID {CAMERA_ID} was not found in Django.")
        return False

    except requests.RequestException as exc:
        print(f"Camera status check failed: {exc}")
        return False


def send_camera_heartbeat():
    """Report that the detection process is alive."""
    try:
        response = requests.post(
            HEARTBEAT_URL,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            print("Camera heartbeat sent.")
        else:
            print(
                f"Heartbeat failed: HTTP {response.status_code} "
                f"{response.text}"
            )

    except requests.RequestException as exc:
        print(f"Camera heartbeat error: {exc}")


def update_django_queue_count(queue_count):
    """Send the current queue count to Django."""
    try:
        response = requests.patch(
            QUEUE_UPDATE_URL,
            json={"current_queue_count": int(queue_count)},
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            print(
                f"Django queue count updated: {queue_count} "
                f"| HTTP {response.status_code}"
            )
        else:
            print(
                f"Queue update failed: HTTP {response.status_code} "
                f"{response.text}"
            )

    except requests.RequestException as exc:
        print(f"Queue update error: {exc}")


def normalized_region_to_pixels(region, width, height):
    """Convert normalized ROI coordinates to pixel coordinates."""
    x1, y1, x2, y2 = region
    return (
        int(x1 * width),
        int(y1 * height),
        int(x2 * width),
        int(y2 * height),
    )


def point_inside_queue(point, region):
    """Return whether a foot point is inside the queue ROI."""
    x, y = point
    x1, y1, x2, y2 = region
    return x1 <= x <= x2 and y1 <= y <= y2


def main():
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"YOLO model not found: {MODEL_PATH}")

    print("Loading YOLO model...")
    model = YOLO(str(MODEL_PATH))

    capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    print("Video opened. Press Q to quit.")

    queue_history = deque(maxlen=HISTORY_SIZE)
    inside_frames = {}
    last_queue_update = 0.0
    last_camera_check = 0.0
    last_heartbeat = 0.0
    camera_enabled = False

    try:
        while True:
            success, frame = capture.read()

            if not success:
                # Replay the input video when it reaches the end.
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            now = time.monotonic()

            if now - last_camera_check >= CAMERA_CHECK_INTERVAL:
                camera_enabled = is_camera_enabled()
                last_camera_check = now

                if camera_enabled:
                    print("Camera enabled.")
                else:
                    print("Camera disabled or Django unavailable.")

            if camera_enabled and now - last_heartbeat >= HEARTBEAT_INTERVAL:
                send_camera_heartbeat()
                last_heartbeat = now

            height, width = frame.shape[:2]
            roi_pixels = normalized_region_to_pixels(
                QUEUE_REGION,
                width,
                height,
            )

            x1, y1, x2, y2 = roi_pixels

            if camera_enabled:
                results = model.track(
                    frame,
                    persist=True,
                    classes=[0],
                    conf=CONFIDENCE,
                    imgsz=IMAGE_SIZE,
                    device=DEVICE,
                    tracker="bytetrack.yaml",
                    verbose=False,
                )

                current_ids_inside = set()

                for result in results:
                    boxes = result.boxes
                    if boxes is None or boxes.id is None:
                        continue

                    ids = boxes.id.int().cpu().tolist()
                    coordinates = boxes.xyxy.int().cpu().tolist()

                    for track_id, box in zip(ids, coordinates):
                        bx1, by1, bx2, by2 = box
                        foot_point = ((bx1 + bx2) // 2, by2)

                        if point_inside_queue(foot_point, roi_pixels):
                            inside_frames[track_id] = (
                                inside_frames.get(track_id, 0) + 1
                            )
                        else:
                            inside_frames[track_id] = 0

                        if (
                            inside_frames.get(track_id, 0)
                            >= MIN_INSIDE_FRAMES
                        ):
                            current_ids_inside.add(track_id)

                        cv2.rectangle(
                            frame,
                            (bx1, by1),
                            (bx2, by2),
                            (0, 255, 0),
                            2,
                        )
                        cv2.putText(
                            frame,
                            f"ID {track_id}",
                            (bx1, max(by1 - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 255, 0),
                            2,
                        )

                raw_count = len(current_ids_inside)
                queue_history.append(raw_count)

                # Smooth short-lived detection fluctuations.
                stable_count = round(
                    sum(queue_history) / len(queue_history)
                )

                if now - last_queue_update >= QUEUE_UPDATE_INTERVAL:
                    update_django_queue_count(stable_count)
                    last_queue_update = now

            else:
                cv2.putText(
                    frame,
                    "CAMERA DISABLED / API UNAVAILABLE",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            # Draw the queue region and count.
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 0, 0),
                2,
            )

            display_count = (
                round(sum(queue_history) / len(queue_history))
                if queue_history
                else 0
            )

            cv2.putText(
                frame,
                f"Queue Count: {display_count}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

            cv2.imshow("QSR Queue Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
