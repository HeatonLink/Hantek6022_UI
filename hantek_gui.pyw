import PySimpleGUI as sg
import time
import json

sg.theme("DarkAmber")

try:
    from pyhantek6022.dso6022be import DSO6022BE, get_dsos
    from pyhantek6022.firmwareupload import FirmwareUploader
    DEVICE_OK = True
except Exception:
    DEVICE_OK = False
    DSO6022BE = None
    get_dsos = None
    FirmwareUploader = None

selected_model = "Hantek 6022BE"
connected = False
device = None
last_ping = 0
log_visible = False

menu_def = [
    ["File", ["Save Settings", "Load Settings"]],
    ["Options", ["Device", ["Hantek 6022BE", "Hantek 6022BL"], "Show Log"]]
]

channels_col = [
    [sg.Text("Channels", font=("Helvetica", 12, "bold"))],
    [sg.Checkbox("CH1", default=True, key="-CH1-"), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), key="-SCALE1-")],
    [sg.Checkbox("CH2", default=False, key="-CH2-"), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), key="-SCALE2-")],
]

trigger_col = [
    [sg.Text("Trigger", font=("Helvetica", 12, "bold"))],
    [sg.Text("Source"), sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1), key="-TRIGSRC-")],
    [sg.Text("Slope"), sg.Combo(["Rising", "Falling", "Both"], default_value="Rising", size=(8, 1), key="-SLOPE-")],
    [sg.Text("Level"), sg.Input("0.0", size=(8, 1), key="-LEVEL-"), sg.Text("V")],
    [sg.Text("Position"), sg.Slider(range=(0, 100), default_value=50, orientation="h", size=(15, 15), key="-POS-")],
    [sg.Radio("Auto", "MODE", default=True, key="-AUTO-"), sg.Radio("Normal", "MODE", key="-NORM-"), sg.Radio("Single", "MODE", key="-SINGLE-")],
]

timebase_col = [
    [sg.Text("Timebase", font=("Helvetica", 12, "bold"))],
    [sg.Combo(["100us", "200us", "500us", "1ms", "2ms", "5ms", "10ms", "20ms"], default_value="1ms", size=(10, 1), key="-TB-"), sg.Text("/div")],
]

layout = [
    [sg.Menu(menu_def, key="-MENU-")],
    [sg.Text("Hantek 6022BE", font=("Helvetica", 16, "bold"), key="-TITLE-"),
     sg.Push(),
     sg.Button("Connect", key="-CONN-", size=(12, 1)),
     sg.Button("Disconnect", key="-DISC-", size=(12, 1)),
     sg.Text("Status: Waiting", key="-STATUS-")],
    [sg.HorizontalSeparator()],

    [sg.Column(channels_col, vertical_alignment="top"), sg.VSeparator(),
     sg.Column(trigger_col, vertical_alignment="top"), sg.VSeparator(),
     sg.Column(timebase_col, vertical_alignment="top")],

    [sg.HorizontalSeparator()],
    [sg.Button("Apply"), sg.Button("Acquire", key="-ACQ-", disabled=True), sg.Button("Run / Stop"), sg.Button("Force Trigger")],

    [sg.HorizontalSeparator()],
    [sg.Text("CH1: 0.00 V   CH2: 0.00 V", key="-READOUT-")],

    [sg.HorizontalSeparator()],
    [sg.Text("Waveform")],
    [sg.Canvas(size=(600, 250), background_color="black", key="-WAVE-")],
    [sg.Text("FFT")],
    [sg.Canvas(size=(600, 150), background_color="black")],

    [sg.Text("Log", key="-LOGLABEL-", visible=False)],
    [sg.Multiline("GUI ready.\n\n", size=(70, 6), key="-LOG-", visible=False)],
]

window = sg.Window("Hantek 6022", layout, resizable=True, finalize=True)

def log(msg):
    try:
        current = window["-LOG-"].get()
        new_text = msg + "\n\n" + current
        lines = new_text.splitlines(keepends=True)
        if len(lines) > 40:
            new_text = "".join(lines[:40])
        window["-LOG-"].update(new_text)
    except Exception:
        pass

def toggle_log():
    global log_visible
    log_visible = not log_visible
    window["-LOG-"].update(visible=log_visible)
    window["-LOGLABEL-"].update(visible=log_visible)

def set_status(text):
    window["-STATUS-"].update(text)
    window["-CONN-"].update(disabled=connected)
    window["-ACQ-"].update(disabled=not connected)

def set_model(model):
    global selected_model, connected, device
    if model == selected_model:
        return
    selected_model = model
    window["-TITLE-"].update(selected_model)
    log(f"Model set to {selected_model}")
    if connected and device is not None:
        try:
            device.disconnect()
        except Exception:
            pass
        connected = False
        device = None
        set_status("Status: Waiting")

def get_settings():
    return {
        "model": selected_model,
        "ch1": window["-CH1-"].get(),
        "scale1": window["-SCALE1-"].get(),
        "ch2": window["-CH2-"].get(),
        "scale2": window["-SCALE2-"].get(),
        "trigsrc": window["-TRIGSRC-"].get(),
        "slope": window["-SLOPE-"].get(),
        "level": window["-LEVEL-"].get(),
        "pos": window["-POS-"].get(),
        "mode": "Auto" if window["-AUTO-"].get() else ("Normal" if window["-NORM-"].get() else "Single"),
        "tb": window["-TB-"].get(),
    }

def set_settings(s):
    global selected_model
    try:
        if "model" in s:
            set_model(s["model"])
        if "ch1" in s:
            window["-CH1-"].update(s["ch1"])
        if "scale1" in s:
            window["-SCALE1-"].update(s["scale1"])
        if "ch2" in s:
            window["-CH2-"].update(s["ch2"])
        if "scale2" in s:
            window["-SCALE2-"].update(s["scale2"])
        if "trigsrc" in s:
            window["-TRIGSRC-"].update(s["trigsrc"])
        if "slope" in s:
            window["-SLOPE-"].update(s["slope"])
        if "level" in s:
            window["-LEVEL-"].update(s["level"])
        if "pos" in s:
            window["-POS-"].update(s["pos"])
        if "mode" in s:
            window["-AUTO-"].update(s["mode"] == "Auto")
            window["-NORM-"].update(s["mode"] == "Normal")
            window["-SINGLE-"].update(s["mode"] == "Single")
        if "tb" in s:
            window["-TB-"].update(s["tb"])
        log("Settings loaded")
    except Exception as e:
        log(f"Load settings error: {e}")

def save_settings():
    path = sg.popup_get_file("Save settings", save_as=True, file_types=(("JSON", "*.json"),), default_extension=".json", no_window=True)
    if not path:
        return
    try:
        with open(path, "w") as f:
            json.dump(get_settings(), f, indent=2)
        log(f"Settings saved to {path}")
    except Exception as e:
        log(f"Save failed: {e}")

def load_settings():
    path = sg.popup_get_file("Load settings", file_types=(("JSON", "*.json"),), no_window=True)
    if not path:
        return
    try:
        with open(path, "r") as f:
            s = json.load(f)
        set_settings(s)
    except Exception as e:
        log(f"Load failed: {e}")

def try_connect():
    global connected, device
    if not DEVICE_OK:
        log("Device library not installed (pip install pyhantek6022)")
        set_status("Status: No library")
        return False
    try:
        log(f"Trying to connect to {selected_model}...")
        set_status("Status: Connecting...")

        try:
            uploader = FirmwareUploader()
            pending = uploader.find_devs()
            log(f"Uninitialized devices found: {len(pending) if pending else 0}")
            if pending:
                log("Uploading firmware...")
                uploaded = FirmwareUploader.init_all()
                log(f"Firmware upload result: {uploaded}")
                if uploaded:
                    time.sleep(2)
        except Exception as e:
            log(f"Firmware step error: {e}")

        dsos = get_dsos() or []
        log(f"Initialized devices found: {len(dsos)}")
        if not dsos:
            log("No device found after firmware step")
            set_status("Status: No device")
            return False

        device = DSO6022BE(dsos[0])
        device.connect()
        connected = True
        set_status("Status: Connected")
        log("Connected")
        return True
    except Exception as e:
        log(f"Connect failed: {e}")
        connected = False
        device = None
        set_status("Status: Failed")
        return False

def do_disconnect():
    global connected, device
    if device is not None:
        try:
            device.disconnect()
        except Exception:
            pass
    connected = False
    device = None
    set_status("Status: Disconnected")
    log("Disconnected")

def plot_trace(canvas, ydata, color, w, h, margin):
    if not ydata or len(ydata) < 2:
        return
    n = len(ydata)
    pts = []
    ymin, ymax = min(ydata), max(ydata)
    if ymax == ymin:
        ymax = ymin + 1
    for i, val in enumerate(ydata):
        x = margin + int((w - 2 * margin) * i / max(n - 1, 1))
        y = margin + int((h - 2 * margin) * (1 - (val - ymin) / (ymax - ymin)))
        pts.extend([x, y])
    if len(pts) >= 4:
        canvas.create_line(pts, fill=color, width=1)

def draw_waveform(data):
    canvas = window["-WAVE-"].TKCanvas
    canvas.delete("all")
    w = canvas.winfo_width() or 600
    h = canvas.winfo_height() or 250
    margin = 40

    # Grid
    for i in range(1, 8):
        y = margin + int((h - 2 * margin) * i / 8)
        canvas.create_line(margin, y, w - margin, y, fill="#333", dash=(2, 4))
    for i in range(1, 10):
        x = margin + int((w - 2 * margin) * i / 10)
        canvas.create_line(x, margin, x, h - margin, fill="#333", dash=(2, 4))

    # Axes
    canvas.create_line(margin, margin, margin, h - margin, fill="#888")
    canvas.create_line(margin, h - margin, w - margin, h - margin, fill="#888")

    # Voltage scale (left) - use CH1 scale
    scale_v = 1.0
    try:
        s = window["-SCALE1-"].get()
        if "mV" in s:
            scale_v = float(s.replace("mV", "")) / 1000
        else:
            scale_v = float(s.replace("V", ""))
    except Exception:
        pass
    for i in range(9):
        y = margin + int((h - 2 * margin) * i / 8)
        v = (4 - i) * scale_v
        canvas.create_text(margin - 5, y, text=f"{v:.2f}", fill="#aaa", anchor="e", font=("Arial", 8))

    # Time scale (bottom)
    tb = window["-TB-"].get()
    canvas.create_text(w // 2, h - margin + 15, text=f"{tb}/div", fill="#aaa", font=("Arial", 9))

    # Plot CH1 (yellow) and CH2 (cyan)
    y0 = data.get("y0") or data.get("y") or []
    y1 = data.get("y1") or []
    plot_trace(canvas, y0, "#FFD700", w, h, margin)
    plot_trace(canvas, y1, "#00FFFF", w, h, margin)

def do_acquire():
    if not connected or device is None:
        log("Not connected")
        return
    try:
        log("Acquiring...")
        channels = []
        if window["-CH1-"].get():
            channels.append(0)
        if window["-CH2-"].get():
            channels.append(1)
        if not channels:
            channels = [0]
        data = device.query_waveform(channels)
        y0 = data.get("y0") or data.get("y") or []
        y1 = data.get("y1") or []
        log(f"Acquired CH1: {len(y0)} samples, CH2: {len(y1)} samples")
        m0 = sum(y0) / len(y0) if y0 else 0.0
        m1 = sum(y1) / len(y1) if y1 else 0.0
        window["-READOUT-"].update(f"CH1: {m0:.3f} V   CH2: {m1:.3f} V")
        draw_waveform(data)
        log("Acquire done")
    except Exception as e:
        log(f"Acquire failed: {e}")

def ping():
    global connected, device
    if not connected or device is None:
        return
    try:
        _ = device.identify()
        log("Ping OK")
    except Exception as e:
        log(f"Ping failed: {e}")
        connected = False
        device = None
        set_status("Status: Lost")

# Try to connect once on startup
try_connect()

while True:
    event, values = window.read(timeout=500)

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    if event == "Save Settings":
        save_settings()

    if event == "Load Settings":
        load_settings()

    if event == "Hantek 6022BE":
        set_model("Hantek 6022BE")

    if event == "Hantek 6022BL":
        set_model("Hantek 6022BL")

    if event == "Show Log":
        toggle_log()

    if event == "-CONN-":
        try_connect()

    if event == "-DISC-":
        do_disconnect()

    if event == "-ACQ-":
        do_acquire()

    # Only ping while connected (no auto-connect)
    now = time.time()
    if connected and now - last_ping >= 5:
        ping()
        last_ping = now

if device is not None:
    try:
        device.disconnect()
    except Exception:
        pass

window.close()
