import json
import random
import socket
import sys
from xmlrpc.client import ServerProxy


class RockEm:

    def __init__(self):
        self.HOST = "127.0.0.1"
        self.SERVER_PORT = 65431
        self.mapofNodes = None
        self.map = {}
        self.color = None
        self.state = None

    def createJSONReq(self, typeReq, nodes=None, slot=None):
        # Get map data
        if typeReq == 3:
            request = {"req": "3", "seq": str(0)}
            return request
        else:
            return ""

    def main(self):
        print('Number of arguments:', len(sys.argv), 'arguments.')
        print('Argument List:', str(sys.argv))

        if len(sys.argv) > 1:
            print("Server ip is {0}".format(sys.argv[1]))
            self.HOST = sys.argv[1]
            print("Server Ip updated")

        print(
            "Ready to start the RockEm Server. Please wait until all the nodes are ready to continue. Then press Enter")
        if input() == "":
            print("Started Creating the RockEm Server")
            self.mapofNodes = self.getMapData()
            print(self.mapofNodes)
            print("Creating the proxy Map")
            self.createProxyMap()

            self.menu()

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

    def menu(self):
        while True:
            while True:
                print("Display RockEm DashBoard\t[d]")
                resp = input("Choice: ").lower().split()
                if not resp:
                    continue
                elif resp[0] == 'a':
                    while True:
                        leaderID = self.map[2].getLeaderInfo()
                        if leaderID is not None:
                            try:
                                result = self.map[leaderID].addRequest({"1": 1})
                                if result:
                                    break
                            except Exception as e:
                                print(e)
                elif resp[0] == 'l':
                    print("Trying to get the leader: {0}".format(self.getLeader()))
                elif resp[0] == 's':
                    leaderID = self.getLeader()
                    self.color = (self.map[leaderID].registerPlayer())[1]
                    print(self.color)
                elif resp[0] == 'g':
                    leaderID = self.getLeader()
                    color = {"b": 0, "r": 1}
                    state = self.map[leaderID].getGameState()
                    print(state)
                    print(self.color)
                elif resp[0] == 'p':
                    color = {"b": 0, "r": 1}
                    punch = int(input("which punch:? "))
                    leaderID = self.getLeader()
                    c = color[self.color]
                    print(c)

                    self.map[leaderID].punch(self.color, punch)
                elif resp[0] == 'e':
                    exit(0)

    def getLeader(self):
        noOfNodes = len(self.mapofNodes)
        li = [*range(1, noOfNodes + 1)]
        while True:
            if not li:
                print("looks like all the nodes are down")
                return None
            k = random.choice(li)
            try:
                leaderId = self.map[k].getLeaderInfo()
                return leaderId
            except Exception as e:
                print("Looks like node is down, choosing a new node")
                print(e)
                li.remove(k)
                continue


if __name__ == '__main__':
    game = RockEm()
    game.main()
