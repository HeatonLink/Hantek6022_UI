import PySimpleGUI as sg
import time

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

menu_def = [["Options", ["Device", ["Hantek 6022BE", "Hantek 6022BL"], "Show Log"]]]

channels_col = [
    [sg.Text("Channels", font=("Helvetica", 12, "bold"))],
    [sg.Checkbox("CH1", default=True), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1))],
    [sg.Checkbox("CH2", default=False), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1))],
]

trigger_col = [
    [sg.Text("Trigger", font=("Helvetica", 12, "bold"))],
    [sg.Text("Source"), sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1))],
    [sg.Text("Slope"), sg.Combo(["Rising", "Falling", "Both"], default_value="Rising", size=(8, 1))],
    [sg.Text("Level"), sg.Input("0.0", size=(8, 1)), sg.Text("V")],
    [sg.Text("Position"), sg.Slider(range=(0, 100), default_value=50, orientation="h", size=(15, 15))],
    [sg.Radio("Auto", "MODE", default=True), sg.Radio("Normal", "MODE"), sg.Radio("Single", "MODE")],
]

timebase_col = [
    [sg.Text("Timebase", font=("Helvetica", 12, "bold"))],
    [sg.Combo(["100us", "200us", "500us", "1ms", "2ms", "5ms", "10ms", "20ms"], default_value="1ms", size=(10, 1)), sg.Text("/div")],
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
    [sg.Button("Apply"), sg.Button("Acquire"), sg.Button("Run / Stop"), sg.Button("Force Trigger")],

    [sg.HorizontalSeparator()],
    [sg.Text("CH1: 0.00 V   CH2: 0.00 V")],

    [sg.HorizontalSeparator()],
    [sg.Text("Waveform")],
    [sg.Canvas(size=(600, 250), background_color="black")],
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
