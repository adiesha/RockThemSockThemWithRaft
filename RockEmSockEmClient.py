import json
import os
import random
import socket
import sys
import threading
from time import sleep
from xmlrpc.client import ServerProxy


class RockEm:

    def __init__(self):
        self.HOST = "127.0.0.1"
        self.SERVER_PORT = 65431
        self.mapofNodes = None
        self.map = {}
        self.color = None
        self.state = None

        self.block_with_left_state = 1
        self.block_with_right_state = 2
        self.punch_with_left_action = 3
        self.punch_with_right_action = 4

        self.gamestate = (None, None, None)
        self.queue = []
        self.queueMutex = threading.Lock()

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
                print("Display RockEm DashBoard. Also can be used to demonstrate the Raft client\t[d]")
                print("Press [a] to add something to Raft Log \t[d]")
                print("Press [s] to start the game\t[d]")
                print("Press [l] to print the leader\t[d]")
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
                    # print(self.color)
                    if self.color is None:
                        print("Press [s] again to continue")
                        print("Press [e] to exit the system")
                        leaderID = self.getLeader()
                        self.color = (self.map[leaderID].registerPlayer())[1]
                        print("Player Color: {0}".format(self.color))
                        updatethread = threading.Thread(target=self.gotogame)
                        updatethread.daemon = True
                        updatethread.start()
                        print("Game update thread created!")
                        self.createProcessRequestThread()
                        while True:
                            print("Press [s] again to register the player")
                            print("Press [e] to exit the system")
                            print("Press [q] to punch left")
                            print("Press [w] to punch right")
                            print("Press [a] to block with left")
                            print("Press [s] to block with right")
                            print("Press anything to do nothing")

                            x = input().lower().split()
                            print("Input Entered:{0}".format(x))
                            if not x:
                                continue
                            elif x[0] == 'e':
                                exit(0)
                            # elif x[0] == 's':
                            #     print("Printing initial state and queues")
                            #     print(self.gamestate)
                            #     print(self.queue)
                            #     self.createProcessRequestThread()
                            elif x[0] == 'q':
                                try:
                                    self.addToRequestQueue(self.punch_with_left_action)
                                except Exception as e:
                                    print("Try again")
                            elif x[0] == 'w':
                                try:
                                    self.addToRequestQueue(self.punch_with_right_action)
                                except Exception as e:
                                    print("Try again")
                            elif x[0] == 'a':
                                try:
                                    self.addToRequestQueue(self.block_with_left_state)
                                except Exception as e:
                                    print("Try again")
                            elif x[0] == 's':
                                try:
                                    self.addToRequestQueue(self.block_with_right_state)
                                except Exception as e:
                                    print("Try again")
                            else:
                                continue
                    else:
                        print("Player already registered!")
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
                # print('Found the leader')
                return leaderId
            except Exception as e:
                print("Looks like node is down, choosing a new node")
                print(e)
                li.remove(k)
                continue

    def gotogame(self):

        while True:
            if 7 not in self.queue:
                self.addToRequestQueue(7)  # retrieve gamestate

            self.clearConsole()
            print("Press [q] punch_with_left() [Q]")
            print("Press [w] punch_with_right() [W]")
            print("Press [a] block_with_left() [A]")
            print("Press [s] block_with_right() [S]")
            print("")
            # print(self.gamestate)
            self.printGameState()
            sleep(2)

    def printGameState(self):
        if self.gamestate[0] == None or self.gamestate[1] == None:
            print("Players are joining")
        else:
            print("==============================================")
            print("Player BLUE:")
            print(self.getState(self.gamestate[0], "Blue"))
            print("++++++++++++++++++++++++++++++++++++++++++++++")
            print("Player RED:")
            print(self.getState(self.gamestate[1], "Blue"))
            print("No State" if self.gamestate[2] is None else self.gamestate[2])
            print("==============================================")

    def getState(self, state, player):
        if state is None:
            return "Game hasn't started yet for player {0}".format(player)
        if state == 0:
            return "Normal stance"
        elif state == 1:
            return "Block Left"
        elif state == 2:
            return "Block Right"
        elif state == 3:
            return "Punch Left"
        elif state == 4:
            return "Punch Right"
        elif state == 5:
            return "Player {0} Won".format(player)
        elif state == 6:
            return "Player {0} Lost".format(player)

    def clearConsole(self):
        command = 'clear'
        if os.name in ('nt', 'dos'):  # If Machine is running on Windows, use cls
            command = 'cls'
        os.system(command)

    def addToRequestQueue(self, req):
        try:
            self.queueMutex.acquire()
            if req != 7:
                self.queue.insert(0, req)
            else:
                self.queue.append(req)
            print("appended")
        except Exception as e:
            print(e)
        finally:
            self.queueMutex.release()

    def createProcessRequestThread(self):
        thread = threading.Thread(target=self.processRequests)
        thread.daemon = True
        print("Request Processing Thread")
        thread.start()

    def processRequests(self):
        while True:
            try:
                # print("Processing")
                self.queueMutex.acquire()
                if self.queue:
                    req = self.queue.pop(0)
                    if req == 7:
                        leaderid = self.getLeader()
                        state = self.map[leaderid].getGameState()
                        # print(state)
                        # print((state['b'], state['r'], state['m']))
                        self.gamestate = (state['b'], state['r'], state['m'])
                    elif req == 3 or req == 4:
                        print("Processing punch")
                        leaderid = self.getLeader()
                        self.map[leaderid].punch(self.color, req)
                    elif req == 1 or req == 2:
                        print("processing block")
                        leaderid = self.getLeader()
                        self.map[leaderid].punch(self.color, req)
                    else:
                        print("Incorrect Request")
                else:
                    # print("Queue is empty")
                    pass
            except Exception as e:
                print("Wow exception")
                print(e)
            finally:
                self.queueMutex.release()


if __name__ == '__main__':
    game = RockEm()
    game.main()
