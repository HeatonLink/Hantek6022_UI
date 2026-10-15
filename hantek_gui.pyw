#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hantek 6022BE / 6022BL Simple GUI
=================================

A lightweight Python GUI for the Hantek DSO6022BE / 6022BL USB oscilloscope.

Dependencies (install with):
    pip install pyhantek6022[gui] matplotlib numpy FreeSimpleGUI

Usage:
    - Save as hantek_gui.pyw (Windows, no console) or hantek_gui.py
    - Plug in the scope
    - Run the script
    - Click Refresh → Connect → Start / Acquire

Notes:
    - Firmware is uploaded automatically if the device is uninitialized.
    - This is a simple control + visualization tool. For a full-featured
      oscilloscope application use OpenHantek6022:
      https://github.com/OpenHantek/OpenHantek6022

License: Based on the open-source pyhantek6022 project (BSD-3-Clause).
"""

import logging
import time
import sys

try:
    import FreeSimpleGUI as sg
except ImportError:
    print("FreeSimpleGUI is required. Install with: pip install FreeSimpleGUI")
    sys.exit(1)

import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    from labdevices.oscilloscope import (
        OscilloscopeRunMode,
        OscilloscopeSweepMode,
        OscilloscopeTriggerMode,
    )
    from pyhantek6022.dso6022be import DSO6022BE, get_dsos
    from pyhantek6022.firmwareupload import FirmwareUploader
except ImportError:
    print("pyhantek6022 is required. Install with: pip install 'pyhantek6022[gui]'")
    sys.exit(1)


class HantekGUI:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._logger.addHandler(logging.StreamHandler())
        self._logger.setLevel(logging.INFO)

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

        sg.theme("DarkAmber")

        layout = [
            [
                sg.Column(
                    [
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
                            sg.Combo(
                                ["RUN", "STOP", "SINGLE"],
                                default_value="RUN",
                                key="cmbRunMode",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Sweep mode"),
                            sg.Combo(
                                ["AUTO", "NORMAL", "SINGLE"],
                                default_value="AUTO",
                                key="cmbSweepMode",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Trigger mode"),
                            sg.Combo(
                                ["EDGE", "PULSE", "SLOPE"],
                                default_value="EDGE",
                                key="cmbTriggerMode",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Trigger source"),
                            sg.Combo(
                                ["CH1", "CH2"],
                                default_value="CH1",
                                key="cmbTriggerSource",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Trigger slope"),
                            sg.Combo(
                                ["positive", "negative", "both"],
                                default_value="positive",
                                key="cmbTriggerSlope",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Trigger level [V]"),
                            sg.InputText("0.0", key="txtTriggerLevel", size=(12, 1)),
                        ],
                        [
                            sg.Text("Trigger position"),
                            sg.InputText("0.5", key="txtTriggerPosition", size=(12, 1)),
                        ],
                        [
                            sg.Checkbox("Smooth trigger", key="chkTriggerSmooth", default=False)
                        ],
                        [sg.HorizontalSeparator()],
                        [
                            sg.Checkbox("CH1", key="chkCh0", default=True),
                            sg.Text("Scale"),
                            sg.Combo(
                                self._channel_scales,
                                default_value=1.0,
                                key="cmbScale0",
                                readonly=True,
                                size=(8, 1),
                            ),
                            sg.Text("Probe"),
                            sg.Combo(
                                self._probe_ratios,
                                default_value=1,
                                key="cmbProbe0",
                                readonly=True,
                                size=(8, 1),
                            ),
                        ],
                        [
                            sg.Checkbox("CH2", key="chkCh1", default=False),
                            sg.Text("Scale"),
                            sg.Combo(
                                self._channel_scales,
                                default_value=1.0,
                                key="cmbScale1",
                                readonly=True,
                                size=(8, 1),
                            ),
                            sg.Text("Probe"),
                            sg.Combo(
                                self._probe_ratios,
                                default_value=1,
                                key="cmbProbe1",
                                readonly=True,
                                size=(8, 1),
                            ),
                        ],
                        [
                            sg.Text("Timebase [s/div]"),
                            sg.Combo(
                                self._timebase_scales,
                                default_value=1e-3,
                                key="cmbTimebase",
                                readonly=True,
                                size=(12, 1),
                            ),
                        ],
                        [
                            sg.Text("Averages"),
                            sg.Combo(
                                [1, 2, 4, 8, 16, 32],
                                default_value=1,
                                key="cmbAverages",
                                readonly=True,
                                size=(8, 1),
                            ),
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
                        [
                            sg.Text("Status:"),
                            sg.Text("Not connected", key="txtStatus", size=(45, 2)),
                        ],
                        [
                            sg.Text("Stats:"),
                            sg.Text("-", key="txtTraceStats", size=(45, 5)),
                        ],
                    ],
                    vertical_alignment="t",
                ),
                sg.Column(
                    [
                        [sg.Canvas(key="canvTrace", size=(900, 320))],
                        [sg.Canvas(key="canvFFT", size=(900, 280))],
                    ],
                    vertical_alignment="t",
                ),
            ]
        ]

        self._window = sg.Window(
            "Hantek 6022 GUI",
            layout,
            finalize=True,
            resizable=True,
            location=(50, 50),
        )

        self._figures = {
            "trace": self._init_figure("canvTrace", "Time [s]", "Voltage [V]", "Waveform"),
            "fft": self._init_figure("canvFFT", "Frequency bin", "Magnitude", "FFT"),
        }

        self._refresh_devices()

    def _init_figure(self, canvas_name, xlabel, ylabel, title):
        fig = Figure(figsize=(9, 3.2), dpi=100)
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
        self._window["txtStatus"].update("Scanning devices & uploading firmware if needed...")
        self._window.refresh()

        try:
            uploaded = FirmwareUploader.init_all()
            if uploaded:
                time.sleep(2.5)
        except Exception as e:
            self._logger.warning(f"Firmware upload: {e}")

        self._devices = get_dsos() or []
        self._device_labels = []

        for i, dev in enumerate(self._devices):
            try:
                dso = DSO6022BE(dev)
                ident = dso.identify() or {}
                label = f"{ident.get('manufacturer', 'Hantek')} {ident.get('product', '6022')} SN:{ident.get('serial', '?')}"
            except Exception:
                label = f"Device {i}"
            self._device_labels.append(label)

        self._window["cmbDevice"].update(
            values=self._device_labels,
            value=self._device_labels[0] if self._device_labels else None,
        )
        self._window["txtStatus"].update(f"Found {len(self._devices)} device(s)")

    def _connect_selected(self):
        sel = self._window["cmbDevice"].get()
        if sel not in self._device_labels:
            self._window["txtStatus"].update("No device selected")
            return

        idx = self._device_labels.index(sel)
        try:
            self._device = DSO6022BE(self._devices[idx])
            self._device.connect()
            self._window["txtStatus"].update(f"Connected: {sel}")
            self._apply_settings()
        except Exception as e:
            self._window["txtStatus"].update(f"Connect failed: {e}")
            self._device = None

    def _disconnect_selected(self):
        if self._device is not None:
            try:
                self._device.disconnect()
            except Exception:
                pass
            self._device = None
        self._running = False
        self._average_buffer.clear()
        self._last_settings = None
        self._window["txtStatus"].update("Disconnected")

    def _apply_settings(self):
        if self._device is None:
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
            self._window["txtStatus"].update("Settings applied")
        except Exception as e:
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
        ax = self._figures["trace"]["axis"]
        ax.clear()
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Voltage [V]")
        ax.set_title("Waveform")
        ax.grid(True, alpha=0.3)

        x = np.asarray(data.get("x", []))
        show_avg = self._window["chkShowAverage"].get()
        show_std = self._window["chkShowStd"].get()

        if "y" in data:
            y = np.asarray(data["y"])
            ax.plot(x, y, label="Trace", linewidth=1.0)
            if self._averages > 1 and "y_trace_avg" in data:
                ax.plot(x, data["y_trace_avg"], label="Average", linewidth=1.5)
                if show_std and "y_trace_std" in data:
                    ax.fill_between(
                        x,
                        data["y_trace_avg"] - data["y_trace_std"],
                        data["y_trace_avg"] + data["y_trace_std"],
                        alpha=0.15,
                    )
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
        ax = self._figures["fft"]["axis"]
        ax.clear()
        ax.set_xlabel("Frequency bin")
        ax.set_ylabel("Magnitude")
        ax.set_title("FFT")
        ax.grid(True, alpha=0.3)

        if "fft" in data:
            for key, value in data["fft"].items():
                if key.endswith("_real") or key.endswith("_mag"):
                    ax.plot(np.asarray(value), label=key, linewidth=1.0)

        ax.legend()
        self._figures["fft"]["fig_agg"].draw()

    def _update_stats(self, data):
        lines = []
        if "means" in data:
            for k, v in data["means"].items():
                if isinstance(v, (int, float, np.floating)):
                    lines.append(f"{k}: {float(v):.4g}")
        self._window["txtTraceStats"].update("\n".join(lines[:8]) or "-")

    def _acquire_once(self):
        if self._device is None:
            self._window["txtStatus"].update("Not connected")
            return

        try:
            channels = self._get_requested_channels()
            stats = ["means", "fft"] if True else None
            data = self._device.query_waveform(channels, stats=stats)
            if data is None:
                self._window["txtStatus"].update("No data returned")
                return

            if self._averages > 1:
                data = self._average_trace(data)

            self._plot_trace(data)
            self._plot_fft(data)
            self._update_stats(data)
            self._window["txtStatus"].update("Acquired")
        except Exception as e:
            self._window["txtStatus"].update(f"Acquire error: {e}")
            self._logger.exception("Acquire failed")

    def run(self):
        while True:
            event, values = self._window.read(timeout=100 if self._running else None)

            if event in (sg.WIN_CLOSED, "Exit"):
                break

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
                if self._running:
                    self._window["txtStatus"].update("Continuous acquisition running")
            elif event == "btnForceTrigger":
                if self._device is not None:
                    try:
                        self._device.force_trigger()
                        self._window["txtStatus"].update("Trigger forced")
                    except Exception as e:
                        self._window["txtStatus"].update(f"Force trigger failed: {e}")

            if self._running and self._device is not None:
                self._acquire_once()

        self._disconnect_selected()
        self._window.close()


def main():
    try:
        app = HantekGUI()
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sg.popup_error(f"Fatal error:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
