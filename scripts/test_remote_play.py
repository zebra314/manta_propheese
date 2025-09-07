from pathlib import Path
from camera import Camera

if __name__ == "__main__":
    camera = Camera()

    raw_file_path = Path(__file__).parent.parent / "assets" / "record.raw"
    camera.remote_play(str(raw_file_path))
