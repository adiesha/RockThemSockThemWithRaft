import json
import random
import sys
import socket
import os
import logging
import threading
import time
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer
import PySimpleGUI as sg


class GUI:

    def __init__(self, id):
        self.id = id
        self.HOST = "127.0.0.1"
        self.SERVER_PORT = 65431
        self.mapofNodes = None
        self.map = {}
        self.leader_id = None
        self.clientip = "127.0.0.1"
        self.clientPort = None
        self.colour = None

    def createJSONReq(self, typeReq, nodes=None, slot=None):
        # Get map data
        if typeReq == 4:
            request = {"req": "4"}
            return request
        # Send port info
        elif typeReq == 2:
            request = {"req": "2", "seq": str(self.id), "port": str(self.clientPort)}
            return request
        # Get map data
        elif typeReq == 3:
            request = {"req": "3", "seq": str(self.id)}
            return request
        else:
            return ""

    def createRPCServer(self):
        print("Creating the RPC server for the Node {0}".format(self.id))
        print("Node {0} IP:{1} port: {2}".format(self.id, self.clientip, self.clientPort))
        thread = threading.Thread(target=self._executeRPCServer)
        thread.daemon = True
        thread.start()
        return thread

    def _executeRPCServer(self):
        server = SimpleXMLRPCServer((self.clientip, self.clientPort), logRequests=True, allow_none=True)
        server.register_instance(self)
        try:
            print("Serving........")
            server.serve_forever()
        except KeyboardInterrupt:
            print("Exiting")

    def createProxyMap(self):
        self.map = {}
        for k, v in self.mapofNodes.items():
            print(k, v)
            uri = r"http://" + v[0] + ":" + str(v[1])
            print(uri)
            self.map[k] = ServerProxy(uri, allow_none=True)

    def getMapData(self):
        print("Requesting Node Map from the Server")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.HOST, self.SERVER_PORT))
            strReq = self.createJSONReq(3)
            jsonReq = json.dumps(strReq)

            s.sendall(str.encode(jsonReq))

            data = self.receiveWhole(s)
            resp = self.getJsonObj(data.decode("utf-8"))
            resp2 = {}
            for k, v in resp.items():
                resp2[int(k)] = (v[0], int(v[1]))

            print(resp2)
            s.close()
            return resp2

    def sendNodePort(self):
        # establish connection with server and give info about the client port
        print('Sending client port to Server')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.HOST, self.SERVER_PORT))
            strReq = self.createJSONReq(2)
            jsonReq = json.dumps(strReq)

            s.sendall(str.encode(jsonReq))

            data = self.receiveWhole(s)
            resp = self.getJsonObj(data.decode("utf-8"))

            print(resp['response'])
            s.close()

    def initializeTheNode(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print("Connecting to HOSTL {0} port {1}".format(self.HOST, self.SERVER_PORT))
            s.connect((self.HOST, self.SERVER_PORT))
            strReq = self.createJSONReq(4)
            jsonReq = json.dumps(strReq)

            s.sendall(str.encode(jsonReq))

            data = self.receiveWhole(s)
            resp = self.getJsonObj(data.decode("utf-8"))

            self.id = int(resp['seq'])
            print("id: " + str(self.id))
            s.close()
        currrent_dir = os.getcwd()
        finallogdir = os.path.join(currrent_dir, 'log')
        if not os.path.exists(finallogdir):
            os.mkdir(finallogdir)
        logging.basicConfig(filename="log/{0}.log".format(self.id), level=logging.DEBUG, filemode='w')

    def receiveWhole(self, s):
        BUFF_SIZE = 4096  # 4 KiB
        data = b''
        while True:
            part = s.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                # either 0 or end of data
                break
        return data

    def getJsonObj(self, input):
        jr = json.loads(input)
        return jr

    def getLeader(self):
        while (self.leader_id == None):
            for k, v, in self.map.items():
                if k < 100:
                    self.leader_id = v.getLeaderInfo()
        print("Leader ID is: "+str(self.leader_id))


    def choosePlayer(self):
        popup_layout = [  [sg.Text('Choose your player', font= ("Arial", 20))],
                    [sg.Button('Red Rocker', s=(10,10), button_color=("white", "firebrick"), font= ("Arial", 20)), 
                    sg.Button('Blue Bomber', s=(10,10), button_color=("white", "royal blue"), font= ("Arial", 20))],
                    [(sg.Graph((800, 100), (0, 0), (800, 100), key='Graph', background_color="black"))]]
        window = sg.Window('Rock ‘Em Sock ‘Em Robots', popup_layout, margins=(200, 200), use_default_focus=False, finalize=True, modal=True, element_justification='c')
        
        ans = None
        flag = None
        error = False
        while ans != 1:
            ans, flag = self.choice(window)
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


    def choice(self, window):
        while True:
            event, values = window.read()
            if event == sg.WIN_CLOSED : 
                break
            if event == 'Red Rocker' :
                ans = self.map[self.leader_id].setPlayer(self.id, "1")
                flag = "red"
                break
            if event == 'Blue Bomber' :
                ans = self.map[self.leader_id].setPlayer(self.id, "2")
                flag = "blue"
                break
        return ans, flag

    def game(self):
        dir = os.path.dirname(__file__)


        sg.theme('DarkAmber')
        layout = [[sg.Text('FIGHT!', font=("Arial", 20), justification='center')],
            [(sg.Graph((800, 500), (0, 0), (800, 500), key='Graph', background_color="black"))],
            [sg.Button('Red Rocker', button_color=("white", "firebrick"), font= ("Arial", 20)), 
            sg.Button('Blue Bomber', button_color=("white", "royal blue"), font= ("Arial", 20))] ]

        window = sg.Window('Rock ‘Em Sock ‘Em Robots', layout, use_default_focus=False, finalize=True, element_justification='c')
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

    def gameOver(self):
        pass

    def main(self):
        print('Number of arguments:', len(sys.argv), 'arguments.')
        print('Argument List:', str(sys.argv))

        if len(sys.argv) > 1:
            print("Server ip is {0}".format(sys.argv[1]))
            self.HOST = sys.argv[1]
            print("Server Ip updated")

        port = random.randint(55000, 63000)
        print("Random port {0} selected".format(port))
        self.clientPort = port

        self.initializeTheNode()
        self.sendNodePort()
        self.createRPCServer()

        print(
            "Ready to start the RockEm Client. Please wait until all the nodes are ready to continue. Then press Enter")
        if input() == "":
            print("Started Creating the RockEm Client")
            self.mapofNodes = self.getMapData()
            print(self.mapofNodes)
            print("Creating the proxy Map")
            self.createProxyMap()
            self.getLeader()
            self.choosePlayer()
            # self.game()


if __name__ == '__main__':
    game = GUI(1)
    game.main()