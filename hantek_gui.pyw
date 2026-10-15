import PySimpleGUI as sg
import time

sg.theme("DarkAmber")

# Device library is optional — GUI still opens if missing
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
last_action = 0

def build_menu():
    be = "\u2713 Hantek 6022BE" if selected_model == "Hantek 6022BE" else "Hantek 6022BE"
    bl = "\u2713 Hantek 6022BL" if selected_model == "Hantek 6022BL" else "Hantek 6022BL"
    return [["Options", ["Device", [be, bl]]]]

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
    [sg.Menu(build_menu(), key="-MENU-")],
    [sg.Text("Hantek 6022BE", font=("Helvetica", 16, "bold"), key="-TITLE-")],
    [sg.HorizontalSeparator()],

    [sg.Column(channels_col, vertical_alignment="top"), sg.VSeparator(),
     sg.Column(trigger_col, vertical_alignment="top"), sg.VSeparator(),
     sg.Column(timebase_col, vertical_alignment="top")],

    [sg.HorizontalSeparator()],
    [sg.Button("Apply"), sg.Button("Acquire"), sg.Button("Run / Stop"), sg.Button("Force Trigger")],

    [sg.HorizontalSeparator()],
    [sg.Text("Status: Waiting", key="-STATUS-")],
    [sg.Text("CH1: 0.00 V   CH2: 0.00 V")],

    [sg.HorizontalSeparator()],
    [sg.Text("Waveform")],
    [sg.Canvas(size=(600, 250), background_color="black")],
    [sg.Text("FFT")],
    [sg.Canvas(size=(600, 150), background_color="black")],

    [sg.HorizontalSeparator()],
    [sg.Text("Log")],
    [sg.Multiline("GUI ready. Default model: Hantek 6022BE\n", size=(70, 6), key="-LOG-")],
]

window = sg.Window("Hantek 6022", layout, resizable=True, finalize=True)

def log(msg):
    current = window["-LOG-"].get()
    lines = (current + msg + "\n").splitlines()[-30:]
    window["-LOG-"].update("\n".join(lines) + "\n")

def set_model(model):
    global selected_model, connected, device
    if model == selected_model:
        return
    selected_model = model
    window["-TITLE-"].update(selected_model)
    window["-MENU-"].update(menu_definition=build_menu())
    log(f"Model set to {selected_model}")
    if connected and device is not None:
        try:
            device.disconnect()
        except Exception:
            pass
        connected = False
        device = None
        window["-STATUS-"].update("Status: Waiting")

def try_connect():
    global connected, device
    if not DEVICE_OK:
        log("Device library not installed (pip install pyhantek6022)")
        return False
    try:
        log(f"Trying to connect to {selected_model}...")
        try:
            FirmwareUploader.init_all()
        except Exception:
            pass
        dsos = get_dsos() or []
        if not dsos:
            log("No device found")
            return False
        device = DSO6022BE(dsos[0])
        device.connect()
        connected = True
        window["-STATUS-"].update("Status: Connected")
        log("Connected")
        return True
    except Exception as e:
        log(f"Connect failed: {e}")
        connected = False
        device = None
        window["-STATUS-"].update("Status: Not connected")
        return False

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
        window["-STATUS-"].update("Status: Disconnected")

while True:
    event, values = window.read(timeout=500)

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    if event in ("Hantek 6022BE", "\u2713 Hantek 6022BE"):
        set_model("Hantek 6022BE")

    if event in ("Hantek 6022BL", "\u2713 Hantek 6022BL"):
        set_model("Hantek 6022BL")

    # Every 5 seconds: try connect if not connected, or ping if connected
    now = time.time()
    if now - last_action >= 5:
        if not connected:
            try_connect()
        else:
            ping()
        last_action = now

if device is not None:
    try:
        device.disconnect()
    except Exception:
        pass

window.close()
