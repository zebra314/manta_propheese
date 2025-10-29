import logging
import time
import threading
from src.setup_logging import setup_logging
from src.camera import Camera

class Launcher:
    def __init__(self, start_delay: int = 10, run_duration: int = 20):
        self.start_delay = start_delay
        self.run_duration = run_duration
        self.camera = Camera()
        self.task_thread = None

    def start(self):
        logger.info(f"Program started. Waiting {self.start_delay} seconds before recording...")
        time.sleep(self.start_delay)
        self.task_thread = threading.Thread(target=self.my_task, daemon=True)
        self.task_thread.start()

    def my_task(self):
        logger.info("Recording started.")
        self.camera.set_end_event_false()
        self.camera.headless_record()

    def stop_task(self):
        logger.info("Stopping recording...")
        self.camera.set_end_event_true()

        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join()
            logger.info("Recording stopped safely.")

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    launcher = Launcher(start_delay=10, run_duration=20)
    launcher.start()

    try:
        time.sleep(launcher.run_duration)
        launcher.stop_task()
        logger.info("Recording finished.")

    except KeyboardInterrupt:
        logger.warning("Exiting program by user.")
        launcher.stop_task()

    finally:
        logger.info("Program terminated.")
