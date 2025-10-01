from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
from metavision_sdk_ui import EventLoop, BaseWindow, MTWindow, UIKeyEvent
from metavision_core.event_io.raw_reader import initiate_device
import threading
import os
import time
import logging
import json
import curses
import subprocess
from pathlib import Path

class Camera:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        try:
            # HAL Device on live camera
            self.device = initiate_device("")
        except Exception as e:
            self.logger.error(f"Failed to initiate device: {e}")
            self.logger.info("Continue without camera")
            self.device = None

    def adjust(self):
        if not self.device:
            self.logger.warning("No device available.")
            return

        curses.wrapper(self.run_adjust_menu)

        self.adjust_running = True
        adjust_thread = threading.Thread(target=self.live, args=())
        adjust_thread.start()

    def run_adjust_menu(self, stdscr):
        curses.curs_set(0)  # hide cursor
        idx = 0             # currently selected bias
        step = 1            # increment/decrement step

        biases = self.device.get_i_ll_biases()
        save_file = Path(__file__).parent.parent / "assets" / "biases.json"

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "--- Terminal Bias Adjustment ---")
            stdscr.addstr(1, 0, "Use ↑/↓ to select, ←/→ to adjust, 's'=save, 'r'=read, 'q'=quit")

            bias_list = list(biases.get_all_biases().items())
            for i, (name, value) in enumerate(bias_list):
                prefix = "-> " if i == idx else "   "
                stdscr.addstr(i + 3, 0, f"{prefix}[{i}] {name}: {value}")

            # Calculate safe line for status messages
            h, w = stdscr.getmaxyx()
            status_y = min(len(bias_list) + 3, h - 1)

            key = stdscr.getch()

            if key == ord("q"):
                break
            elif key == curses.KEY_UP:
                idx = (idx - 1) % len(bias_list)
            elif key == curses.KEY_DOWN:
                idx = (idx + 1) % len(bias_list)
            elif key == curses.KEY_LEFT:
                name, value = bias_list[idx]
                new_val = value - step

                try:
                    biases.set(name, new_val)
                except Exception as e:
                    message = f"Error: {e}"
                    stdscr.addstr(status_y, 0, message[:w-1])

            elif key == curses.KEY_RIGHT:
                name, value = bias_list[idx]
                new_val = value + step

                try:
                    biases.set(name, new_val)
                except Exception as e:
                    message = f"Error: {e}"
                    stdscr.addstr(status_y, 0, message[:w-1])

            elif key == ord("s"):
                with open(save_file, "w") as f:
                    json.dump(dict(bias_list), f, indent=4)
                msg = f"Saved to {save_file}"
                stdscr.addstr(min(status_y + 2, h - 1), 0, msg[:w-1])

            elif key == ord("r"):
                if os.path.exists(save_file):
                    with open(save_file, "r") as f:
                        saved = json.load(f)
                    for k, v in saved.items():
                        biases.set(k, v)
                msg = f"Loaded from {save_file}"
                stdscr.addstr(min(status_y + 2, h - 1), 0, msg[:w-1])

            stdscr.refresh()

    def record(self):
        if not self.device:
            self.logger.warning("No device available for recording.")
            return

        # Events iterator on Device
        mv_iterator = EventsIterator.from_device(device=self.device)
        height, width = mv_iterator.get_size()  # Camera Geometry

        # Start the recording
        output_dir = Path(__file__).parent.parent / "assets"
        log_path = str(output_dir) + "recording_" + time.strftime("%y%m%d_%H%M%S", time.localtime()) + ".raw"
        if self.device.get_i_events_stream():
            self.logger.info(f'Recording to {log_path}')
            self.device.get_i_events_stream().log_raw_data(log_path)

        self.logger.info("Open window")
        with MTWindow(title="Metavision Events Viewer",
                        width=width,
                        height=height,
                        mode=BaseWindow.RenderMode.BGR) as window:
            def keyboard_cb(key, scancode, action, mods):
                if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                    window.set_close_flag()

            window.set_keyboard_callback(keyboard_cb)

            # Event Frame Generator
            event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width,
                                                            sensor_height=height,
                                                            fps=25,
                                                            palette=ColorPalette.Dark)

            def on_cd_frame_cb(ts, cd_frame):
                window.show_async(cd_frame)

            event_frame_gen.set_output_callback(on_cd_frame_cb)

            # Process events
            for evs in mv_iterator:
                # Dispatch system events to the window
                EventLoop.poll_and_dispatch()
                event_frame_gen.process_events(evs)

                if window.should_close():
                    # Stop the recording
                    self.device.get_i_events_stream().stop_log_raw_data()
                    self.logger.info(f"Stopped recording. Saved to {log_path}")
                    break


    def headless_record(self, output_dir=""):
        if not self.device:
            self.logger.warning("No device available for recording.")
            return

        # Events iterator on Device
        mv_iterator = EventsIterator.from_device(device=self.device)
        height, width = mv_iterator.get_size()  # Camera Geometry

        # Start the recording
        if self.device.get_i_events_stream():
            log_path = "recording_" + time.strftime("%y%m%d_%H%M%S", time.localtime()) + ".raw"
            if output_dir != "":
                log_path = os.path.join(output_dir, log_path)
            self.logger.info(f'Recording to {log_path}')
            self.device.get_i_events_stream().log_raw_data(log_path)

        try:
            for evs in mv_iterator:
                pass
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user.")
        except Exception as e:
            self.logger.error(f"Error during recording: {e}")
        finally:
            self.device.get_i_events_stream().stop_log_raw_data()
            self.logger.info(f"Stopped recording. Saved to {log_path}")

    def play(self, input_file: str = ""):
        if input_file == "":
            self.logger.error("No input file provided for playback.")
            return

        if not os.path.exists(input_file):
            self.logger.error(f"Input file does not exist: {input_file}")
            return

        self.logger.info("Setup events iterator")
        self.mv_iterator = EventsIterator(input_path=input_file, delta_t=1000)
        height, width = self.mv_iterator.get_size() # Camera Geometry

        if not is_live_camera(input_file):
            self.mv_iterator = LiveReplayEventsIterator(self.mv_iterator)

        self.logger.info("Open window")
        with MTWindow(
            title="Metavision Events Viewer",
            width=width,
            height=height,
            mode=BaseWindow.RenderMode.BGR
        ) as window:

            def keyboard_cb(key, scancode, action, mods):
                if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                    window.set_close_flag()

            window.set_keyboard_callback(keyboard_cb)

            # Event Frame Generator
            event_frame_gen = PeriodicFrameGenerationAlgorithm(
                sensor_width=width,
                sensor_height=height,
                fps=25,
                palette=ColorPalette.Dark
            )

            def on_cd_frame_cb(ts, cd_frame):
                window.show_async(cd_frame)

            event_frame_gen.set_output_callback(on_cd_frame_cb)

            # Process events
            for evs in self.mv_iterator:
                # Dispatch system events to the window
                EventLoop.poll_and_dispatch()
                event_frame_gen.process_events(evs)

                if window.should_close():
                    break

    def live(self):
        if not self.device:
            self.logger.warning("No device available for living.")
            return

        # Events iterator on Device
        mv_iterator = EventsIterator.from_device(device=self.device)
        height, width = mv_iterator.get_size()  # Camera Geometry

        self.logger.info("Open window")
        with MTWindow(title="Metavision Events Viewer",
                        width=width,
                        height=height,
                        mode=BaseWindow.RenderMode.BGR) as window:
            def keyboard_cb(key, scancode, action, mods):
                if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                    window.set_close_flag()

            window.set_keyboard_callback(keyboard_cb)

            # Event Frame Generator
            event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width,
                                                            sensor_height=height,
                                                            fps=25,
                                                            palette=ColorPalette.Dark)

            def on_cd_frame_cb(ts, cd_frame):
                window.show_async(cd_frame)

            event_frame_gen.set_output_callback(on_cd_frame_cb)

            # Process events
            for evs in mv_iterator:
                # Dispatch system events to the window
                EventLoop.poll_and_dispatch()
                event_frame_gen.process_events(evs)

                if window.should_close():
                    # Stop the recording
                    self.logger.info(f"Stopped living")
                    break

    def remote_live(self, quality="medium", fps=25):
        if not self.device:
            self.logger.warning("No device available for streaming.")
            return

        mv_iterator = EventsIterator.from_device(device=self.device)
        height, width = mv_iterator.get_size()

        receiver_ip = input("Enter the receiver's IP address to stream to: ")
        # receiver_port = int(input("Enter the port to stream to: "))
        receiver_port = 5000
        self.logger.info(f"Streaming live frame to {receiver_ip}:{receiver_port} (quality={quality}, fps={fps})")

        # Compression settings
        if quality == "low":
            preset, crf = "slow", 35
        elif quality == "high":
            preset, crf = "veryfast", 20
        else:
            preset, crf = "fast", 28

        # ffmpeg command
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "rawvideo",
            "-pixel_format", "bgr24",
            "-video_size", f"{width}x{height}",
            "-r", "25",
            "-i", "-",
            "-c:v", "libx264",
            "-preset", f"{preset}",
            "-crf", f"{crf}",
            "-tune", "zerolatency",
            "-g", "25",
            "-f", "mpegts",
            f"udp://{receiver_ip}:{receiver_port}"
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

        # Event Frame Generator
        event_frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=width,
            sensor_height=height,
            fps=fps,
            palette=ColorPalette.Dark,
        )

        def on_cd_frame_cb(ts, cd_frame):
            try:
                proc.stdin.write(cd_frame.tobytes())
            except (BrokenPipeError, IOError):
                self.logger.error("SSH stream closed.")
                proc.terminate()

        event_frame_gen.set_output_callback(on_cd_frame_cb)

        for evs in mv_iterator:
            EventLoop.poll_and_dispatch()
            event_frame_gen.process_events(evs)
            if proc.poll() is not None:
                break

        proc.stdin.close()
        proc.wait()
        self.logger.info("Stopped streaming.")

    def remote_play(self, input_file="", quality="medium", fps=25):
        if input_file == "":
            self.logger.error("No input file provided for playback.")
            return

        if not os.path.exists(input_file):
            self.logger.error(f"Input file does not exist: {input_file}")
            return

        receiver_ip = input("Enter the receiver's IP address to stream to: ")
        # receiver_port = int(input("Enter the port to stream to: "))
        receiver_port = 5000
        self.logger.info(f"Streaming {input_file} to {receiver_ip}:{receiver_port} (quality={quality}, fps={fps})")

        if quality == "low":
            preset, crf = "slow", 35
        elif quality == "high":
            preset, crf = "veryfast", 20
        else:
            preset, crf = "fast", 28

        self.mv_iterator = EventsIterator(input_path=input_file, delta_t=1000)
        height, width = self.mv_iterator.get_size()

        if not is_live_camera(input_file):
            self.mv_iterator = LiveReplayEventsIterator(self.mv_iterator)

        # ffmpeg command
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "rawvideo",
            "-pixel_format", "bgr24",
            "-video_size", f"{width}x{height}",
            "-r", "25",
            "-i", "-",
            "-c:v", "libx264",
            "-preset", f"{preset}",
            "-crf", f"{crf}",
            "-tune", "zerolatency",
            "-g", "25",
            "-f", "mpegts",
            f"udp://{receiver_ip}:{receiver_port}"
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

        event_frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=width,
            sensor_height=height,
            fps=fps,
            palette=ColorPalette.Dark
        )

        def on_cd_frame_cb(ts, cd_frame):
            try:
                proc.stdin.write(cd_frame.tobytes())
            except (BrokenPipeError, IOError):
                self.logger.error("UDP stream closed.")
                proc.terminate()

        event_frame_gen.set_output_callback(on_cd_frame_cb)

        for evs in self.mv_iterator:
            EventLoop.poll_and_dispatch()
            event_frame_gen.process_events(evs)
            if proc.poll() is not None:
                break

        proc.stdin.close()
        proc.wait()
        self.logger.info("Stopped streaming.")
