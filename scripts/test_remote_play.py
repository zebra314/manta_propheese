from camera_handler import CameraHandler
from logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    camera_handler = CameraHandler()
    # camera_handler.live()
    camera_handler.remote_live()
    # camera_handler.play("recording_250812_052245.raw")
    # camera_handler.record(DISPLAY=False)
