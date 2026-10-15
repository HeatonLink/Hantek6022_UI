import PySimpleGUI as sg
import time
import json
import os

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
last_data = None
last_width = 0
zoom_x = 1.0
pan_start = 0.0
last_save = 0
current_values = {}
running = False

drag_start_x = None
drag_start_pan = 0.0

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".hantek6022_settings.json")

menu_def = [
    ["File", ["Save Settings", "Load Settings"]],
    ["Options", ["Device", ["Hantek 6022BE", "Hantek 6022BL"], "Show Log"]]
]

sample_rates = ["100kS/s", "200kS/s", "500kS/s", "1MS/s", "4MS/s", "8MS/s", "16MS/s", "24MS/s"]
num_samples = ["1000", "2000", "5000", "10000", "20000", "50000"]

channels_col = [
    [sg.Text("Channels", font=("Helvetica", 12, "bold"))],
    [sg.Checkbox("CH1", default=True, key="-CH1-", enable_events=True), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), key="-SCALE1-", enable_events=True), sg.Text("Probe"), sg.Combo(["1x", "10x"], default_value="1x", size=(5, 1), key="-PROBE1-", enable_events=True)],
    [sg.Checkbox("CH2", default=False, key="-CH2-", enable_events=True), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1), key="-SCALE2-", enable_events=True), sg.Text("Probe"), sg.Combo(["1x", "10x"], default_value="1x", size=(5, 1), key="-PROBE2-", enable_events=True)],
    [sg.Text("Sample Rate"), sg.Combo(sample_rates, default_value="1MS/s", size=(10, 1), key="-SRATE-", enable_events=True)],
    [sg.Text("Samples"), sg.Combo(num_samples, default_value="10000", size=(10, 1), key="-NSAMP-", enable_events=True)],
]

trigger_col = [
    [sg.Text("Trigger", font=("Helvetica", 12, "bold"))],
    [sg.Text("Source"), sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1), key="-TRIGSRC-", enable_events=True)],
    [sg.Text("Slope"), sg.Combo(["Rising", "Falling", "Both"], default_value="Rising", size=(8, 1), key="-SLOPE-", enable_events=True)],
    [sg.Text("Level"), sg.Input("0.0", size=(8, 1), key="-LEVEL-", enable_events=True), sg.Text("V")],
    [sg.Text("Position"), sg.Slider(range=(0, 100), default_value=50, orientation="h", size=(15, 15), key="-POS-", enable_events=True)],
    [sg.Radio("Auto", "MODE", default=True, key="-AUTO-", enable_events=True), sg.Radio("Normal", "MODE", key="-NORM-", enable_events=True), sg.Radio("Single", "MODE", key="-SINGLE-", enable_events=True)],
]

timebase_col = [
    [sg.Text("Timebase", font=("Helvetica", 12, "bold"))],
    [sg.Combo(["100us", "200us", "500us", "1ms", "2ms", "5ms", "10ms", "20ms"], default_value="1ms", size=(10, 1), key="-TB-", enable_events=True), sg.Text("/div")],
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
    [sg.Button("Acquire", key="-ACQ-", disabled=True), sg.Button("Run / Stop", key="-RUN-"), sg.Button("Force Trigger")],

    [sg.HorizontalSeparator()],
    [sg.Text("CH1: 0.00 V   CH2: 0.00 V", key="-READOUT-")],

    [sg.HorizontalSeparator()],
    [sg.Text("CH1 Waveform"), sg.Push(), sg.Text("Y min"), sg.Input("-4.0", size=(6, 1), key="-YMIN1-", enable_events=True), sg.Text("max"), sg.Input("4.0", size=(6, 1), key="-YMAX1-", enable_events=True), sg.Checkbox("Auto", key="-AUTO1-", enable_events=True)],
    [sg.Canvas(size=(600, 180), background_color="black", key="-WAVE1-", expand_x=True)],
    [sg.Text("CH2 Waveform"), sg.Push(), sg.Text("Y min"), sg.Input("-4.0", size=(6, 1), key="-YMIN2-", enable_events=True), sg.Text("max"), sg.Input("4.0", size=(6, 1), key="-YMAX2-", enable_events=True), sg.Checkbox("Auto", key="-AUTO2-", enable_events=True)],
    [sg.Canvas(size=(600, 180), background_color="black", key="-WAVE2-", expand_x=True)],
    [sg.Slider(range=(0, 100), default_value=0, orientation="h", size=(50, 15), key="-PAN-", expand_x=True, enable_events=True)],

    [sg.Text("Log", key="-LOGLABEL-", visible=False)],
    [sg.Multiline("GUI ready.\n", size=(70, 6), key="-LOG-", visible=False, expand_x=True)],
]

window = sg.Window("Hantek 6022", layout, resizable=True, finalize=True)

win_size = window.size
window.TKroot.minsize(win_size[0], win_size[1])
last_width = win_size[0]

def log(msg):
    try:
        current = window["-LOG-"].get()
        new_text = msg + "\n" + current
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
    window["-RUN-"].update(disabled=not connected)
    if not connected:
        window["-RUN-"].update(button_color=("white", "#444"))

def set_model(model):
    global selected_model, connected, device, running
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
        running = False
        set_status("Status: Waiting")

def safe_get(key, default=None):
    try:
        return window[key].get()
    except Exception:
        return current_values.get(key, default)

def get_probe_factor(key):
    p = safe_get(key, "1x")
    return 10.0 if str(p) == "10x" else 1.0

def get_settings():
    ch1 = bool(safe_get("-CH1-", True))
    ch2 = bool(safe_get("-CH2-", False))
    return {
        "model": selected_model,
        "ch1": ch1,
        "scale1": safe_get("-SCALE1-", "1V"),
        "probe1": safe_get("-PROBE1-", "1x"),
        "ch2": ch2,
        "scale2": safe_get("-SCALE2-", "1V"),
        "probe2": safe_get("-PROBE2-", "1x"),
        "srate": safe_get("-SRATE-", "1MS/s"),
        "nsamp": safe_get("-NSAMP-", "10000"),
        "trigsrc": safe_get("-TRIGSRC-", "CH1"),
        "slope": safe_get("-SLOPE-", "Rising"),
        "level": safe_get("-LEVEL-", "0.0"),
        "pos": safe_get("-POS-", 50),
        "mode": "Auto" if safe_get("-AUTO-", True) else ("Normal" if safe_get("-NORM-", False) else "Single"),
        "tb": safe_get("-TB-", "1ms"),
        "ymin1": safe_get("-YMIN1-", "-4.0"),
        "ymax1": safe_get("-YMAX1-", "4.0"),
        "auto1": bool(safe_get("-AUTO1-", False)),
        "ymin2": safe_get("-YMIN2-", "-4.0"),
        "ymax2": safe_get("-YMAX2-", "4.0"),
        "auto2": bool(safe_get("-AUTO2-", False)),
    }

def set_settings(s):
    global selected_model
    try:
        if "model" in s:
            set_model(s["model"])
        if "ch1" in s:
            window["-CH1-"].update(bool(s["ch1"]))
            log(f"Restored CH1={s['ch1']}")
        if "scale1" in s:
            window["-SCALE1-"].update(s["scale1"])
        if "probe1" in s:
            window["-PROBE1-"].update(s["probe1"])
        if "ch2" in s:
            window["-CH2-"].update(bool(s["ch2"]))
            log(f"Restored CH2={s['ch2']}")
        if "scale2" in s:
            window["-SCALE2-"].update(s["scale2"])
        if "probe2" in s:
            window["-PROBE2-"].update(s["probe2"])
        if "srate" in s:
            window["-SRATE-"].update(s["srate"])
        if "nsamp" in s:
            window["-NSAMP-"].update(s["nsamp"])
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
        if "ymin1" in s:
            window["-YMIN1-"].update(s["ymin1"])
        if "ymax1" in s:
            window["-YMAX1-"].update(s["ymax1"])
        if "auto1" in s:
            window["-AUTO1-"].update(bool(s["auto1"]))
        if "ymin2" in s:
            window["-YMIN2-"].update(s["ymin2"])
        if "ymax2" in s:
            window["-YMAX2-"].update(s["ymax2"])
        if "auto2" in s:
            window["-AUTO2-"].update(bool(s["auto2"]))
        log("Settings loaded")
    except Exception as e:
        log(f"Load settings error: {e}")

def auto_save():
    try:
        s = get_settings()
        with open(SETTINGS_FILE, "w") as f:
            json.dump(s, f, indent=2)
        log(f"Saved CH1={s['ch1']}, CH2={s['ch2']} to {SETTINGS_FILE}")
    except Exception as e:
        log(f"Auto-save failed: {e}")

def load_auto_settings():
    log(f"Looking for settings at {SETTINGS_FILE}")
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                s = json.load(f)
            set_settings(s)
            log("Restored previous settings")
        except Exception as e:
            log(f"Auto-load failed: {e}")
    else:
        log("No previous settings found")

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
        auto_save()
    except Exception as e:
        log(f"Load failed: {e}")

def parse_tb(s):
    try:
        if "us" in s:
            return float(s.replace("us", "")) * 1e-6
        if "ms" in s:
            return float(s.replace("ms", "")) * 1e-3
        return 1e-3
    except Exception:
        return 1e-3

def apply_settings():
    if not connected or device is None:
        return False
    try:
        ch1 = window["-CH1-"].get()
        ch2 = window["-CH2-"].get()
        device.set_channel_enable(0, ch1)
        device.set_channel_enable(1, ch2)

        scale1 = parse_scale(window["-SCALE1-"].get())
        device.set_channel_scale(0, scale1)

        scale2 = parse_scale(window["-SCALE2-"].get())
        device.set_channel_scale(1, scale2)

        tb = parse_tb(window["-TB-"].get())
        device.set_timebase_scale(tb)

        src = 0 if window["-TRIGSRC-"].get() == "CH1" else 1
        try:
            device.set_trigger_source(src)
        except Exception:
            pass

        slope = window["-SLOPE-"].get()
        try:
            device.set_trigger_slope(slope)
        except Exception:
            pass

        try:
            level = float(window["-LEVEL-"].get())
            device.set_trigger_level(src, level)
        except Exception:
            pass

        return True
    except Exception as e:
        log(f"Apply settings failed: {e}")
        return False

def try_connect():
    global connected, device, running
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
        log("Connecting to device...")
        device.connect()
        connected = True
        running = False
        set_status("Status: Connected")
        log("Connected")
        apply_settings()
        return True
    except Exception as e:
        log(f"Connect failed: {e}")
        connected = False
        device = None
        running = False
        set_status("Status: Failed")
        return False

def do_disconnect():
    global connected, device, running
    if device is not None:
        try:
            device.disconnect()
        except Exception:
            pass
    connected = False
    device = None
    running = False
    set_status("Status: Disconnected")
    log("Disconnected")

def to_list(arr):
    if arr is None:
        return []
    try:
        return list(arr)
    except Exception:
        return []

def parse_scale(s):
    try:
        if "mV" in s:
            return float(s.replace("mV", "")) / 1000
        return float(s.replace("V", ""))
    except Exception:
        return 1.0

def update_sliders():
    try:
        window["-PAN-"].update(value=int(pan_start * 100))
    except Exception:
        pass

def plot_trace(canvas_key, ydata, color, ymin_key, ymax_key, auto_key, probe_key, show_tb=False):
    canvas = window[canvas_key].TKCanvas
    canvas.delete("all")
    w = canvas.winfo_width() or 600
    h = canvas.winfo_height() or 180
    margin = 40

    for i in range(1, 8):
        y = margin + int((h - 2 * margin) * i / 8)
        canvas.create_line(margin, y, w - margin, y, fill="#333", dash=(2, 4))
    for i in range(1, 10):
        x = margin + int((w - 2 * margin) * i / 10)
        canvas.create_line(x, margin, x, h - margin, fill="#333", dash=(2, 4))

    canvas.create_line(margin, margin, margin, h - margin, fill="#888")
    canvas.create_line(margin, h - margin, w - margin, h - margin, fill="#888")

    ydata = to_list(ydata)
    auto = bool(safe_get(auto_key, False))

    if auto and len(ydata) >= 2:
        n = len(ydata)
        visible = max(2, int(n / zoom_x))
        max_start = max(0, n - visible)
        start = int(pan_start * max_start)
        end = min(n, start + visible)
        view = ydata[start:end]
        if len(view) >= 2:
            dmin = min(view)
            dmax = max(view)
            span = dmax - dmin
            if span == 0:
                span = 1.0
            ymin = dmin - 0.1 * span
            ymax = dmax + 0.1 * span
            window[ymin_key].update(f"{ymin:.3f}")
            window[ymax_key].update(f"{ymax:.3f}")
        else:
            ymin, ymax = -4.0, 4.0
    else:
        try:
            ymin = float(safe_get(ymin_key, "-4.0"))
            ymax = float(safe_get(ymax_key, "4.0"))
        except Exception:
            ymin, ymax = -4.0, 4.0

    if ymax == ymin:
        ymax = ymin + 1.0

    probe = get_probe_factor(probe_key)

    for i in range(9):
        y = margin + int((h - 2 * margin) * i / 8)
        v = (ymax - (ymax - ymin) * i / 8) * probe
        canvas.create_text(margin - 5, y, text=f"{v:.2f}", fill="#aaa", anchor="e", font=("Arial", 8))

    if show_tb:
        tb = window["-TB-"].get()
        canvas.create_text(w // 2, h - margin + 15, text=f"{tb}/div  (zoom {zoom_x:.1f}x)", fill="#aaa", font=("Arial", 9))

    if len(ydata) < 2:
        return
    n = len(ydata)
    visible = max(2, int(n / zoom_x))
    max_start = max(0, n - visible)
    start = int(pan_start * max_start)
    end = min(n, start + visible)
    view = ydata[start:end]
    if len(view) < 2:
        return

    pts = []
    vn = len(view)
    for i, val in enumerate(view):
        x = margin + int((w - 2 * margin) * i / max(vn - 1, 1))
        norm = (val - ymin) / (ymax - ymin)
        norm = max(0.0, min(1.0, norm))
        y = margin + int((h - 2 * margin) * (1.0 - norm))
        pts.extend([x, y])
    if len(pts) >= 4:
        canvas.create_line(pts, fill=color, width=1)

def draw_waveforms(data):
    if data is None:
        return
    y0 = data.get("y0") if data.get("y0") is not None else data.get("y")
    y1 = data.get("y1")
    plot_trace("-WAVE1-", y0, "#FFD700", "-YMIN1-", "-YMAX1-", "-AUTO1-", "-PROBE1-", show_tb=False)
    plot_trace("-WAVE2-", y1, "#00FFFF", "-YMIN2-", "-YMAX2-", "-AUTO2-", "-PROBE2-", show_tb=True)

def on_wheel(event, canvas_key):
    global zoom_x, pan_start
    delta = getattr(event, "delta", 0)
    if delta == 0:
        delta = 1 if getattr(event, "num", 0) == 4 else -1
    if delta > 0:
        zoom_x = min(20.0, zoom_x * 1.2)
    else:
        zoom_x = max(1.0, zoom_x / 1.2)
    if last_data is not None:
        draw_waveforms(last_data)
        update_sliders()

def on_press(event):
    global drag_start_x, drag_start_pan
    drag_start_x = event.x
    drag_start_pan = pan_start

def on_drag(event):
    global pan_start
    if drag_start_x is None or last_data is None:
        return
    dx = event.x - drag_start_x
    canvas = event.widget
    w = canvas.winfo_width() or 600
    fraction = -dx / max(w, 1)
    pan_start = max(0.0, min(1.0, drag_start_pan + fraction))
    draw_waveforms(last_data)
    update_sliders()

def on_release(event):
    global drag_start_x
    drag_start_x = None

def bind_events():
    for key in ("-WAVE1-", "-WAVE2-"):
        canvas = window[key].TKCanvas
        canvas.bind("<MouseWheel>", lambda e, k=key: on_wheel(e, k))
        canvas.bind("<Button-4>", lambda e, k=key: on_wheel(e, k))
        canvas.bind("<Button-5>", lambda e, k=key: on_wheel(e, k))
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

bind_events()

def do_acquire(quiet=False):
    global last_data, zoom_x, pan_start
    if not connected or device is None:
        if not quiet:
            log("Not connected")
        return False
    try:
        if not quiet:
            log("=== Acquire started ===")
        apply_settings()
        channels = []
        if window["-CH1-"].get():
            channels.append(0)
        if window["-CH2-"].get():
            channels.append(1)
        if not channels:
            channels = [0]
        data = device.query_waveform(channels)
        last_data = data
        y0 = to_list(data.get("y0") if data.get("y0") is not None else data.get("y"))
        y1 = to_list(data.get("y1"))
        p1 = get_probe_factor("-PROBE1-")
        p2 = get_probe_factor("-PROBE2-")
        m0 = (sum(y0) / len(y0) if len(y0) > 0 else 0.0) * p1
        m1 = (sum(y1) / len(y1) if len(y1) > 0 else 0.0) * p2
        window["-READOUT-"].update(f"CH1: {m0:.3f} V   CH2: {m1:.3f} V")
        draw_waveforms(data)
        update_sliders()
        if not quiet:
            log("=== Acquire done ===")
        return True
    except Exception as e:
        if not quiet:
            log(f"Acquire failed: {e}")
        return False

def ping():
    global connected, device, running
    if not connected or device is None:
        return
    try:
        _ = device.identify()
    except Exception as e:
        log(f"Ping failed: {e}")
        connected = False
        device = None
        running = False
        set_status("Status: Lost")

log(f"Settings file: {SETTINGS_FILE}")
load_auto_settings()
try_connect()

while True:
    event, values = window.read(timeout=200 if running else 500)
    current_values = values or {}

    if event in (sg.WIN_CLOSED, "Exit"):
        auto_save()
        break

    now = time.time()
    if now - last_save >= 2:
        auto_save()
        last_save = now

    current_width = window.size[0]
    if current_width != last_width and last_data is not None:
        draw_waveforms(last_data)
        last_width = current_width

    if event == "Save Settings":
        save_settings()

    if event == "Load Settings":
        load_settings()

    if event == "Hantek 6022BE":
        set_model("Hantek 6022BE")
        auto_save()

    if event == "Hantek 6022BL":
        set_model("Hantek 6022BL")
        auto_save()

    if event == "Show Log":
        toggle_log()

    if event == "-CONN-":
        try_connect()

    if event == "-DISC-":
        do_disconnect()

    if event == "-ACQ-":
        do_acquire()

    if event == "-RUN-":
        if connected:
            running = not running
            window["-RUN-"].update(button_color=("white", "red") if running else ("white", "#444"))
            log("Running" if running else "Stopped")

    if event == "-PAN-":
        pan_start = values[event] / 100.0
        if last_data is not None:
            draw_waveforms(last_data)

    if event in ("-CH1-", "-CH2-", "-SCALE1-", "-SCALE2-", "-PROBE1-", "-PROBE2-", "-SRATE-", "-NSAMP-",
                 "-TRIGSRC-", "-SLOPE-", "-LEVEL-", "-POS-", "-AUTO-", "-NORM-", "-SINGLE-", "-TB-",
                 "-YMIN1-", "-YMAX1-", "-AUTO1-", "-YMIN2-", "-YMAX2-", "-AUTO2-"):
        auto_save()
        last_save = now
        if last_data is not None:
            draw_waveforms(last_data)

    if running and connected:
        do_acquire(quiet=True)

    if connected and now - last_ping >= 5:
        ping()
        last_ping = now

if device is not None:
    try:
        device.disconnect()
    except Exception:
        pass

window.close()
