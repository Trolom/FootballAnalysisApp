from .utils import read_video, save_video
from .tracker import Tracker
from .team_assigner import TeamAssigner
from .pitch import PitchAnnotator, SoccerPitchConfiguration

from pathlib import Path

PKG_DIR: Path = Path(__file__).resolve().parent
models_dir: Path = PKG_DIR / "models"
#remove later
STUBS_DIR: Path = PKG_DIR / "stubs"

def get_model_path(name: str):
    return str((models_dir / name).resolve())

#remove later
def get_stub_path(name: str) -> str:
    """Return absolute path to a stub file under stubs/."""
    return str((STUBS_DIR / name).resolve())