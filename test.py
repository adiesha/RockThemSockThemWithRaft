import PySimpleGUI as sg
import os
import time

from numpy import choose

def choosePlayer():
        popup_layout = [  [sg.Text('Choose your player', font= ("Arial", 20))],
                    [sg.Button('Red Rocker', s=(10,10), button_color=("white", "firebrick"), font= ("Arial", 20)), 
                    sg.Button('Blue Bomber', s=(10,10), button_color=("white", "royal blue"), font= ("Arial", 20))],
                    [(sg.Graph((800, 100), (0, 0), (800, 100), key='Graph', background_color="black"))]]
        window = sg.Window('Rock ‘Em Sock ‘Em Robots', popup_layout, margins=(200, 200), use_default_focus=False, modal=True, element_justification='c')
                
        ans = None
        flag = None
        error = False
        while ans != 1:
            ans, flag = choice(window)
            if ans == 1:
                if error:
                    window['Graph'].delete_figure(error)
                window['Graph'].draw_text(text = "Player Chosen : "+flag+ ". Loading game!", location=(400, 50), color = "white", text_location = "center", font= ("Arial", 20))
                window.refresh()
                time.sleep(10)
                break
            elif ans == 2:
                ans = None
                error = window['Graph'].draw_text(text = "Player already taken, please choose another player", location=(400, 50),color = "white", text_location = "center", font= ("Arial", 20))
                window.refresh()

        window.close()

def choice(window):
        while True:
            event, values = window.read()
            if event == sg.WIN_CLOSED : 
                break
            if event == 'Red Rocker' :
                # ans = self.map[self.leader_id].setPlayer(self.id, "1")
                flag = "red"
                ans = 1
                break
            if event == 'Blue Bomber' :
                # ans = self.map[self.leader_id].setPlayer(self.id, "2")
                flag = "blue"
                ans = 2
                break
        return ans, flag

def game():
    dir = os.path.dirname(__file__)


    sg.theme('DarkAmber')
    layout = [[sg.Text('FIGHT!', font=("Arial", 20), justification='center')],
        [(sg.Graph((800, 500), (0, 0), (800, 500), key='Graph', background_color="black"))],
        [sg.Button('Red Rocker', button_color=("white", "firebrick"), font= ("Arial", 20)), 
        sg.Button('Blue Bomber', button_color=("white", "royal blue"), font= ("Arial", 20))] ]

    window = sg.Window('Rock ‘Em Sock ‘Em Robots', layout, use_default_focus=False, element_justification='c')
    window['Graph'].draw_text(text = "Controls", location=(400, 475), color = "white", text_location = "center", font= ("Arial", 20))
    window['Graph'].draw_text(text = "Q : Punch Left      W : Punch Right", location=(415, 450), color = "white", text_location = "center")
    window['Graph'].draw_text(text = "A : Block Left      S : Block Right", location=(415, 425), color = "white", text_location = "center")
    window['Graph'].draw_image(filename=os.path.join(dir, "assets/ring.png"), location=(25, 400))
    red_id = window['Graph'].draw_image(filename=os.path.join(dir, "assets/red_default.png"), location=(-60, 500))
    blue_id = window['Graph'].draw_image(filename=os.path.join(dir, "assets/blue_default.png"), location=(-60, 500))


    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED : 
            break
        if event == 'Red Rocker' :
            window['Graph'].delete_figure(red_id)
            red_id = window['Graph'].draw_image(filename=os.path.join(dir, "assets/red_attack_left.png"), location=(-60, 500))
        if event == 'Blue Bomber' :
            window['Graph'].delete_figure(blue_id) 

    window.close()


game()