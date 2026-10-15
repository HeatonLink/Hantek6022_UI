#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hantek 6022 Visual-Only GUI
===========================

Looks like a real oscilloscope interface. No device connection.
Requires: pip install FreeSimpleGUI
"""

import FreeSimpleGUI as sg

# Dark scope-like theme
sg.theme("DarkGrey13")
sg.set_options(font=("Segoe UI", 10), element_padding=(2, 2))

# Colors that match typical DSO software
BG = "#1e1e1e"
PANEL = "#2d2d2d"
GRID = "#3a3a3a"
CH1 = "#FFD700"
CH2 = "#00BFFF"
TEXT = "#e0e0e0"
ACCENT = "#ff8c00"

def make_plot_canvas(key, height):
    return sg.Canvas(
        key=key,
        size=(820, height),
        background_color="#0f0f0f",
        pad=(0, 0),
    )

# Left control panel
controls = [
    [sg.Text("HANTEK 6022", font=("Segoe UI", 14, "bold"), text_color=ACCENT, background_color=PANEL)],
    [sg.Text("Visual Mockup", font=("Segoe UI", 9), text_color="#888", background_color=PANEL)],
    [sg.HorizontalSeparator(color="#444")],

    [sg.Text("Device", background_color=PANEL), sg.Push(background_color=PANEL)],
    [sg.Combo(["No device", "Hantek 6022BE", "Hantek 6022BL"],
              default_value="No device", key="-DEV-", size=(22, 1), readonly=True)],
    [sg.Button("Refresh", size=(10, 1)), sg.Button("Connect", size=(10, 1), button_color=("white", "#2a6"))],

    [sg.HorizontalSeparator(color="#444")],
    [sg.Text("Channels", font=("Segoe UI", 11, "bold"), text_color=TEXT, background_color=PANEL)],

    [sg.Checkbox("CH1", default=True, key="-CH1-", text_color=CH1, background_color=PANEL),
     sg.Text("1 V/div", size=(8, 1), background_color=PANEL),
     sg.Combo(["50 mV", "100 mV", "200 mV", "500 mV", "1 V", "2 V", "5 V"],
              default_value="1 V", size=(8, 1), key="-SCALE1-", readonly=True)],

    [sg.Checkbox("CH2", default=False, key="-CH2-", text_color=CH2, background_color=PANEL),
     sg.Text("1 V/div", size=(8, 1), background_color=PANEL),
     sg.Combo(["50 mV", "100 mV", "200 mV", "500 mV", "1 V", "2 V", "5 V"],
              default_value="1 V", size=(8, 1), key="-SCALE2-", readonly=True)],

    [sg.HorizontalSeparator(color="#444")],
    [sg.Text("Timebase", font=("Segoe UI", 11, "bold"), text_color=TEXT, background_color=PANEL)],
    [sg.Combo(["100 µs", "200 µs", "500 µs", "1 ms", "2 ms", "5 ms", "10 ms", "20 ms"],
              default_value="1 ms", size=(12, 1), key="-TB-", readonly=True),
     sg.Text("/div", background_color=PANEL)],

    [sg.HorizontalSeparator(color="#444")],
    [sg.Text("Trigger", font=("Segoe UI", 11, "bold"), text_color=TEXT, background_color=PANEL)],
    [sg.Text("Source", background_color=PANEL),
     sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1), key="-TSRC-", readonly=True)],
    [sg.Text("Slope", background_color=PANEL),
     sg.Combo(["Rising", "Falling", "Both"], default_value="Rising", size=(8, 1), key="-TSLOPE-", readonly=True)],
    [sg.Text("Level", background_color=PANEL),
     sg.Input("0.0", size=(8, 1), key="-TLEVEL-"), sg.Text("V", background_color=PANEL)],
    [sg.Text("Mode", background_color=PANEL),
     sg.Combo(["Auto", "Normal", "Single"], default_value="Auto", size=(8, 1), key="-TMODE-", readonly=True)],

    [sg.HorizontalSeparator(color="#444")],
    [sg.Button("Single", size=(10, 1), button_color=("white", "#555")),
     sg.Button("Run / Stop", size=(12, 1), button_color=("white", "#c60"))],
    [sg.Button("Force Trig", size=(10, 1)), sg.Button("Auto Setup", size=(12, 1))],

    [sg.HorizontalSeparator(color="#444")],
    [sg.Text("Status", font=("Segoe UI", 10, "bold"), text_color=TEXT, background_color=PANEL)],
    [sg.Text("Stopped", key="-STATUS-", size=(28, 1), text_color="#aaa", background_color=PANEL)],
    [sg.Text("0.00 V   0.00 V", key="-READOUT-", size=(28, 1), text_color=CH1, background_color=PANEL)],
]

# Right side: waveform + FFT placeholders
plots = [
    [sg.Text("CH1", text_color=CH1, background_color="#0f0f0f", font=("Segoe UI", 9, "bold")),
     sg.Text("CH2", text_color=CH2, background_color="#0f0f0f", font=("Segoe UI", 9, "bold")),
     sg.Push(background_color="#0f0f0f"),
     sg.Text("1.00 ms/div", text_color="#888", background_color="#0f0f0f")],
    [make_plot_canvas("-WAVE-", 340)],
    [sg.Text("FFT", text_color="#aaa", background_color="#0f0f0f", font=("Segoe UI", 9))],
    [make_plot_canvas("-FFT-", 200)],
]

layout = [
    [sg.Column(controls, background_color=PANEL, pad=(0, 0), vertical_alignment="top"),
     sg.VSeparator(color="#333"),
     sg.Column(plots, background_color="#0f0f0f", pad=(4, 4), vertical_alignment="top")],
    [sg.HorizontalSeparator(color="#333")],
    [sg.Multiline("Visual-only Hantek-style interface.\nNo hardware connected.\n",
                  size=(120, 5), key="-LOG-", disabled=True,
                  font=("Consolas", 9), background_color="#111", text_color="#bbb",
                  no_scrollbar=False)],
]

window = sg.Window(
    "Hantek 6022 — Visual",
    layout,
    finalize=True,
    resizable=True,
    background_color=BG,
    margins=(8, 8),
    location=(60, 40),
    icon=None,
)

# Draw simple grid lines on the canvases so it looks like a scope
def draw_grid(canvas_key, color="#222"):
    canvas = window[canvas_key].TKCanvas
    w = int(canvas["width"])
    h = int(canvas["height"])
    # Clear
    canvas.delete("all")
    # Horizontal lines
    for i in range(1, 8):
        y = int(h * i / 8)
        canvas.create_line(0, y, w, y, fill=color, dash=(2, 4))
    # Vertical lines
    for i in range(1, 10):
        x = int(w * i / 10)
        canvas.create_line(x, 0, x, h, fill=color, dash=(2, 4))
    # Center cross
    canvas.create_line(w // 2, 0, w // 2, h, fill="#444", width=1)
    canvas.create_line(0, h // 2, w, h // 2, fill="#444", width=1)

draw_grid("-WAVE-")
draw_grid("-FFT-")

# Idle event loop — buttons do nothing useful
while True:
    event, values = window.read(timeout=200)
    if event in (sg.WIN_CLOSED, "Exit"):
        break

window.close()
