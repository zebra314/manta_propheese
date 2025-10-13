import lgpio
import logging
import time
import threading
from src.setup_logging import setup_logging
from src.camera import Camera

RUN_DURATION = 20
CHIP = 0 # usually gpiochip0
INPUT_PIN = 3 # BCM 3, physical pin 5

signal_detected = False
task_thread = None
camera = Camera()

def my_task():
    logger.info("Task started.")

    while True:
        logger.info("Task is running...")
        time.sleep(1)

    # camera.headless_record()

def stop_task():
    global task_thread
    logger.info("Stopping task...")
    camera.set_end_event_true()

    if task_thread and task_thread.is_alive():
        task_thread.join()
        logger.info("Task thread has stopped safely.")

    task_thread = None

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

    # GPIO.setmode(GPIO.BCM)
    # GPIO.setup(INPUT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # GPIO.add_event_detect(INPUT_PIN, GPIO.RISING, callback=on_signal_detected, bouncetime=200)

    h = lgpio.gpiochip_open(CHIP)
    lgpio.gpio_claim_input(h, INPUT_PIN)
    lgpio.gpio_set_debounce_micros(CHIP, INPUT_PIN, 200000)
    lgpio.gpio_claim_alert(h, INPUT_PIN, lgpio.RISING_EDGE)
    cb = lgpio.callback(h, INPUT_PIN, lgpio.RISING_EDGE, on_signal_detected)

    try:
        while True:
            if signal_detected:

                time.sleep(RUN_DURATION)
                stop_task()

                logger.info("Task finished. Resetting state.")

                signal_detected = False
                camera.set_end_event_false()

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("Exiting program by user.")

    finally:
        cb.cancel()
        lgpio.gpiochip_close(h)
