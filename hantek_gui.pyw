import PySimpleGUI as sg

layout = [
    [sg.Text("Hello, World!")],
    [sg.Text("Hantek test")],
    [sg.Button("OK")],
    [sg.Button("Cancel")],
    [sg.Checkbox("CH1")],
    [sg.Input(key="-IN-")],
]

window = sg.Window("My First GUI", layout)

event, values = window.read()

window.close()
