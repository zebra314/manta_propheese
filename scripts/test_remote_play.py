from pathlib import Path
from camera_handler import CameraHandler
from logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    camera_handler = CameraHandler()

    raw_file_path = Path(__file__).parent / "assets" / "record.raw"
    camera_handler.remote_play(str(raw_file_path))
