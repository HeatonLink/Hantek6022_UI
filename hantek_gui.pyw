#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hantek-style visual-only GUI
Uses PySimpleGUI (same as your working script).
"""

try:
    import PySimpleGUI as sg
except ImportError:
    try:
        import FreeSimpleGUI as sg
    except ImportError:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Missing library", "Need PySimpleGUI or FreeSimpleGUI\n\npip install PySimpleGUI")
        raise SystemExit(1)

sg.theme("DarkAmber")

layout = [
    [sg.Text("HANTEK 6022", font=("Helvetica", 16, "bold"))],
    [sg.Text("Visual only — no device connected")],
    [sg.HorizontalSeparator()],

    [sg.Text("Device"), sg.Combo(["No device"], default_value="No device", size=(20, 1), readonly=True)],
    [sg.Button("Refresh"), sg.Button("Connect")],

    [sg.HorizontalSeparator()],
    [sg.Text("Channels", font=("Helvetica", 11, "bold"))],
    [sg.Checkbox("CH1", default=True, text_color="gold"),
     sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), readonly=True)],
    [sg.Checkbox("CH2", default=False, text_color="cyan"),
     sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), readonly=True)],

    [sg.HorizontalSeparator()],
    [sg.Text("Timebase"), sg.Combo(["100us", "200us", "500us", "1ms", "2ms", "5ms", "10ms"], default_value="1ms", size=(10, 1), readonly=True)],

    [sg.HorizontalSeparator()],
    [sg.Text("Trigger", font=("Helvetica", 11, "bold"))],
    [sg.Text("Source"), sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1), readonly=True)],
    [sg.Text("Slope"), sg.Combo(["Rising", "Falling"], default_value="Rising", size=(8, 1), readonly=True)],
    [sg.Text("Level"), sg.Input("0.0", size=(8, 1)), sg.Text("V")],

    [sg.HorizontalSeparator()],
    [sg.Button("Single"), sg.Button("Run / Stop"), sg.Button("Force Trig")],

    [sg.HorizontalSeparator()],
    [sg.Text("Status: Stopped")],
    [sg.Text("0.00 V   0.00 V", text_color="gold")],

    [sg.HorizontalSeparator()],
    [sg.Text("Waveform")],
    [sg.Canvas(size=(700, 280), background_color="black", key="-WAVE-")],
    [sg.Text("FFT")],
    [sg.Canvas(size=(700, 160), background_color="black", key="-FFT-")],

    [sg.HorizontalSeparator()],
    [sg.Multiline("Visual mockup only.\nNo hardware.\n", size=(80, 4), disabled=True, key="-LOG-")],
]

window = sg.Window("Hantek 6022 Visual", layout, finalize=True, resizable=True)

# Draw a simple grid so the canvas looks like a scope
def draw_grid(key):
    c = window[key].TKCanvas
    w = c.winfo_width() or 700
    h = c.winfo_height() or 200
    c.delete("all")
    for i in range(1, 8):
        y = int(h * i / 8)
        c.create_line(0, y, w, y, fill="#333", dash=(2, 4))
    for i in range(1, 10):
        x = int(w * i / 10)
        c.create_line(x, 0, x, h, fill="#333", dash=(2, 4))
    c.create_line(w // 2, 0, w // 2, h, fill="#555")
    c.create_line(0, h // 2, w, h // 2, fill="#555")

window["-WAVE-"].TKCanvas.after(100, lambda: draw_grid("-WAVE-"))
window["-FFT-"].TKCanvas.after(100, lambda: draw_grid("-FFT-"))

while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, "Exit"):
        break

window.close()
