from camera_handler import CameraHandler
from logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    camera_handler = CameraHandler()
    camera_handler.remote_live()
