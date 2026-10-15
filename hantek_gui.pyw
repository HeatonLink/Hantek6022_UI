import PySimpleGUI as sg

sg.theme("DarkAmber")

layout = [
    [sg.Text("HANTEK 6022", font=("Helvetica", 16, "bold"))],
    [sg.Text("Visual GUI")],
    [sg.HorizontalSeparator()],

    [sg.Text("Device")],
    [sg.Combo(["No device", "Hantek 6022BE", "Hantek 6022BL"], default_value="No device", size=(25, 1))],
    [sg.Button("Refresh"), sg.Button("Connect"), sg.Button("Disconnect")],

    [sg.HorizontalSeparator()],
    [sg.Text("Channels", font=("Helvetica", 12, "bold"))],
    [sg.Checkbox("CH1", default=True), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1))],
    [sg.Checkbox("CH2", default=False), sg.Text("Scale"), sg.Combo(["50mV", "100mV", "200mV", "500mV", "1V", "2V", "5V"], default_value="1V", size=(8, 1))],

    [sg.HorizontalSeparator()],
    [sg.Text("Timebase", font=("Helvetica", 12, "bold"))],
    [sg.Combo(["100us", "200us", "500us", "1ms", "2ms", "5ms", "10ms", "20ms"], default_value="1ms", size=(10, 1)), sg.Text("/div")],

    [sg.HorizontalSeparator()],
    [sg.Text("Trigger", font=("Helvetica", 12, "bold"))],
    [sg.Text("Source"), sg.Combo(["CH1", "CH2"], default_value="CH1", size=(8, 1))],
    [sg.Text("Slope"), sg.Combo(["Rising", "Falling", "Both"], default_value="Rising", size=(8, 1))],
    [sg.Text("Level"), sg.Input("0.0", size=(8, 1)), sg.Text("V")],
    [sg.Text("Position"), sg.Slider(range=(0, 100), default_value=50, orientation="h", size=(15, 15))],
    [sg.Radio("Auto", "MODE", default=True), sg.Radio("Normal", "MODE"), sg.Radio("Single", "MODE")],

    [sg.HorizontalSeparator()],
    [sg.Button("Apply"), sg.Button("Acquire"), sg.Button("Run / Stop"), sg.Button("Force Trigger")],

    [sg.HorizontalSeparator()],
    [sg.Text("Status: Stopped", key="-STATUS-")],
    [sg.Text("CH1: 0.00 V   CH2: 0.00 V")],

    [sg.HorizontalSeparator()],
    [sg.Text("Waveform")],
    [sg.Canvas(size=(600, 250), background_color="black")],
    [sg.Text("FFT")],
    [sg.Canvas(size=(600, 150), background_color="black")],

    [sg.HorizontalSeparator()],
    [sg.Text("Log")],
    [sg.Multiline("GUI ready.\n", size=(70, 5), disabled=True)],
]

window = sg.Window("Hantek 6022", layout, resizable=True)

event, values = window.read()

window.close()
