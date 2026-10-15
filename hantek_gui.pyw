import PySimpleGUI as sg

layout = [
    [sg.Text("Hello, World!")],
    [sg.Text("Hantek test")],
    [sg.Button("OK")],
    [sg.Button("Cancel")],
    [sg.Button("Start")],
    [sg.Checkbox("CH1")],
    [sg.Checkbox("CH2")],
    [sg.Input(key="-IN-")],
    [sg.Combo(["1V", "2V", "5V"], default_value="1V")],
    [sg.Combo(["1ms", "2ms", "5ms"], default_value="1ms")],
    [sg.Slider(range=(0, 10), default_value=5, orientation="h")],
    [sg.Radio("Auto", "TRIG", default=True)],
    [sg.Radio("Normal", "TRIG")],
    [sg.Text("Status: ready")],
    [sg.Multiline("Log area", size=(40, 4))],
]

window = sg.Window("My First GUI", layout)

event, values = window.read()

window.close()
