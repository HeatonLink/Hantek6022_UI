import PySimpleGUI as sg

layout = [
    [sg.Text("Hello, World!")],
    [sg.Text("Hantek test")],
    [sg.Button("OK")],
    [sg.Button("Cancel")],
    [sg.Checkbox("CH1")],
    [sg.Checkbox("CH2")],
    [sg.Input(key="-IN-")],
    [sg.Combo(["1V", "2V", "5V"], default_value="1V")],
    [sg.Slider(range=(0, 10), default_value=5, orientation="h")],
    [sg.Text("Status: ready")],
]

window = sg.Window("My First GUI", layout)

event, values = window.read()

window.close()
