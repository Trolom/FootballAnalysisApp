import os
import torch
import logging
from celery import shared_task
from pathlib import Path
from django.conf import settings
from django.db import transaction
from .models import VideoJob

# === your pipeline modules ===
from processingVideo.utils import read_video, save_video
from processingVideo.tracker import Tracker
from processingVideo.team_assigner import TeamAssigner
from processingVideo.pitch import PitchAnnotator, SoccerPitchConfiguration
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Detect Device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def send_status(job_id, status, progress, outputs=None):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'job_{job_id}',
        {
            "type": "job_update",
            "data": {"status": status, "progress": progress, "outputs": outputs}
        }
    )

def verify_file_exists(file_path):
    """Helper to check if the file was actually written to disk."""
    p = Path(file_path)
    if not p.exists():
        raise RuntimeError(f"FILE SYSTEM ERROR: File was not created at {file_path}. Check permissions or OpenCV codec.")
    if p.stat().st_size == 0:
        raise RuntimeError(f"FILE SYSTEM ERROR: File at {file_path} is empty (0 bytes).")
    print(f"DEBUG: Successfully verified file: {file_path} ({p.stat().st_size} bytes)")

@shared_task
def process_video_task(job_id: int, requested_outputs: list[str]):
    try:
        job = VideoJob.objects.get(id=job_id)
    except VideoJob.DoesNotExist:
        return f"Job {job_id} not found"

    print(f"PyTorch device configured for Celery worker: {DEVICE}")

    try:
        # 1. Initialization & Directory Creation
        CONFIG = SoccerPitchConfiguration()
        player_model_path = "processingVideo/models/player_detection.pt"
        field_model_path  = "processingVideo/models/field_detection.pt"
        
        # Ensure absolute pathing for Docker Volume
        # We use Path(settings.MEDIA_ROOT).resolve() to ensure we aren't using relative paths
        base_media = Path(settings.MEDIA_ROOT).resolve()
        job_output_dir = base_media / "outputs" / str(job.id)
        
        print(f"DEBUG: MEDIA_ROOT is {base_media}")
        print(f"DEBUG: Attempting to create directory: {job_output_dir}")
        
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verification of Directory
        if not job_output_dir.exists():
            raise RuntimeError(f"Could not create or find directory: {job_output_dir}")
        
        send_status(job_id, "processing", 10)

        # 2. Reading Video
        video_frames = read_video(job.original.path)
        send_status(job_id, "processing", 20)

        # 3. Tracking
        tracker = Tracker(player_model_path)
        tracks = tracker.get_object_tracks(video_frames)
        tracker.add_position_to_track(tracks)
        send_status(job_id, "processing", 40)

        # 4. Team Assignment
        team_assigner = TeamAssigner(device=DEVICE)
        team_assigner.assign_teams(tracks, video_frames)
        send_status(job_id, "processing", 50)

        # 5. Pitch Analysis
        pitch_ann = PitchAnnotator(CONFIG=CONFIG, model_path=field_model_path)
        pitch_results = pitch_ann.annotate_video_batched(video_frames=video_frames, batch_size=8)
        send_status(job_id, "processing", 70)

        outputs_map: dict[str, str] = {}

        # 6. Generate Requested Outputs
        # Logic: Save using ABSOLUTE path, store using RELATIVE path
        
        if "detections" in requested_outputs:
            det_frames = tracker.draw_annotations(video_frames, tracks)
            rel_path = f"outputs/{job.id}/detections.mp4"
            abs_path = job_output_dir / "detections.mp4"
            save_video(det_frames, str(abs_path))
            verify_file_exists(abs_path) # Verification step
            outputs_map["detections"] = rel_path

        if "pitch_edges" in requested_outputs:
            pe_frames = [pitch_ann.annotate_frame_from_result(f, r) for f, r in zip(video_frames, pitch_results)]
            rel_path = f"outputs/{job.id}/pitch_edges.mp4"
            abs_path = job_output_dir / "pitch_edges.mp4"
            save_video(pe_frames, str(abs_path))
            verify_file_exists(abs_path)
            outputs_map["pitch_edges"] = rel_path

        if "tactical_board" in requested_outputs:
            tb_frames = [
                pitch_ann.annotate_tactical_board_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5)
                for i, (f, r) in enumerate(zip(video_frames, pitch_results))
            ]
            rel_path = f"outputs/{job.id}/tactical_board.mp4"
            abs_path = job_output_dir / "tactical_board.mp4"
            save_video(tb_frames, str(abs_path))
            verify_file_exists(abs_path)
            outputs_map["tactical_board"] = rel_path

        if "voronoi" in requested_outputs:
            vb_frames = [
                pitch_ann.annotate_voronoi_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5, vor_step=3)
                for i, (f, r) in enumerate(zip(video_frames, pitch_results))
            ]
            rel_path = f"outputs/{job.id}/voronoi.mp4"
            abs_path = job_output_dir / "voronoi.mp4"
            save_video(vb_frames, str(abs_path))
            verify_file_exists(abs_path)
            outputs_map["voronoi"] = rel_path

        if not outputs_map:
            raise RuntimeError("No valid outputs requested/produced")

        # 7. Finalize Job
        with transaction.atomic():
            job.outputs = outputs_map
            job.status = "done"
            job.error = ""
            job.save(update_fields=["outputs", "status", "error"])

        # Notify via Websocket
        send_status(job_id, "done", 100, outputs=outputs_map)

    except Exception as e:
        print(f"CRITICAL ERROR in process_video_task: {e}")
        send_status(job_id, "failed", 0)
        job.status = "failed"
        job.error = str(e)
        job.save(update_fields=["status", "error"])
        raise e