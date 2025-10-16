import logging
import time
import threading
from gpiozero import DigitalInputDevice
from src.setup_logging import setup_logging
from src.camera import Camera

class Launcher:
    def __init__(self, input_pin: int = 4, run_duration: int = 20):
        self.input_pin = input_pin
        self.run_duration = run_duration
        self.signal_detected = False
        self.camera = Camera()
        self.task_thread = None

    def start(self):
        self.input_device = DigitalInputDevice(self.input_pin, pull_up=False, bounce_time=0.05)
        self.input_device.when_activated = self.on_signal_detected

    def on_signal_detected(self):
        if not self.signal_detected:
            self.signal_detected = True
            self.task_thread = threading.Thread(target=self.my_task, daemon=True)
            self.task_thread.start()

    def my_task(self):
        logger.info("Task started.")
        self.camera.set_end_event_false()
        self.camera.headless_record()

    def stop_task(self):
        logger.info("Stopping task...")
        self.camera.set_end_event_true()

        if self.task_thread and self.task_thread.is_alive():
            self.task_thread.join()
            logger.info("Task thread has stopped safely.")

    def reset_task(self):
        logger.info("Resetting task...")
        self.camera.set_end_event_false()
        self.signal_detected = False

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    launcher = Launcher()
    launcher.start()

    last_log_time = 0
    log_interval = 1.0

    try:
        while True:
            if launcher.signal_detected:

                time.sleep(launcher.run_duration)
                launcher.stop_task()
                logger.info("Task finished.")

                launcher.reset_task()
                logger.info("Ready for next signal.")
            else:
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    logger.info("No signal detected.")
                    last_log_time = current_time

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.warning("Exiting program by user.")

    finally:
        launcher.input_device.close()
        logger.info("Program terminated.")
