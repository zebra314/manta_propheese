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
from menu import Menu
from collections import deque
from datetime import datetime
from pathlib import Path

# ---------------------------------- Logging --------------------------------- #
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',   # Blue
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[95m' # Purple
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

class CursesLogHandler(logging.Handler):
    """Custom logging handler that stores log messages for display in curses window"""
    
    def __init__(self, max_lines=100):
        super().__init__()
        self.log_lines = deque(maxlen=max_lines)  # Store recent log messages
    
    def emit(self, record):
        try:
            # Format the log message
            log_entry = self.format(record)
            # Add timestamp if not already in format
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_entry = f"[{timestamp}] {log_entry}"
            self.log_lines.append(formatted_entry)
        except Exception:
            self.handleError(record)
    
    def get_recent_logs(self, num_lines=None):
        """Get recent log messages for display"""
        if num_lines is None:
            return list(self.log_lines)
        return list(self.log_lines)[-num_lines:]
    
# ------------------------------ Camera Handler ------------------------------ #
class CameraHandler:
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        try:
            # HAL Device on live camera
            self.device = initiate_device("")
        except Exception as e:
            self.logger.error(f"Failed to initiate device: {e}")
            self.logger.info("Continue without camera")
            self.device = None

        self.display_menu_items = [mode for mode in Menu if mode != Menu.HOME]
        self.current_mode = Menu.HOME
        self.selected_idx = 0
    
    def setup_logging(self):
        # Create custom handler for curses display
        self.curses_handler = CursesLogHandler()
        self.curses_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s: %(message)s'))
        
        # Create console handler for terminal output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColorFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        ))
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.curses_handler)
        root_logger.addHandler(console_handler)

    def display_logs_in_window(self):
        """Display recent log messages in the log window"""
        self.log_window.erase()
        self.log_window.box()
        
        # Get window dimensions
        height, width = self.log_window.getmaxyx()
        max_lines = height - 2  # Account for box borders
        
        # Get recent log messages
        recent_logs = self.curses_handler.get_recent_logs(max_lines)
        
        # Display logs starting from the most recent
        for i, log_line in enumerate(recent_logs[-max_lines:]):
            try:
                display_line = log_line[:width-3]
                self.log_window.addstr(1 + i, 1, display_line)
            except curses.error:
                break

        self.log_window.refresh()
    
    def menu(self):
        curses.wrapper(self.main_loop)

    def main_loop(self, stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        
        height, width = stdscr.getmaxyx()

        menu_window = curses.newwin(2 * height // 3, width, 0, 0)
        self.log_window = curses.newwin(1 * height // 3, width, 2 * height // 3, 0)

        menu_window.keypad(True)
        menu_window.nodelay(False)
        self.log_window.nodelay(True)

        self.logger.info("Application started")
        
        while True:
            # Update log window
            self.display_logs_in_window()

            # Read user input with timeout
            menu_window.timeout(100)  # 100ms timeout
            key = menu_window.getch()
            
            # Handle modes
            if self.current_mode == Menu.HOME:
                self.run_home(menu_window, key)
            elif self.current_mode == Menu.RECORD:
                self.run_record(menu_window, key)
            elif self.current_mode == Menu.PLAY:
                self.run_play(menu_window, key)
            elif self.current_mode == Menu.LIVE:
                self.run_live(menu_window, key)
            elif self.current_mode == Menu.ADJUST:
                self.run_adjust(menu_window, key)

    def run_home(self, window: curses.window, key):
        if key == ord("q") or key == ord("Q"):
            self.logger.info("Quit requested")
            exit(0)
        elif key == curses.KEY_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.display_menu_items)
        elif key == curses.KEY_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.display_menu_items)
        elif key in [10, 13, curses.KEY_ENTER]:  # Enter
            selected_mode = self.display_menu_items[self.selected_idx]
            self.logger.info(f"Enter pressed, switching to mode: {selected_mode.name}")
            self.current_mode = selected_mode
    
        window.clear()
        window.box()
        window.addstr(1, 1, "HOME MENU")
        window.addstr(2, 1, "Use ↑/↓ to select, Enter to confirm, q to quit")
        
        for i, mode in enumerate(self.display_menu_items):
            line_y = 4 + i
            try:
                if i == self.selected_idx:
                    window.addstr(line_y, 2, f"> {mode.name}", curses.A_REVERSE)
                else:
                    window.addstr(line_y, 2, f"  {mode.name}")
            except curses.error:
                break

        window.refresh()

    def run_record(self, window: curses.window, key):
        if key == ord("b") or key == ord("B"):
            self.current_mode = Menu.HOME
        
        window.clear()
        window.box()
        window.addstr(1, 1, "RECORD MODE")
        window.addstr(2, 1, "Press 'b' to go back")
        window.refresh()

    def run_play(self, window: curses.window, key):
        # Search files
        folder_path = Path(__file__).parent.parent / "assets"
        raw_files = [f for f in os.listdir(folder_path) if f.endswith(".raw")]
        
        if not raw_files:
            window.clear()
            window.box()
            window.addstr(1, 1, "No .raw files found!")
            window.addstr(2, 1, "Press 'q' to go back")
            window.refresh()
            if key in [ord("q"), ord("Q")]:
                self.current_mode = Menu.HOME
            return

        if not hasattr(self, "play_selected_idx"):
            self.play_selected_idx = 0

        if key == curses.KEY_UP:
            self.play_selected_idx = (self.play_selected_idx - 1) % len(raw_files)
        elif key == curses.KEY_DOWN:
            self.play_selected_idx = (self.play_selected_idx + 1) % len(raw_files)
        elif key in [10, 13, curses.KEY_ENTER]:  # Enter
            selected_file = os.path.join(folder_path, raw_files[self.play_selected_idx])
            self.play(selected_file)
        elif key in [ord("q"), ord("Q")]:
            self.current_mode = Menu.HOME
            del self.play_selected_idx
            return

        window.clear()
        window.box()
        window.addstr(1, 1, "PLAY MODE - Select file")
        window.addstr(2, 1, "Use ↑/↓ to select, Enter to play, 'q' to go back")
        
        for i, f in enumerate(raw_files):
            if i == self.play_selected_idx:
                window.addstr(3+i, 3, f"> {f}", curses.A_REVERSE)
            else:
                window.addstr(3+i, 3, f"  {f}")

        window.refresh()

    def run_live(self, window: curses.window, key):
        if key == ord("q") or key == ord("Q"):
            self.current_mode = Menu.HOME
            return
        
        self.live()
        
        window.clear()
        window.box()
        window.addstr(1, 1, "LIVE MODE")
        window.addstr(2, 1, "Press 'q' to go back")
        window.refresh()

    def run_adjust(self, window: curses.window, key):
        if key == ord("q") or key == ord("Q"):
            self.current_mode = Menu.HOME
            return
        
        if not self.device:
            self.logger.warning("No device available for adjusting bias.")
            return
        
        biases = self.device.get_i_ll_biases()
        if not biases:
            self.logger.warning("No biases available on the device.")
            return
        bias_list = list(biases.get_all_biases().items())

        self.adjust_running = True

        # Start live thread
        if not hasattr(self, "live_thread") or not self.live_thread.is_alive():
            self.live_stop_event = threading.Event()

            def live_thread_fn():
                self.logger.info("Start live feed in adjust mode")
                mv_iterator = EventsIterator.from_device(device=self.device)
                height, width = mv_iterator.get_size()

                with MTWindow(title="Metavision Events Viewer",
                            width=width,
                            height=height,
                            mode=BaseWindow.RenderMode.BGR) as window_mt:

                    event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width,
                                                                    sensor_height=height,
                                                                    fps=25,
                                                                    palette=ColorPalette.Dark)

                    def on_cd_frame_cb(ts, cd_frame):
                        window_mt.show_async(cd_frame)

                    event_frame_gen.set_output_callback(on_cd_frame_cb)

                    for evs in mv_iterator:
                        if not self.adjust_running:
                            break

                        EventLoop.poll_and_dispatch()
                        event_frame_gen.process_events(evs)

                self.logger.info("Stop live feed in adjust mode")

            self.live_thread = threading.Thread(target=live_thread_fn, daemon=True)
            self.live_thread.start()

        # Start adjust curses loop
        save_file = Path(__file__).parent.parent / "assets" / "biases.json"
        idx, step = 0, 1

        window.timeout(50)
        while self.adjust_running:
            k = window.getch()

            if k in [ord("q"), ord("Q")]:
                self.current_mode = Menu.HOME
                self.adjust_running = False
                break
            elif k == curses.KEY_UP:
                idx = (idx - 1) % len(bias_list)
            elif k == curses.KEY_DOWN:
                idx = (idx + 1) % len(bias_list)
            elif k == curses.KEY_LEFT:
                name, value = bias_list[idx]
                biases.set(name, value - step)
            elif k == curses.KEY_RIGHT:
                name, value = bias_list[idx]
                biases.set(name, value + step)
            elif k == ord("s"):
                with open(save_file, "w") as f:
                    json.dump(dict(bias_list), f, indent=4)
            elif k == ord("r"):
                if os.path.exists(save_file):
                    with open(save_file, "r") as f:
                        saved = json.load(f)
                    for name, val in saved.items():
                        biases.set(name, val)
            
            window.clear()
            window.box()
            window.addstr(1, 1, "BIAS ADJUSTMENT MODE")
            window.addstr(2, 1, "Use ↑/↓ to select, ←/→ to adjust, 's'=save, 'r'=read, 'b'=back")

            for i, (name, value) in enumerate(bias_list):
                prefix = "-> " if i == idx else "   "
                window.addstr(4 + i, 2, f"{prefix}[{i}] {name}: {value}")

            window.refresh()

    def adjust_bias(self):
        if not self.device:
            self.logger.warning("No device available for recording.")
            return
        
        biases = self.device.get_i_ll_biases()
        if not biases:
            self.logger.warning("No biases available on the device.")
            return
        
        # self.logger.info(f"Available biases: {biases.get_all_biases()}")

        # All biases
        ## bias_diff, recommend not to change, the reference voltage of the comparators

        # Contrast sensitivity threshold biases
        ## bias_diff_on, the contrast threshould for on events
        ## bias_diff_off, the contrast threshould for off events

        # Bandwidth biases
        ## bias_fo, the low pass filter, the maximum rate of change of illumination that can be detected
        ## bias_hpf, the high pass filter, determines the minimum rate the light must change, for the pixel to output an event
        
        # Dead time bias
        ## bias_refr, adjusts the refractory period, determines the duration for which the pixel is blind after each event

        # Nevertheless, those steps are considered valid in many scenarios are a good starting point:
        # first update bias_fo to reduce impacts of rapidly fluctuating light (high frequencies),
        # then update bias_hpf to reduce background noise (low frequencies),
        # finally you can adjust bias_diff_on and bias_diff_off to adapt the Contrast Sensitivity to your application.

        save_file = "biases.json"
        def run(stdscr):
            curses.curs_set(0)  # hide cursor
            idx = 0             # currently selected bias
            step = 1            # increment/decrement step

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

        curses.wrapper(run)
        
    def record(self, output_dir="", DISPLAY=True):
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

        if DISPLAY:
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
        else:
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
                self.display_logs_in_window()
                
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
