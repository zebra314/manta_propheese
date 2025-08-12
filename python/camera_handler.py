from metavision_sdk_stream import Camera, CameraStreamSlicer
from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
from metavision_sdk_ui import EventLoop, BaseWindow, MTWindow, UIAction, UIKeyEvent
from metavision_core.event_io.raw_reader import initiate_device
import threading
import argparse
import os
import time
import logging
import tkinter as tk
from tkinter import ttk

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt = '%H:%M:%S',
    )

class CameraHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            # HAL Device on live camera
            self.device = initiate_device("")

            # Start adjusting camera bias thread
            self.enable_ajust_bias()

        except Exception as e:
            self.logger.error(f"Failed to initiate device: {e}")
            self.logger.info("Continue without camera")

            self.device = None
        
    def enable_ajust_bias(self):
        if not self.device:
            self.logger.warning("No device available for adjusting bias.")
            return
        
        self.adjust_running = True
        adjust_thread = threading.Thread(target=self.adjust_bias, args=())
        adjust_thread.start()

    def adjust_bias(self, GUI=True):
        if not self.device:
            self.logger.warning("No device available for recording.")
            return
        
        biases = self.device.get_i_ll_biases()
        if not biases:
            self.logger.warning("No biases available on the device.")
            return
        
        self.logger.info(f"Available biases: {biases.get_all_biases()}")

        # All biases
        ## bias_diff, recommend not to change

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

        if GUI:
            root = tk.Tk()
            root.title("Bias 調整工具")
            root.geometry("400x400")

            # 動態建立 slider
            sliders = {}
            for i, (bias_name, value) in enumerate(biases.get_all_biases().items()):
                tk.Label(root, text=bias_name).grid(row=i, column=0, padx=10, pady=5, sticky="w")

                slider = ttk.Scale(
                    root,
                    from_=-150,
                    to=150,  # 假設範圍 0~255，可依 datasheet 調整
                    orient="horizontal",
                    command=lambda val, name=bias_name: biases.set(name, int(float(val)))
                )
                slider.set(value)
                slider.grid(row=i, column=1, padx=10, pady=5)
                sliders[bias_name] = slider

            root.mainloop()

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
            finally:
                self.device.get_i_events_stream().stop_log_raw_data()
                self.logger.info(f"Stopped recording. Saved to {log_path}")

    def play(self, input_file=""):
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

if __name__ == "__main__":
    setup_logging()
    camera_handler = CameraHandler()
    camera_handler.live()
    # camera_handler.play("recording_250812_052245.raw")
    # camera_handler.record(DISPLAY=False)
    # camera_handler.adjust_camera_bias()
