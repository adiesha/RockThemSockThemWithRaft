import os
from PIL import Image, ImageTk
import PySimpleGUI as sg

def player_choice():
    popup_layout = [  [sg.Text('Choose your player', font= ("Arial", 20))],
                [sg.Button('Red Rocker', s=(10,10), button_color=("white", "firebrick"), font= ("Arial", 20)), 
                sg.Button('Blue Bomber', s=(10,10), button_color=("white", "royal blue"), font= ("Arial", 20))] ]
    window = sg.Window('Rock ‘Em Sock ‘Em Robots', popup_layout, margins=(200, 200), use_default_focus=False, finalize=True, modal=True, element_justification='c')

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED : 
            break
        if event == 'Red Rocker' :
            choice = "1"
            break
        if event == 'Blue Bomber' :
            choice = "2" 
            break
    window.close()
    return choice

def main():
    dir = os.path.dirname(__file__)
    sg.theme('DarkAmber') 
    choice = player_choice()
    print("Choice: " +choice)
    layout = [[sg.Text('FIGHT!', font=("Arial", 20), justification='center')],
        [sg.Image(source=os.path.join(dir, "assets/ring.png"))],
        [(sg.Graph((400, 190), (0, 0), (400, 190), key='Graph'))]]

    window = sg.Window('Rock ‘Em Sock ‘Em Robots', layout, use_default_focus=False, finalize=True, element_justification='c')
    window['Graph'].draw_image(filename=os.path.join(dir, "assets/blue_default.png"), location=(0, 200))
    window['Graph'].draw_image(filename=os.path.join(dir, "assets/red_default.png"), location=(190, 170))

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED : 
            break

    window.close()

if __name__ == '__main__':
    main()