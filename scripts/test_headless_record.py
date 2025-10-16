from pathlib import Path
from camera import Camera

if __name__ == "__main__":
    camera = Camera()
    camera.set_end_event_false()
    camera.headless_record()
