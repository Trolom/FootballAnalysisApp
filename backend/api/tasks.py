# processing/tasks.py
from pathlib import Path
from celery import shared_task
from django.conf import settings
from .models import VideoJob

from processingVideo import (
    read_video, save_video,
    Tracker, TeamAssigner,
    PitchAnnotator, SoccerPitchConfiguration,
    get_model_path,
)

try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    DEVICE = "cpu"


def _out_dir(job_id: int) -> Path:
    p = Path(settings.MEDIA_ROOT) / "outputs" / str(job_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


@shared_task
def process_video_task(job_id: int, produce: list[str]):
    """
    Always:
      - read video
      - run tracking + team assignment  (tracks required for tactical/voronoi, and cheap to have ready)

    Then, conditionally:
      - 'detections'      -> output_video.avi
      - 'pitch_edges'     -> pitch_with_edges.avi
      - 'tactical_board'  -> match_with_tactical_board.avi
      - 'voronoi'         -> match_with_voronoi.avi
    """
    job = VideoJob.objects.get(id=job_id)
    try:
        out_dir = _out_dir(job_id)
        in_path = Path(job.original.path)

        # 1) Read frames once
        video_frames = read_video(str(in_path))

        # 2) ALWAYS do tracking + team assignment (so downstream has tracks)
        tracker = Tracker(get_model_path("player_detection.pt"))
        tracks = tracker.get_object_tracks(video_frames)
        tracker.add_position_to_track(tracks)

        team_assigner = TeamAssigner(device=DEVICE)
        team_assigner.assign_teams(tracks, video_frames)

        outputs = {}

        # 3) Detections overlay, if requested
        if "detections" in produce:
            det_frames = tracker.draw_annotations(video_frames, tracks)
            det_path = out_dir / "output_video.avi"
            save_video(det_frames, str(det_path))
            outputs["detections"] = f"outputs/{job_id}/{det_path.name}"

        # 4) Pitch-based products — run batched pitch model only if needed
        need_pitch = any(k in produce for k in ("pitch_edges", "tactical_board", "voronoi"))
        if need_pitch:
            CONFIG = SoccerPitchConfiguration()
            pitch_ann = PitchAnnotator(
                CONFIG=CONFIG,
                model_path=get_model_path("field_detection.pt"),
            )
            results = pitch_ann.annotate_video_batched(video_frames=video_frames, batch_size=8)

            if "pitch_edges" in produce:
                pd_frames = [pitch_ann.annotate_frame_from_result(f, r) for f, r in zip(video_frames, results)]
                pd_path = out_dir / "pitch_with_edges.avi"
                save_video(pd_frames, str(pd_path))
                outputs["pitch_edges"] = f"outputs/{job_id}/{pd_path.name}"

            if "tactical_board" in produce:
                tb_frames = []
                for i, (f, r) in enumerate(zip(video_frames, results)):
                    tb = pitch_ann.annotate_tactical_board_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5)
                    tb_frames.append(tb)
                tb_path = out_dir / "match_with_tactical_board.avi"
                save_video(tb_frames, str(tb_path))
                outputs["tactical_board"] = f"outputs/{job_id}/{tb_path.name}"

            if "voronoi" in produce:
                vb_frames = []
                for i, (f, r) in enumerate(zip(video_frames, results)):
                    vb = pitch_ann.annotate_voronoi_from_result(f, tracks, i, CONFIG, r, kp_thresh=0.5, vor_step=3)
                    vb_frames.append(vb)
                vb_path = out_dir / "match_with_voronoi.avi"
                save_video(vb_frames, str(vb_path))
                outputs["voronoi"] = f"outputs/{job_id}/{vb_path.name}"

        job.outputs = outputs
        job.status = "done"
        job.error = ""
        job.save()

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.save()
        raise
