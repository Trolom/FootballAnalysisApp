from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from moviepy.editor import VideoFileClip
from .models import VideoJob
from .serializers import VideoJobSerializer
from .tasks import process_video_task
import os
from pathlib import Path
from django.http import FileResponse, Http404, StreamingHttpResponse
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO

MAX_SECONDS = 30
VALID_PRODUCTS = {"detections", "pitch_edges", "tactical_board", "voronoi"}

class VideoJobViewSet(viewsets.ModelViewSet):
    queryset = VideoJob.objects.order_by("-id")
    serializer_class = VideoJobSerializer

    def create(self, request, *args, **kwargs):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "file required"}, status=400)

        # read desired outputs from query (?produce=...)
        raw = request.query_params.get("produce", "") or ""
        selected = {s.strip() for s in raw.split(",") if s.strip()}
        if not selected:
            selected = {"detections"}  # sensible default
        unknown = selected - VALID_PRODUCTS
        if unknown:
            return Response({"detail": f"invalid produce values: {sorted(unknown)}"}, status=400)

        job = VideoJob.objects.create(original=f, status="pending")

        # 30s validation
        try:
            with VideoFileClip(job.original.path) as clip:
                if clip.duration > MAX_SECONDS + 0.01:
                    p = job.original.path
                    job.delete()
                    try: os.remove(p)
                    except Exception: pass
                    return Response({"detail": "video longer than 30 seconds"}, status=400)
        except Exception as e:
            job.delete()
            return Response({"detail": f"could not read video: {e}"}, status=400)

        job.status = "processing"
        job.save()

        # pass the selection to Celery
        # process_video_task.delay(job.id, sorted(list(selected)))
        return Response(VideoJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        job = self.get_object()
        base = request.build_absolute_uri(settings.MEDIA_URL)
        def absify(x):
            if isinstance(x, str): return base + x
            if isinstance(x, dict): return {k: absify(v) for k, v in x.items()}
            if isinstance(x, list): return [absify(i) for i in x]
            return x
        return Response(absify(job.outputs or {}))


    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):

        job = self.get_object()
        if job.status != "done" or not job.outputs:
            raise Http404("Outputs not ready")

        # normalize job.outputs to dict of key -> relative path (string)
        outputs = job.outputs
        rel_paths = {}

        def collect(key, val):
            if isinstance(val, str):
                rel_paths[key] = val
            elif isinstance(val, dict):
                for k, v in val.items():
                    collect(f"{key}.{k}", v)

        for k, v in outputs.items():
            collect(k, v)

        which = request.query_params.get("which", "")
        selected = [w.strip() for w in which.split(",") if w.strip()]
        if not selected:
            # if none specified, select all top-level keys
            selected = list(rel_paths.keys())

        # resolve absolute paths
        base = Path(settings.MEDIA_ROOT)
        picked = []
        for key in selected:
            if key not in rel_paths:
                continue
            abs_path = base / rel_paths[key]
            if not abs_path.exists():
                continue
            picked.append((key, abs_path))

        if not picked:
            raise Http404("No matching outputs found")

        cleanup = request.query_params.get("cleanup") == "1"

        # single file -> direct FileResponse with attachment
        if len(picked) == 1:
            key, abs_path = picked[0]
            resp = FileResponse(open(abs_path, "rb"), as_attachment=True, filename=abs_path.name)
            # optional cleanup AFTER preparing response (best-effort)
            if cleanup:
                try:
                    abs_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return resp

        # multiple -> build a zip in memory and stream
        zip_name = f"job-{job.id}-outputs.zip"

        def make_zip_bytes():
            bio = BytesIO()
            with ZipFile(bio, mode="w", compression=ZIP_DEFLATED) as zf:
                for key, abs_path in picked:
                    # store under a tidy name in the zip
                    arcname = abs_path.name
                    zf.write(abs_path, arcname=arcname)
            bio.seek(0)
            return bio

        bio = make_zip_bytes()
        resp = StreamingHttpResponse(bio, content_type="application/zip")
        resp["Content-Disposition"] = f'attachment; filename="{zip_name}"'

        if cleanup:
            for _, abs_path in picked:
                try:
                    abs_path.unlink(missing_ok=True)
                except Exception:
                    pass

        return resp