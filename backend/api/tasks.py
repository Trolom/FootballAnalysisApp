# tasks.py
from celery import shared_task
from pathlib import Path
from django.conf import settings
from .models import VideoJob

# === your pipeline modules ===
from processingVideo.utils import read_video, save_video
from processingVideo.tracker import Tracker
from processingVideo.team_assigner import TeamAssigner
from processingVideo.pitch import PitchAnnotator, SoccerPitchConfiguration

try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    DEVICE = "cpu"

VALID_PRODUCTS = {"detections", "pitch_edges", "tactical_board", "voronoi"}

@shared_task
def process_video_task(job_id: int, requested_outputs: list[str]):
    job = VideoJob.objects.get(id=job_id)

    print(f"PyTorch device configured for Celery worker: {DEVICE}")

    try:
        # ---- I/O paths ----
        src_path = job.original.path
        out_dir = Path(settings.MEDIA_ROOT) / "outputs" / str(job.id)
        out_dir.mkdir(parents=True, exist_ok=True)

        # ---- models & helpers ----
        device = "cuda" if torch.cuda.is_available() else "cpu"
        player_model_path = "processingVideo/models/player_detection.pt"
        field_model_path  = "processingVideo/models/field_detection.pt"
        CONFIG = SoccerPitchConfiguration()

        # ---- 1) read frames ----
        video_frames = read_video(src_path)

        # ---- 2) tracking + team assignment ----
        tracker = Tracker(player_model_path)
        tracks = tracker.get_object_tracks(video_frames)
        tracker.add_position_to_track(tracks)

        team_assigner = TeamAssigner(device=device)
        team_assigner.assign_teams(tracks, video_frames)

        # ---- 3) pitch model (run once, reused) ----
        pitch_ann = PitchAnnotator(CONFIG=CONFIG, model_path=field_model_path)
        pitch_results = pitch_ann.annotate_video_batched(video_frames=video_frames, batch_size=8)

        outputs_map: dict[str, str] = {}

        # ---- 4) write only what was requested ----
        if "detections" in requested_outputs:
            det_frames = tracker.draw_annotations(video_frames, tracks)  # players/teams/ball
            det_rel = f"outputs/{job.id}/detections.mp4"
            save_video(det_frames, str(Path(settings.MEDIA_ROOT) / det_rel))
            outputs_map["detections"] = det_rel

        if "pitch_edges" in requested_outputs:
            pe_frames = [pitch_ann.annotate_frame_from_result(f, r) for f, r in zip(video_frames, pitch_results)]
            pe_rel = f"outputs/{job.id}/pitch_edges.mp4"
            save_video(pe_frames, str(Path(settings.MEDIA_ROOT) / pe_rel))
            outputs_map["pitch_edges"] = pe_rel

        if "tactical_board" in requested_outputs:
            tb_frames = [
                pitch_ann.annotate_tactical_board_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5)
                for i, (f, r) in enumerate(zip(video_frames, pitch_results))
            ]
            tb_rel = f"outputs/{job.id}/tactical_board.mp4"
            save_video(tb_frames, str(Path(settings.MEDIA_ROOT) / tb_rel))
            outputs_map["tactical_board"] = tb_rel

        if "voronoi" in requested_outputs:
            vb_frames = [
                pitch_ann.annotate_voronoi_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5, vor_step=3)
                for i, (f, r) in enumerate(zip(video_frames, pitch_results))
            ]
            vb_rel = f"outputs/{job.id}/voronoi.mp4"
            save_video(vb_frames, str(Path(settings.MEDIA_ROOT) / vb_rel))
            outputs_map["voronoi"] = vb_rel

        if not outputs_map:
            raise RuntimeError("No valid outputs requested/produced")

        job.outputs = outputs_map
        job.status = "done"
        job.error = ""
        job.save(update_fields=["outputs", "status", "error"])

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.save(update_fields=["status", "error"])
        raise