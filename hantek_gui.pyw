import PySimpleGUI as sg

# Define the window's contents
layout = [[sg.Text("Hello, World!")],
          [sg.Button("OK")]]

# Create the window
window = sg.Window("My First GUI", layout)

# Display and interact with the Window
event, values = window.read()

# Close the window
window.close()
