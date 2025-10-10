from roboflow import Roboflow
from ultralytics import YOLO
import torch
from pathlib import Path
import shutil
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:128"

# ==== CONFIG (edit this part only) ====
cfg = {
    "api_key": "QbX06VaTIC5Q6ldwuNAc",
    "workspace": "roboflow-jvuqo",
    "project": "football-field-detection-f07vi",
    "version": 12,
    "format": "yolov8",
    "model": "yolov8x-pose.pt",
    "epochs": 500,
    "batch": 8,
    "imgsz": 640,
    "mosaic": 0.0,
    "out_best": "checkpoints/best.pt"
}
# =====================================


def safe_train(model_path, data_yaml, batch, imgsz, epochs, mosaic):
    model = YOLO(model_path)
    while batch >= 1:
        try:
            print(f"🧠 Trying batch={batch}...")
            results = model.train(
                data=data_yaml,
                epochs=epochs,
                batch=batch,
                imgsz=imgsz,
                mosaic=mosaic,
                plots=True
            )
            return results  # success
        except torch.cuda.OutOfMemoryError:
            print(f"⚠️ OOM at batch={batch}, reducing by half...")
            torch.cuda.empty_cache()
            batch //= 2
    raise RuntimeError("Ran out of memory even with batch=1")


print("==> Downloading dataset...")
rf = Roboflow(api_key=cfg["api_key"])
project = rf.workspace(cfg["workspace"]).project(cfg["project"])
dataset = project.version(cfg["version"]).download(cfg["format"])

print("==> Training...")
model = YOLO(cfg["model"])
results = safe_train(cfg["model"], f"{dataset.location}/data.yaml",
                     batch=cfg["batch"], imgsz=cfg["imgsz"],
                     epochs=cfg["epochs"], mosaic=cfg["mosaic"])

# copy best.pt to chosen output
best_pt = Path(results.save_dir) / "weights" / "best.pt"
Path(cfg["out_best"]).parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(best_pt, cfg["out_best"])

print(f"\n✅ Training done!\nBest model copied to: {cfg['out_best']}")