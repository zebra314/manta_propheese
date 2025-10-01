import RPi.GPIO as GPIO
import logging
import time
import threading
from src.setup_logging import setup_logging

RUN_DURATION = 10
signal_detected = False
task_thread = None

def my_task():
    logger.info("Task started.")
    while True:
        logger.info("Task is running...")
        time.sleep(1)

def stop_task():
    global task_thread
    logger.info("Stopping task...")
    task_thread = None  # Set thread to None to indicate stopping

def on_signal_detected(channel):
    global signal_detected, task_thread

    if not signal_detected: # Avoid multiple triggers
        logger.info(f"Detected signal on channel: {channel}")
        signal_detected = True

        # Activate new task thread
        task_thread = threading.Thread(target=my_task, daemon=True)
        task_thread.start()

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    GPIO.setmode(GPIO.BCM)

    # GPIO 3, PIN 5
    INPUT_PIN = 3

    GPIO.setup(INPUT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(INPUT_PIN, GPIO.RISING, callback=on_signal_detected, bouncetime=200)

    try:
        while True:
            if signal_detected:

                time.sleep(RUN_DURATION)
                stop_task()

                logger.info("Task finished. Exiting program.")
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("Exiting program by user.")

    finally:
        GPIO.cleanup()
