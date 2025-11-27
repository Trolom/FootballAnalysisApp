# Football Match Analysis App

## Project Goal

To create an end-to-end system that automatically analyzes short football match videos using computer vision, providing deep tactical insights through a modern, interactive web interface. The system is designed to accelerate analysis for coaches, analysts, and passionate fans.

## Key Features and Deliverables

The project focuses on achieving a fully functional pipeline that combines front-end usability with high-performance video processing.

### Core Pipeline (Intelligent Video Analysis)

- **Object Detection & Tracking**: Uses YOLOv8 to detect players, referees, goalkeepers, and the ball, combined with ByteTrack to maintain consistent IDs across frames.
- **Team Identification**: Identifies teams by analyzing colors and appearance using CLIP embeddings.
- **Pitch Mapping**: Detects pitch keypoints and landmarks to map player movement and events to real-world field coordinates.
- **Asynchronous Processing**: Handles video uploads ($\le 30$ seconds) via Django and queues processing tasks using Celery/Redis.

### Visualization Outputs

- **Player/Team Detections**: Annotated video showing bounding ellipses, ball control indicators, and team markers.
- **Tactical Board**: A simplified, animated view mapping player positions to a standardized pitch diagram.
- **Voronoi Maps**: Visual representation of team space control and dominance over the field.

## System Architecture

The application follows a standard microservices pattern orchestrated by Docker Compose.

**| Layer | Technology | Purpose |**
|-------|------------|---------|
| Frontend | React + Vite | User interface for file upload, interactive visualization, and HTTP Polling for status updates. |
| Backend/API | Django + DRF (Django REST Framework) | API endpoints, database models (VideoJob), and serving media outputs. |
| Asynchronous Tasks | Celery | Executes the heavy, GPU-accelerated computer vision pipeline. |
| Task Broker/Cache | Redis | Used as the message broker for Celery. |
| Database | PostgreSQL | Persistent storage for job records, users, and Django data. |
| Computer Vision | PyTorch + YOLOv8 + OpenCV | Core modules for detection, tracking, and video I/O. |
| Containerization | Docker + Docker Compose | Orchestrates all services, providing networking and resource isolation. |


## Local Development Setup

### Prerequisites

- Git (for version control)
- Docker (v20.10.0+ required)
- Docker Compose (v2.x is standard)
- NVIDIA GPU & NVIDIA Container Toolkit (Highly recommended for video processing speed; CPU fallback is available).

### Accessing the Application

**| Service | Access Point | Notes |**
| --- | --- |
| Frontend UI | http://localhost:3000 | The main user interface for uploads and viewing status. |
| Django API | http://localhost:8000 | The backend API root (used by the frontend). |
| Worker Logs | docker compose logs -f celery_worker | View real-time progress of video analysis tasks.
