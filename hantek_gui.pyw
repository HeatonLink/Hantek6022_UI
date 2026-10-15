#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hantek 6022 Visual-Only GUI (placeholder)
=========================================

Just the look and feel. No device connection, no real functionality.
Double-click to open the window.
"""

import FreeSimpleGUI as sg

sg.theme("DarkAmber")

# Fake data for the plot area labels
left_col = [
    [sg.Text("Device")],
    [sg.Combo(["(not connected)"], default_value="(not connected)", key="cmbDevice", size=(40, 1), readonly=True),
     sg.Button("Refresh", key="btnRefresh", disabled=True)],
    [sg.Button("Connect", key="btnConnect", disabled=True),
     sg.Button("Disconnect", key="btnDisconnect", disabled=True)],
    [sg.HorizontalSeparator()],
    [sg.Text("Run mode"), sg.Combo(["RUN", "STOP", "SINGLE"], default_value="RUN", key="cmbRunMode", readonly=True, size=(12, 1))],
    [sg.Text("Sweep mode"), sg.Combo(["AUTO", "NORMAL", "SINGLE"], default_value="AUTO", key="cmbSweepMode", readonly=True, size=(12, 1))],
    [sg.Text("Trigger mode"), sg.Combo(["EDGE", "PULSE", "SLOPE"], default_value="EDGE", key="cmbTriggerMode", readonly=True, size=(12, 1))],
    [sg.Text("Trigger source"), sg.Combo(["CH1", "CH2"], default_value="CH1", key="cmbTriggerSource", readonly=True, size=(12, 1))],
    [sg.Text("Trigger slope"), sg.Combo(["positive", "negative", "both"], default_value="positive", key="cmbTriggerSlope", readonly=True, size=(12, 1))],
    [sg.Text("Trigger level [V]"), sg.InputText("0.0", key="txtTriggerLevel", size=(12, 1))],
    [sg.Text("Trigger position"), sg.InputText("0.5", key="txtTriggerPosition", size=(12, 1))],
    [sg.Checkbox("Smooth trigger", key="chkTriggerSmooth", default=False)],
    [sg.HorizontalSeparator()],
    [sg.Checkbox("CH1", key="chkCh0", default=True),
     sg.Text("Scale"), sg.Combo([0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0], default_value=1.0, key="cmbScale0", readonly=True, size=(8, 1)),
     sg.Text("Probe"), sg.Combo([1, 10, 100], default_value=1, key="cmbProbe0", readonly=True, size=(8, 1))],
    [sg.Checkbox("CH2", key="chkCh1", default=False),
     sg.Text("Scale"), sg.Combo([0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0], default_value=1.0, key="cmbScale1", readonly=True, size=(8, 1)),
     sg.Text("Probe"), sg.Combo([1, 10, 100], default_value=1, key="cmbProbe1", readonly=True, size=(8, 1))],
    [sg.Text("Timebase [s/div]"), sg.Combo(["100µs", "200µs", "500µs", "1ms", "2ms", "5ms", "10ms"], default_value="1ms", key="cmbTimebase", readonly=True, size=(12, 1))],
    [sg.Text("Averages"), sg.Combo([1, 2, 4, 8, 16], default_value=1, key="cmbAverages", readonly=True, size=(8, 1))],
    [sg.Checkbox("Show average", key="chkShowAverage", default=True),
     sg.Checkbox("Show std dev", key="chkShowStd", default=False)],
    [sg.HorizontalSeparator()],
    [sg.Button("Apply", key="btnApply", disabled=True),
     sg.Button("Acquire", key="btnAcquire", disabled=True),
     sg.Button("Start Continuous", key="btnStart", disabled=True),
     sg.Button("Force Trigger", key="btnForceTrigger", disabled=True)],
    [sg.Text("Status:"), sg.Text("Visual only — not connected", key="txtStatus", size=(40, 2))],
    [sg.Text("Stats:"), sg.Text("-", key="txtTraceStats", size=(40, 4))],
]

right_col = [
    [sg.Text("Waveform (placeholder)", font=("Helvetica", 12))],
    [sg.Canvas(key="canvTrace", size=(900, 280), background_color="#1a1a1a")],
    [sg.Text("FFT (placeholder)", font=("Helvetica", 12))],
    [sg.Canvas(key="canvFFT", size=(900, 240), background_color="#1a1a1a")],
]

layout = [
    [sg.Column(left_col, vertical_alignment="t"), sg.Column(right_col, vertical_alignment="t")],
    [sg.HorizontalSeparator()],
    [sg.Text("Log:")],
    [sg.Multiline("GUI opened.\nThis is a visual-only mockup.\nNo device connection or acquisition.\n",
                  size=(140, 8), key="-LOG-", autoscroll=True, disabled=True,
                  font=("Consolas", 9), background_color="#1e1e1e", text_color="#d4d4d4")],
]

window = sg.Window(
    "Hantek 6022 GUI (Visual Only)",
    layout,
    finalize=True,
    resizable=True,
    location=(40, 40),
)

# Simple event loop that does nothing useful
while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, "Exit"):
        break
    # All buttons are disabled or do nothing

window.close()
