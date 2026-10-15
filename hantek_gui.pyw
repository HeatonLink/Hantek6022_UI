#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hantek 6022BE / 6022BL Simple GUI
=================================

A lightweight Python GUI for the Hantek DSO6022BE / 6022BL USB oscilloscope.

Dependencies (install with):
    pip install pyhantek6022[gui] matplotlib numpy FreeSimpleGUI

Usage:
    - Double-click hantek_gui.pyw
    - If nothing appears, check hantek_gui_startup.log next to this file
"""

import sys
import os
import traceback
import time
import logging
from datetime import datetime

# --- Startup log (always written, even if GUI fails) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
STARTUP_LOG = os.path.join(SCRIPT_DIR, "hantek_gui_startup.log")

def write_startup_log(msg):
    try:
        with open(STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except Exception:
        pass

write_startup_log("=== Script started ===")
write_startup_log(f"Python: {sys.version}")
write_startup_log(f"Executable: {sys.executable}")
write_startup_log(f"Working dir: {os.getcwd()}")
write_startup_log(f"Script dir: {SCRIPT_DIR}")

# --- Always-safe imports ---
try:
    import FreeSimpleGUI as sg
    write_startup_log("FreeSimpleGUI imported OK")
except Exception as e:
    write_startup_log(f"FreeSimpleGUI import FAILED: {e}\n{traceback.format_exc()}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Hantek GUI - Missing dependency",
            f"FreeSimpleGUI is required.\n\nError: {e}\n\nRun:\npip install FreeSimpleGUI\n\nSee {STARTUP_LOG}"
        )
    except Exception:
        pass
    sys.exit(1)

try:
    import numpy as np
    write_startup_log("numpy imported OK")
except Exception:
    np = None
    write_startup_log("numpy not available")

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_OK = True
    write_startup_log("matplotlib imported OK")
except Exception as e:
    MATPLOTLIB_OK = False
    write_startup_log(f"matplotlib import failed: {e}")

# Optional device library
try:
    from labdevices.oscilloscope import (
        OscilloscopeRunMode,
        OscilloscopeSweepMode,
        OscilloscopeTriggerMode,
    )
    from pyhantek6022.dso6022be import DSO6022BE, get_dsos
    from pyhantek6022.firmwareupload import FirmwareUploader
    DEVICE_LIB_OK = True
    write_startup_log("pyhantek6022 imported OK")
except Exception as e:
    DEVICE_LIB_OK = False
    DEVICE_LIB_ERROR = str(e)
    write_startup_log(f"pyhantek6022 import failed: {e}\n{traceback.format_exc()}")


class GUILogHandler(logging.Handler):
    """Send log records to the GUI multiline log."""
    def __init__(self, window, key="-LOG-"):
        super().__init__()
        self.window = window
        self.key = key

    def emit(self, record):
        try:
            msg = self.format(record)
            current = self.window[self.key].get()
            lines = (current + "\n" + msg).splitlines()[-200:]
            self.window[self.key].update("\n".join(lines))
        except Exception:
            pass


class HantekGUI:
    def __init__(self):
        write_startup_log("HantekGUI.__init__ starting")
        self._logger = logging.getLogger("HantekGUI")
        self._logger.setLevel(logging.DEBUG)

        self._probe_ratios = [1, 10, 100]
        self._channel_scales = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        self._timebase_scales = [
            33.3e-6, 66.7e-6, 100e-6, 200e-6, 500e-6,
            1e-3, 2e-3, 5e-3, 10e-3, 20e-3
        ]

        self._device_labels = []
        self._devices = []
        self._device = None
        self._running = False
        self._averages = 1
        self._average_buffer = []
        self._last_settings = None
        self._figures = {}

        sg.theme("DarkAmber")

        left_col = [
            [sg.Text("Device")],
            [
                sg.Combo([], key="cmbDevice", size=(40, 1), readonly=True),
                sg.Button("Refresh", key="btnRefresh"),
            ],
            [
                sg.Button("Connect", key="btnConnect"),
                sg.Button("Disconnect", key="btnDisconnect"),
            ],
            [sg.HorizontalSeparator()],
            [
                sg.Text("Run mode"),
                sg.Combo(["RUN", "STOP", "SINGLE"], default_value="RUN", key="cmbRunMode", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Sweep mode"),
                sg.Combo(["AUTO", "NORMAL", "SINGLE"], default_value="AUTO", key="cmbSweepMode", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Trigger mode"),
                sg.Combo(["EDGE", "PULSE", "SLOPE"], default_value="EDGE", key="cmbTriggerMode", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Trigger source"),
                sg.Combo(["CH1", "CH2"], default_value="CH1", key="cmbTriggerSource", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Trigger slope"),
                sg.Combo(["positive", "negative", "both"], default_value="positive", key="cmbTriggerSlope", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Trigger level [V]"),
                sg.InputText("0.0", key="txtTriggerLevel", size=(12, 1)),
            ],
            [
                sg.Text("Trigger position"),
                sg.InputText("0.5", key="txtTriggerPosition", size=(12, 1)),
            ],
            [sg.Checkbox("Smooth trigger", key="chkTriggerSmooth", default=False)],
            [sg.HorizontalSeparator()],
            [
                sg.Checkbox("CH1", key="chkCh0", default=True),
                sg.Text("Scale"),
                sg.Combo(self._channel_scales, default_value=1.0, key="cmbScale0", readonly=True, size=(8, 1)),
                sg.Text("Probe"),
                sg.Combo(self._probe_ratios, default_value=1, key="cmbProbe0", readonly=True, size=(8, 1)),
            ],
            [
                sg.Checkbox("CH2", key="chkCh1", default=False),
                sg.Text("Scale"),
                sg.Combo(self._channel_scales, default_value=1.0, key="cmbScale1", readonly=True, size=(8, 1)),
                sg.Text("Probe"),
                sg.Combo(self._probe_ratios, default_value=1, key="cmbProbe1", readonly=True, size=(8, 1)),
            ],
            [
                sg.Text("Timebase [s/div]"),
                sg.Combo(self._timebase_scales, default_value=1e-3, key="cmbTimebase", readonly=True, size=(12, 1)),
            ],
            [
                sg.Text("Averages"),
                sg.Combo([1, 2, 4, 8, 16, 32], default_value=1, key="cmbAverages", readonly=True, size=(8, 1)),
            ],
            [
                sg.Checkbox("Show average", key="chkShowAverage", default=True),
                sg.Checkbox("Show std dev", key="chkShowStd", default=False),
            ],
            [sg.HorizontalSeparator()],
            [
                sg.Button("Apply", key="btnApply"),
                sg.Button("Acquire", key="btnAcquire"),
                sg.Button("Start Continuous", key="btnStart"),
                sg.Button("Force Trigger", key="btnForceTrigger"),
            ],
            [sg.Text("Status:"), sg.Text("Not connected", key="txtStatus", size=(40, 2))],
            [sg.Text("Stats:"), sg.Text("-", key="txtTraceStats", size=(40, 4))],
        ]

        right_col = [
            [sg.Canvas(key="canvTrace", size=(900, 300))],
            [sg.Canvas(key="canvFFT", size=(900, 260))],
        ]

        layout = [
            [sg.Column(left_col, vertical_alignment="t"), sg.Column(right_col, vertical_alignment="t")],
            [sg.HorizontalSeparator()],
            [sg.Text("Log:")],
            [sg.Multiline(size=(140, 10), key="-LOG-", autoscroll=True, disabled=True, font=("Consolas", 9), background_color="#1e1e1e", text_color="#d4d4d4")],
        ]

        write_startup_log("Creating window...")
        self._window = sg.Window(
            "Hantek 6022 GUI",
            layout,
            finalize=True,
            resizable=True,
            location=(50, 50),
            keep_on_top=False,
        )
        # Force to front
        try:
            self._window.TKroot.lift()
            self._window.TKroot.attributes('-topmost', 1)
            self._window.TKroot.after_idle(self._window.TKroot.attributes, '-topmost', 0)
            self._window.TKroot.focus_force()
        except Exception as e:
            write_startup_log(f"Could not force window to front: {e}")

        write_startup_log("Window created")

        gui_handler = GUILogHandler(self._window)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S"))
        self._logger.addHandler(gui_handler)
        self._logger.propagate = False

        self.log("GUI started. Startup log: " + STARTUP_LOG)

        if not DEVICE_LIB_OK:
            self.log(f"ERROR: Device library not available: {DEVICE_LIB_ERROR}", level="error")
            self.log("Install with: pip install 'pyhantek6022[gui]'", level="error")
            self._window["txtStatus"].update("Library missing - see log")
        else:
            self.log("Device library loaded OK.")

        if not MATPLOTLIB_OK:
            self.log("WARNING: matplotlib not available - plots will not work.", level="warning")
        else:
            try:
                self._figures = {
                    "trace": self._init_figure("canvTrace", "Time [s]", "Voltage [V]", "Waveform"),
                    "fft": self._init_figure("canvFFT", "Frequency bin", "Magnitude", "FFT"),
                }
                self.log("Plots initialized.")
            except Exception as e:
                self.log(f"Plot init failed: {e}", level="error")
                write_startup_log(f"Plot init failed: {e}")

        self._refresh_devices()
        write_startup_log("HantekGUI.__init__ finished")

    def log(self, message, level="info"):
        if level == "error":
            self._logger.error(message)
        elif level == "warning":
            self._logger.warning(message)
        else:
            self._logger.info(message)
        write_startup_log(f"[{level.upper()}] {message}")

    def _init_figure(self, canvas_name, xlabel, ylabel, title):
        fig = Figure(figsize=(9, 3.0), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        fig_agg = FigureCanvasTkAgg(fig, self._window[canvas_name].TKCanvas)
        fig_agg.draw()
        fig_agg.get_tk_widget().pack(side="top", fill="both", expand=1)

        return {"figure": fig, "axis": ax, "fig_agg": fig_agg}

    def _refresh_devices(self):
        if not DEVICE_LIB_OK:
            self.log("Cannot scan - device library missing.", level="error")
            return

        self.log("Scanning devices & uploading firmware if needed...")
        self._window["txtStatus"].update("Scanning...")
        self._window.refresh()

        try:
            uploaded = FirmwareUploader.init_all()
            if uploaded:
                self.log(f"Firmware uploaded to {len(uploaded)} device(s). Waiting for re-enumeration...")
                time.sleep(2.5)
            else:
                self.log("No firmware upload needed.")
        except Exception as e:
            self.log(f"Firmware upload error: {e}", level="error")
            self.log(traceback.format_exc(), level="error")

        try:
            self._devices = get_dsos() or []
            self._device_labels = []

            for i, dev in enumerate(self._devices):
                try:
                    dso = DSO6022BE(dev)
                    ident = dso.identify() or {}
                    label = f"{ident.get('manufacturer', 'Hantek')} {ident.get('product', '6022')} SN:{ident.get('serial', '?')}"
                except Exception as e:
                    label = f"Device {i} ({e})"
                self._device_labels.append(label)

            self._window["cmbDevice"].update(
                values=self._device_labels,
                value=self._device_labels[0] if self._device_labels else None,
            )
            self.log(f"Found {len(self._devices)} initialized device(s).")
            self._window["txtStatus"].update(f"Found {len(self._devices)} device(s)")
        except Exception as e:
            self.log(f"Device scan failed: {e}", level="error")
            self.log(traceback.format_exc(), level="error")
            self._window["txtStatus"].update("Scan failed - see log")

    def _connect_selected(self):
        if not DEVICE_LIB_OK or self._device is not None:
            return

        sel = self._window["cmbDevice"].get()
        if not sel or sel not in self._device_labels:
            self.log("No device selected.", level="warning")
            self._window["txtStatus"].update("No device selected")
            return

        idx = self._device_labels.index(sel)
        try:
            self.log(f"Connecting to {sel}...")
            self._device = DSO6022BE(self._devices[idx])
            self._device.connect()
            self.log("Connected.")
            self._window["txtStatus"].update(f"Connected: {sel}")
            self._apply_settings()
        except Exception as e:
            self.log(f"Connect failed: {e}", level="error")
            self.log(traceback.format_exc(), level="error")
            self._window["txtStatus"].update(f"Connect failed: {e}")
            self._device = None

    def _disconnect_selected(self):
        if self._device is not None:
            try:
                self._device.disconnect()
                self.log("Disconnected.")
            except Exception as e:
                self.log(f"Disconnect error: {e}", level="warning")
            self._device = None
        self._running = False
        self._average_buffer.clear()
        self._last_settings = None
        self._window["txtStatus"].update("Disconnected")
        self._window["btnStart"].update("Start Continuous")

    def _apply_settings(self):
        if self._device is None:
            self.log("Apply: not connected.", level="warning")
            return

        ch0 = self._window["chkCh0"].get()
        ch1 = self._window["chkCh1"].get()
        if not ch0 and not ch1:
            ch0 = True
            self._window["chkCh0"].update(True)

        try:
            self._device.set_channel_enable(0, ch0)
            self._device.set_channel_enable(1, ch1)

            if ch0:
                self._device.set_channel_probe_ratio(0, int(self._window["cmbProbe0"].get()))
                self._device.set_channel_scale(0, float(self._window["cmbScale0"].get()))
            if ch1:
                self._device.set_channel_probe_ratio(1, int(self._window["cmbProbe1"].get()))
                self._device.set_channel_scale(1, float(self._window["cmbScale1"].get()))

            self._device.set_timebase_scale(float(self._window["cmbTimebase"].get()))

            self._device.set_run_mode(getattr(OscilloscopeRunMode, self._window["cmbRunMode"].get()))
            self._device.set_sweep_mode(getattr(OscilloscopeSweepMode, self._window["cmbSweepMode"].get()))
            self._device.set_trigger_mode(getattr(OscilloscopeTriggerMode, self._window["cmbTriggerMode"].get()))

            src = 0 if self._window["cmbTriggerSource"].get() == "CH1" else 1
            self._device.set_trigger_source(src, smooth=self._window["chkTriggerSmooth"].get())

            slope_map = {"positive": 0, "negative": 1, "both": 2}
            self._device.set_trigger_slope(slope_map[self._window["cmbTriggerSlope"].get()])
            self._device.set_trigger_level(src, float(self._window["txtTriggerLevel"].get()))
            self._device.set_trigger_position(float(self._window["txtTriggerPosition"].get()))

            self._averages = int(self._window["cmbAverages"].get())
            self._average_buffer.clear()
            self.log("Settings applied.")
            self._window["txtStatus"].update("Settings applied")
        except Exception as e:
            self.log(f"Apply failed: {e}", level="error")
            self.log(traceback.format_exc(), level="error")
            self._window["txtStatus"].update(f"Apply failed: {e}")

    def _get_requested_channels(self):
        req = []
        if self._window["chkCh0"].get():
            req.append(0)
        if self._window["chkCh1"].get():
            req.append(1)
        if not req:
            req.append(0)
        return req[0] if len(req) == 1 else tuple(req)

    def _average_trace(self, data):
        if np is None:
            return data
        self._average_buffer.append(data)
        if len(self._average_buffer) > self._averages:
            self._average_buffer = self._average_buffer[-self._averages:]

        if not self._average_buffer:
            return data

        out = dict(data)
        if "y" in data:
            ys = np.array([np.asarray(d["y"]) for d in self._average_buffer])
            out["y_trace_avg"] = np.mean(ys, axis=0)
            out["y_trace_std"] = np.std(ys, axis=0)
        else:
            for ch in (0, 1):
                key = f"y{ch}"
                if key in data:
                    ys = np.array([np.asarray(d[key]) for d in self._average_buffer])
                    out[f"{key}_trace_avg"] = np.mean(ys, axis=0)
                    out[f"{key}_trace_std"] = np.std(ys, axis=0)
        return out

    def _plot_trace(self, data):
        if not self._figures.get("trace"):
            return
        ax = self._figures["trace"]["axis"]
        ax.clear()
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Voltage [V]")
        ax.set_title("Waveform")
        ax.grid(True, alpha=0.3)

        x = np.asarray(data.get("x", [])) if np is not None else data.get("x", [])
        show_avg = self._window["chkShowAverage"].get()
        show_std = self._window["chkShowStd"].get()

        if "y" in data:
            y = np.asarray(data["y"]) if np is not None else data["y"]
            ax.plot(x, y, label="Trace", linewidth=1.0)
            if self._averages > 1 and "y_trace_avg" in data:
                ax.plot(x, data["y_trace_avg"], label="Average", linewidth=1.5)
                if show_std and "y_trace_std" in data:
                    ax.fill_between(x, data["y_trace_avg"] - data["y_trace_std"], data["y_trace_avg"] + data["y_trace_std"], alpha=0.15)
        else:
            colors = ["#FFD700", "#1E90FF"]
            for ch in (0, 1):
                key = f"y{ch}"
                if key not in data:
                    continue
                ax.plot(x, data[key], label=f"CH{ch+1}", color=colors[ch], linewidth=1.0)
                if self._averages > 1 and f"{key}_trace_avg" in data:
                    ax.plot(x, data[f"{key}_trace_avg"], label=f"CH{ch+1} avg", linestyle="--")
                    if show_std and f"{key}_trace_std" in data:
                        ax.fill_between(
                            x,
                            data[f"{key}_trace_avg"] - data[f"{key}_trace_std"],
                            data[f"{key}_trace_avg"] + data[f"{key}_trace_std"],
                            alpha=0.12,
                            color=colors[ch],
                        )

        ax.legend(loc="upper right")
        self._figures["trace"]["fig_agg"].draw()

    def _plot_fft(self, data):
        if not self._figures.get("fft"):
            return
        ax = self._figures["fft"]["axis"]
        ax.clear()
        ax.set_xlabel("Frequency bin")
        ax.set_ylabel("Magnitude")
        ax.set_title("FFT")
        ax.grid(True, alpha=0.3)

        if "fft" in data and np is not None:
            for key, value in data["fft"].items():
                if key.endswith("_real") or key.endswith("_mag"):
                    ax.plot(np.asarray(value), label=key, linewidth=1.0)

        ax.legend()
        self._figures["fft"]["fig_agg"].draw()

    def _update_stats(self, data):
        lines = []
        if "means" in data:
            for k, v in data["means"].items():
                if isinstance(v, (int, float)) or (np is not None and isinstance(v, np.floating)):
                    lines.append(f"{k}: {float(v):.4g}")
        self._window["txtTraceStats"].update("\n".join(lines[:8]) or "-")

    def _acquire_once(self):
        if self._device is None:
            self.log("Acquire: not connected.", level="warning")
            self._window["txtStatus"].update("Not connected")
            return

        try:
            channels = self._get_requested_channels()
            data = self._device.query_waveform(channels, stats=["means", "fft"])
            if data is None:
                self.log("No data returned from device.", level="warning")
                self._window["txtStatus"].update("No data")
                return

            if self._averages > 1:
                data = self._average_trace(data)

            self._plot_trace(data)
            self._plot_fft(data)
            self._update_stats(data)
            self.log("Acquired OK.")
            self._window["txtStatus"].update("Acquired")
        except Exception as e:
            self.log(f"Acquire error: {e}", level="error")
            self.log(traceback.format_exc(), level="error")
            self._window["txtStatus"].update(f"Acquire error: {e}")

    def run(self):
        self.log("Entering main loop. Ready.")
        write_startup_log("Entering main event loop")
        while True:
            try:
                event, values = self._window.read(timeout=120 if self._running else None)
            except Exception as e:
                self.log(f"Window read error: {e}", level="error")
                write_startup_log(f"Window read error: {e}")
                break

            if event in (sg.WIN_CLOSED, "Exit"):
                self.log("Window closed.")
                break

            try:
                if event == "btnRefresh":
                    self._refresh_devices()
                elif event == "btnConnect":
                    self._connect_selected()
                elif event == "btnDisconnect":
                    self._disconnect_selected()
                elif event == "btnApply":
                    self._apply_settings()
                elif event == "btnAcquire":
                    self._acquire_once()
                elif event == "btnStart":
                    self._running = not self._running
                    self._window["btnStart"].update("Stop Continuous" if self._running else "Start Continuous")
                    self.log("Continuous " + ("started" if self._running else "stopped"))
                    if self._running:
                        self._window["txtStatus"].update("Continuous acquisition running")
                elif event == "btnForceTrigger":
                    if self._device is not None:
                        try:
                            self._device.force_trigger()
                            self.log("Trigger forced.")
                            self._window["txtStatus"].update("Trigger forced")
                        except Exception as e:
                            self.log(f"Force trigger failed: {e}", level="error")
                    else:
                        self.log("Force trigger: not connected.", level="warning")

                if self._running and self._device is not None:
                    self._acquire_once()
            except Exception as e:
                self.log(f"Event handler error: {e}", level="error")
                self.log(traceback.format_exc(), level="error")

        self._disconnect_selected()
        self._window.close()
        write_startup_log("GUI closed normally")


def main():
    write_startup_log("main() entered")
    try:
        app = HantekGUI()
        app.run()
    except Exception as e:
        tb = traceback.format_exc()
        write_startup_log(f"FATAL ERROR in main:\n{tb}")
        try:
            sg.popup_error(
                f"Fatal error:\n{e}\n\nFull traceback written to:\n{STARTUP_LOG}",
                title="Hantek GUI Crash"
            )
        except Exception:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "Hantek GUI Crash",
                    f"{e}\n\nSee log file:\n{STARTUP_LOG}"
                )
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
