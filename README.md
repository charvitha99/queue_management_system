# QSR Queue Management System
## AI-Based Queue Monitoring and Management

## 1. Project Overview

The QSR (Quick Service Restaurant) Queue Management System is an AI-based application designed to monitor customer queues, track queue sizes, manage service counters, monitor camera status, and analyze queue activity.

The system uses YOLO object detection to detect people in video footage. The detected queue count is sent to a Django REST-style backend, stored in PostgreSQL, and displayed through a React dashboard.

The main objective is to reduce customer waiting congestion, improve counter utilization, and help restaurant staff make better operational decisions.

## 2. Project Objectives

- Monitor customer queues using computer vision.
- Detect people in a video stream using YOLO.
- Update queue counts automatically.
- Generate alerts when queue thresholds are reached.
- Manage service counter status.
- Monitor camera heartbeat and health status.
- Analyze queue activity by hour.
- Recommend opening an available counter when queue congestion occurs.
- Store queue information in PostgreSQL.
- Display queue information through a web dashboard.
- Prepare the system for automatic customer entry and exit counting.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend and computer vision programming |
| Django | Backend framework and API development |
| PostgreSQL | Relational database |
| React | Frontend dashboard |
| Vite | Frontend development server |
| JavaScript | Frontend functionality |
| HTML and CSS | Dashboard structure and styling |
| Ultralytics YOLO | Person detection and tracking |
| ByteTrack | Object tracking across video frames |
| OpenCV | Video processing and display |
| Requests | Sending HTTP requests from the detector |
| Git and GitHub | Version control and source code management |

## 4. System Architecture

The application contains four main layers.

1. **Computer Vision Layer:** Reads the video, detects people, tracks objects, and estimates the number of people in the configured queue region.
2. **Backend Layer:** Django provides APIs for queue status, counters, cameras, recommendations, and analytics.
3. **Database Layer:** PostgreSQL stores queue status, counter information, camera information, and queue history.
4. **Frontend Layer:** React retrieves API data and displays queue information, alerts, camera health, analytics, and counter recommendations.

### Data Flow

```text
Video File / Camera Source
          |
          v
     OpenCV Video
       Processing
          |
          v
     YOLO Detection
          |
          v
    ByteTrack Tracking
          |
          v
   Queue Region Filtering
          |
          v
    Queue Count Update
          |
          v
       Django API
          |
          v
      PostgreSQL
          |
          v
    React Dashboard
          |
          v
 Alerts, Queue Status,
 Analytics and Counters
```

The current computer vision implementation has been tested using a video file. Live physical camera integration and reliable entry/exit counting require separate validation.

## 5. Project Structure

```text
queue_management_system/
│
├── backend/
│   ├── manage.py
│   ├── config/
│   │   └── urls.py
│   └── app/
│       └── api/
│           ├── models.py
│           ├── views.py
│           └── migrations/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── ...
│
├── vision/
│   └── tests/
│       └── queue_detection.py
│
├── videos/
│   └── V4.mp4
│
├── .venv/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

This is the main project structure based on the files used during development. Additional configuration files and migrations may exist in the repository.

## 6. Main Features

### 6.1 AI-Based Queue Detection

- Uses YOLO to detect people in video frames.
- Uses ByteTrack to track detected people across frames.
- Processes the video using OpenCV.
- Filters detections using a configured queue region of interest (ROI).
- Smooths queue-count updates using recent detection history.
- Sends queue-count updates to the Django backend.

The detector currently uses a video file for testing.

### 6.2 Smart Queue Alerts

The backend evaluates the current queue count against a configured threshold.

The current alert threshold is **6 people**.

The dashboard can display queue alert information, including the alert level,