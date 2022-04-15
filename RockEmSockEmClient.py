import json
import random
import sys
import socket
import acd
import os
import logging
import threading
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

class RockEm:

    def __init__(self, id):
        self.id = id
        self.HOST = "127.0.0.1"
        self.SERVER_PORT = 65431
        self.mapofNodes = None
        self.map = {}
        self.leader_id = None
        self.clientip = "127.0.0.1"
        self.clientPort = None

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
        while True:
            print("Enter your choice:")
            print("Red Rocker [1]")
            print("Blue Bomber [2]")
            resp = input("Choice: ")
            ans = self.map[self.leader_id].setPlayer(self.id, resp)
            if ans == 1:
                print("Player chosen")
                break
            elif ans == 2:
                print("Player already taken, please choose another player")
            else:
                print("Getting correct leader")
                self.getLeader()

    def menu(self):
        while True:
            print("Choose an option")
            print("punch_with_left [Q]")
            print("punch_with_right [W]")
            print("block_with_left [A]")
            print("block_with_right [S]")
            resp = input("Choice: ").lower()
            ans = self.map[self.leader_id].playerMove(self.id, resp)
            if ans == 1:
                print("Punch blocked!")
            elif ans == 2:
                print("Hit landed! You win!")
                exit(0)
            elif ans == 3:
                print("Punch Dodged!")
            

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
            "Ready to start the RockEm Server. Please wait until all the nodes are ready to continue. Then press Enter")
        if input() == "":
            print("Started Creating the RockEm Server")
            self.mapofNodes = self.getMapData()
            print(self.mapofNodes)
            print("Creating the proxy Map")
            self.createProxyMap()
            self.getLeader()
            self.choosePlayer()
            self.menu()

if __name__ == '__main__':
    game = RockEm(1)
    game.main()

