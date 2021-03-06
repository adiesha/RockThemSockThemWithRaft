import json
import logging
import os
import pickle
import random
import socket
import sys
import threading
from enum import Enum
from time import sleep
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

import numpy as np


# ToDO: Mutex, commiting, threading, rpc threading, exceptions handling, basic input/output
#  adding function for clients (who is the leader?, persistent storage and restart, getting gamestate)

class Raft:
    def __init__(self, id):
        # these attributes should be persistent
        self.id = id
        self.currentTerm = 0
        self.votedFor = None
        self.log = []
        self.map = None  # Map about the other nodes
        self.noOfNodes = 0

        self.state = State.FOLLOWER
        self.leader = None

        # volatile states
        self.commitIndex = -1
        self.lastApplied = 0
        self.stateIndex = 0

        # volatile state on leader
        self.nextIndex = None
        self.matchIndex = None

        # check this flag every after every timeout
        # if false issue go for election
        # if not set this to false and choose another timeout and check after that time
        self.receivedHeartBeat = False

        self.mutexForAppendEntry = threading.Lock()
        self.mutexForHB = threading.Lock()
        self.voteMutex = threading.Lock()

        self.HOST = "127.0.0.1"
        self.clientip = "127.0.0.1"
        self.clientPort = None
        self.SERVER_PORT = 65431
        self.mapofNodes = None

        # Game state Variables
        self.blueID = None
        self.blueState = None
        self.redID = None
        self.redState = None

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the heartbeat for leader
    # We can create a daemon that issues appendEntries to all the nodes if they are the leader
    def heartbeat(self, message):
        print("heartbeat invoked in node {0}".format(self.id))

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the appendEntries for leader
    def appendEntries(self, info):
        self.mutexForAppendEntry.acquire()
        # print("Acquiring mutex for appendEntry in node {0}".format(self.id))
        logging.debug("Acquiring mutex for appendEntry in node {0}".format(self.id))
        # First check whether this is a initial heartbeat by a leader.
        check = self.checkwhetheritsaheratbeat(info)
        if check is not None:
            self.mutexForAppendEntry.release()
            # print("Mutex for appendEntry is released in node {0}".format(self.id))
            logging.debug("Mutex for appendEntry is released in node {0}".format(self.id))
            return check, self.currentTerm
        else:
            if info['term'] < self.currentTerm:
                self.mutexForAppendEntry.release()
                # print("Mutex for appendEntry is released in node {0}".format(self.id))
                logging.debug("Mutex for appendEntry is released in node {0}".format(self.id))
                return False, self.currentTerm
            prevLogIndex = info['previouslogindex']
            prevLogTerm = info['previouslogterm']
            leadercommitIndex = info['leadercommit']
            print("leaddercommmit {0}".format(leadercommitIndex))

            if prevLogIndex == -1:
                pass
            else:
                print("prev:" + str(prevLogIndex))
                if self.log[prevLogIndex].term != prevLogTerm:
                    self.mutexForAppendEntry.release()
                    # print("Mutex for appendEntry is released in node {0}".format(self.id))
                    logging.debug("Mutex for appendEntry is released in node {0}".format(self.id))
                    return False, self.currentTerm

            # received actual appendEntry do the logic
            entries = info['values']
            for e in entries:
                print("Appending Entries in node {0} by the leader".format(self.id))
                print("Id of the entry that we are adding is {0}".format(e.id))
                logging.debug("Appending Entries in node {0} by the leader".format(self.id))
                logging.debug("Id of the entry that we are adding is {0}".format(e.id))
                if e.id != len(self.log):
                    print("Entry that we are adding is not at the correct log index {0} log length {1}".format(e.id,
                                                                                                               len(self.log)))
                    logging.debug(
                        "Entry that we are adding is not at the correct log index {0} log length {1}".format(e.id,
                                                                                                             len(self.log)))
                    # This needs to be double checked
                    self.log[e.id] = e
                    # raise Exception(
                    #     "Entry that we are adding is not at the correct log index {0} log length {1}".format(e.id,
                    #                                                                                          len(self.log)))
                else:
                    self.log.append(e)
                    self.commitIndex = leadercommitIndex
                    self.updateCommittedEntries()
        self.mutexForAppendEntry.release()
        # print("Mutex for appendEntry is released in node {0}".format(self.id))
        logging.debug("Mutex for appendEntry is released in node {0}".format(self.id))
        return True, self.currentTerm

    def checkwhetheritsaheratbeat(self, info):
        print(
            "Checking whether appendEntry is a Heartbeat from {0} to node {1} leader Term {2}".format(info['leaderid'],
                                                                                                      self.id,
                                                                                                      info['term']))
        logging.debug(
            "Checking whether appendEntry is a Heartbeat from {0} to node {1} leader Term {2}".format(info['leaderid'],
                                                                                                      self.id,
                                                                                                      info['term']))
        if info['values'] is None:
            info['values'] = []
        else:
            print("Before")
            print(info['values'])
            info['values'] = pickle.loads(info['values'].data)
            print("After")
            print(info['values'])
        print(info['values'])
        if len(info['values']) == 0:
            if info['term'] < self.currentTerm:
                print("Term from the heartbeat is lower: HB Term {0} current term {1}".format(info['term'],
                                                                                              self.currentTerm))
                logging.debug("Term from the heartbeat is lower: HB Term {0} current term {1}".format(info['term'],
                                                                                                      self.currentTerm))
                return False
            else:
                # print("Heartbeat received by node {0} from the leader {1}".format(self.id, info['leaderid']))
                logging.debug("Heartbeat received by node {0} from the leader {1}".format(self.id, info['leaderid']))
                self.leader = info['leaderid']
                self.state = State.FOLLOWER
                self.mutexForHB.acquire()
                self.receivedHeartBeat = True
                self.mutexForHB.release()
                # print("Node {0} 's current Term is before update is {1} state {2}".format(self.id, self.currentTerm,
                #                                                                           self.state))
                logging.debug(
                    "Node {0} 's current Term is before update is {1} state {2}".format(self.id, self.currentTerm,
                                                                                        self.state))
                self.currentTerm = info['term']
                self.commitIndex = info['leadercommit']
                self.updateCommittedEntries()
                print("Node {0} 's current Term is updated to {1} state {2}".format(self.id, self.currentTerm,
                                                                                    self.state))
                return True
        else:
            print("AppendEntry from {0} to node {1} leader's Term {2} is not a HB".format(info['leaderid'], self.id,
                                                                                          info['term']))
            logging.debug(
                "AppendEntry from {0} to node {1} leader's Term {2} is not a HB".format(info['leaderid'], self.id,
                                                                                        info['term']))
            return None

    # Request RPC is the method that is invoked by a candidate to request the vote
    def requestVote(self, info):
        self.mutexForAppendEntry.acquire()
        # print('Acquiring mutex for request vote in node {0}'.format(self.id))
        # info is a dict: nodeid, term, lastindexofthelog lastlogterm
        candidateid = info['nodeid']
        term = info['term']
        candidateslastindexofthelog = info['lastindexofthelog']
        candidateslastlogterm = info['lastlogterm']

        if term < self.currentTerm:
            self.mutexForAppendEntry.release()
            # print('Releasing mutex for request vote in node {0}'.format(self.id))
            print("Request for vote was rejected for candidate {0} by node {0} for lower term".format(candidateid,
                                                                                                      self.id))
            logging.debug(
                "Request for vote was rejected for candidate {0} by node {0} for lower term".format(candidateid,
                                                                                                    self.id))
            return False
        elif term == self.currentTerm:
            print("candidates term {0} is equal to nodes {0} term: {2}".format(candidateid, self.id, term))
            logging.debug("candidates term {0} is equal to nodes {0} term: {2}".format(candidateid, self.id, term))
            if self.votedFor is None:
                pass
            else:
                print("Node {0} has already voted for {1} in term {2}".format(self.id, self.votedFor, self.currentTerm))
                logging.debug(
                    "Node {0} has already voted for {1} in term {2}".format(self.id, self.votedFor, self.currentTerm))
                self.mutexForAppendEntry.release()
                return False
        else:  # term >= self.currentTerm
            print("Node {0} term {1} is lower than the candidate {3} term {2}".format(self.id, self.currentTerm, term,
                                                                                      candidateid))
            print("Node {0}'s term is incremented to match the candidates term {1}".format(self.id, term))
            logging.debug(
                "Node {0} term {1} is lower than the candidate {3} term {2}".format(self.id, self.currentTerm, term,
                                                                                    candidateid))
            logging.debug("Node {0}'s term is incremented to match the candidates term {1}".format(self.id, term))
            self.currentTerm = term
            # updating votedFor to None since candidates term is larger than the current term
            self.votedFor = None

        # Need to implement this
        if self.votedFor is None:
            # Compare the term of the last entry against candidates last term
            # if they are the same then compare the last log index

            if candidateslastlogterm < self.getLastTerm():
                print("Candidates last term is smaller than the current term of the node {0}".format(self.id))
                logging.debug("Candidates last term is smaller than the current term of the node {0}".format(self.id))
                self.mutexForAppendEntry.release()
                # print('Releasing mutex for request vote in node {0}'.format(self.id))
                print(
                    "Request for vote was rejected for candidate {0} by node {0} for not having correct previous log "
                    "term")
                logging.debug(
                    "Request for vote was rejected for candidate {0} by node {0} for not having correct previous log "
                    "term")
                return False
            else:
                # candidates term is greater than or equal to nodes term, now we have to look at the last index
                if candidateslastlogterm == self.getLastTerm():
                    # check the last index of the log
                    if candidateslastindexofthelog < self.getLastIndex():
                        print(
                            "Candidates term and current term is equal but last index of the node {0} is greater than the candidates last index".format(
                                self.id
                            ))
                        logging.debug(
                            "Candidates term and current term is equal but last index of the node {0} is greater than the candidates last index".format(
                                self.id
                            ))
                        self.mutexForAppendEntry.release()
                        # print('Releasing mutex for request vote in node {0}'.format(self.id))
                        return False
                    else:
                        self.votedFor = candidateid
                        self.mutexForAppendEntry.release()
                        # print('Releasing mutex for request vote in node {0}'.format(self.id))
                        return True
                else:
                    self.votedFor = candidateid
                    self.mutexForAppendEntry.release()
                    # print('Releasing mutex for request vote in node {0}'.format(self.id))
                    return True
        else:  # Already voted for someone
            print(
                "Request rejected as node {0} has already voted for {1} in term {2}".format(self.id, self.votedFor,
                                                                                            self.currentTerm))
            logging.debug(
                "Request rejected as node {0} has already voted for {1} in term {2}".format(self.id, self.votedFor,
                                                                                            self.currentTerm))
            self.mutexForAppendEntry.release()
            # print('Releasing mutex for request vote in node {0}'.format(self.id))
            return False

    # invoking appendEntries of other nodes
    # This method should not be exposed to invoke
    def _invokeAppendEntries(self):
        # check whether you are the leader
        if self.state != State.LEADER:
            print("Node {0} is not the leader cannot add entries".format(self.id))
            return

        # add the entry to the log
        entry = Entry(len(self.log), self.currentTerm)
        self.log.append(entry)
        entry.id = len(self.log) - 1

        info = self.createApppendEntryInfo()

        info['value'] = pickle.dumps(entry)

        # Node is the leader
        for k, v in self.map.items():
            if k < 100:
                v.appendEntries(info)
        pass

    # This method should invoke heartbeat function of other nodes
    # This method should not be exposed to invoke
    def _invokeHeartBeat(self):
        pass

    def _invokeRequestVoteRPV(self):
        print("Invoking Election by Node {0}".format(self.id))
        # vote for itself
        # loop the nodes and call the RequestVoteRPC
        vote = Vote()

        self.mutexForAppendEntry.acquire()
        self.state = State.CANDIDATE
        self.currentTerm = self.currentTerm + 1
        self.votedFor = self.id
        self.mutexForAppendEntry.release()
        vote.addVote()
        inf = self.createInfo()
        print(
            "Node:{0} Term: {1} state: {2} votedFor: {3}".format(self.id, self.currentTerm, self.state, self.votedFor))

        for k, v in self.map.items():
            if k != self.id and k < 100:
                # result = self.createDaemon(v.requestVote, inf)
                self.requestVoteFromNode(k, v, inf, vote)

        if vote.getVotes() >= self.getSimpleMajority():
            print("Found the majority. Making node {0} the leader".format(self.id))
            self.state = State.LEADER
            self.intializevolatileStateOfTheLeader()
            # send a heartbeat
            return True
        else:
            print("Node {0} did not get the majority. Number of votes got is {1}".format(self.id, vote.votes))
            return False

    def intializevolatileStateOfTheLeader(self):
        if not self.log:
            self.nextIndex = np.zeros(self.noOfNodes, dtype=np.int32)
            self.matchIndex = np.zeros(self.noOfNodes, dtype=np.int32)
        else:
            lastIndex = self.getLastIndex()
            self.nextIndex = np.zeros(lastIndex + 1, dtype=np.int32)

    def createDaemon(self, func, inf):
        thread = threading.Thread(target=func, args=(inf,))
        thread.daemon = True
        thread.start()
        return thread

    def requestVoteFromNode(self, k, proxy, inf, vote):
        result = proxy.requestVote(inf)
        if result:
            vote.addVote()
        print("Election Result: Candidate {0} requestedNde {1} result: {2} term: {3}".format(self.id, k, result,
                                                                                             inf['term']))
        return result

    def getSimpleMajority(self):
        if self.noOfNodes % 2 == 0:
            return int(self.noOfNodes / 2 + 1)
        else:
            return int(self.noOfNodes / 2) + 1

    def getLastTerm(self):
        if not self.log:
            return 0
        else:
            return self.log[-1].term

    def getLastIndex(self):
        return -1 if not self.log else len(self.log) - 1

    def createInfo(self):
        dict = {}

        dict['nodeid'] = self.id
        dict['term'] = self.currentTerm
        dict['lastindexofthelog'] = self.getLastIndex()
        dict['lastlogterm'] = self.getLastTerm()
        return dict

    def createApppendEntryInfo(self):
        dict = {}

        dict['leaderid'] = self.id
        dict['term'] = self.currentTerm
        dict['previouslogindex'] = -1 if self.getLastIndex() == -1 else self.getLastIndex() - 1
        dict['previouslogterm'] = self.getLastTerm()
        dict['values'] = None
        dict['leadercommit'] = self.commitIndex

        return dict

    def timeout(self):
        while True:
            randomTimeout = random.randint(4, 8)
            if self.state == State.FOLLOWER:
                print("Chosen timeout for node {0} is {1}".format(self.id, randomTimeout))
                logging.debug("Chosen timeout for node {0} is {1}".format(self.id, randomTimeout))
                sleep(randomTimeout)
                # print("Acquiring HB mutex")
                logging.debug('Acquiring HB mutex')
                self.mutexForHB.acquire()
                if self.receivedHeartBeat:
                    self.receivedHeartBeat = False
                    print(
                        "Timeout occurred but Heartbeat was received by the node {0} earlier. Picking a new timeout".format(
                            self.id))
                    logging.debug(
                        "Timeout occurred but Heartbeat was received by the node {0} earlier. Picking a new timeout".format(
                            self.id))
                    self.mutexForHB.release()
                    # print("Releasing HB mutex")
                    logging.debug("Releasing HB mutex")
                    continue
                    # pick a new timeout
                else:
                    self.mutexForHB.release()
                    # print("Releasing HB mutex")
                    logging.debug("Releasing HB mutex")
                    print(
                        "Timeout occurred NO Heartbeat was received by the node {0} earlier. Picking a new timeout".format(
                            self.id))
                    logging.debug(
                        "Timeout occurred NO Heartbeat was received by the node {0} earlier. Picking a new timeout".format(
                            self.id))
                    while True:
                        electionTimeout = random.randint(2, 5)
                        # we can send the timeout period to following method as well
                        # Not sure what is the best solution yet
                        result = self._invokeRequestVoteRPV()
                        if result:
                            print("Leader Elected: Node {0}".format(self.id))
                            break
                        else:
                            if self.state == State.CANDIDATE:
                                sleep(electionTimeout)
                                print("Election timeout occurred. Restarting the election Node {0}".format(self.id))
                                logging.debug(
                                    "Election timeout occurred. Restarting the election Node {0}".format(self.id))
                            elif self.state == State.FOLLOWER:
                                print("Looks like we found a leader for the term, leader is {0}".format(self.votedFor))
                                logging.debug(
                                    "Looks like we found a leader for the term, leader is {0}".format(self.votedFor))
            elif self.state == State.LEADER:
                randomTimeout = random.randint(3, 4)
                # send heartbeats
                # self.updatecommitIndex()
                info = self.createApppendEntryInfo()
                info['value'] = None
                for k, v in self.map.items():
                    if k != self.id and k < 100:
                        self.callAppendEntryForaSingleNode(k, v, hb=True)
                        # v.appendEntries(info)

                sleep(randomTimeout)
                # print("Sending Heartbeats")
                logging.debug("Sending Heartbeats")

    def createTimeoutThread(self):
        thread = threading.Thread(target=self.timeout)
        thread.daemon = True
        thread.start()

        thread2 = threading.Thread(target=self.updatecommitIndex)
        thread2.daemon = True
        thread2.start()
        return thread

    def updatecommitIndex(self):
        temp = self.commitIndex + 1
        while True:
            if self.state == State.LEADER:
                print("Current Commit Index {0}".format(self.commitIndex))
                print("Current State Index {0}".format(self.stateIndex))
                logging.debug("Current Commit Index {0}".format(self.commitIndex))
                # temp = self.commitIndex + 1
                count = 0
                if 0 <= temp < len(self.log):
                    count = count + 1
                else:
                    print("Next index does not exist in the log next index {0}".format(temp))
                    logging.debug("Next index does not exist in the log next index {0}".format(temp))
                    sleep(3)
                    continue
                for i in range(self.noOfNodes):
                    if i != self.id:
                        if temp <= self.matchIndex[i - 1]:
                            count = count + 1
                if count >= self.getSimpleMajority():
                    if self.log[temp].term == self.currentTerm:
                        print("Next commit index is {0}".format(temp))
                        logging.debug("Next commit index is {0}".format(temp))
                        self.commitIndex = temp
                        self.log[temp].iscommitted = True
                    else:
                        print(
                            "Entry ID:{0} is replicated in majority but was not appended by current term {1} and "
                            "leader {1}".format(
                                temp, self.currentTerm, self.id))
                        logging.debug(
                            "Entry ID:{0} is replicated in majority but was not appended by current term {1} and "
                            "leader {1}".format(
                                temp, self.currentTerm, self.id))
                sleep(3)
                print("Waked up")
                temp += 1
            else:
                # print("Not the leader to find the commit index")
                pass

    def callAppendEntryForaSingleNode(self, k, v, hb=False):
        # this method should spawn a thread
        while True:
            info = self.createApppendEntryInfo()
            values = []
            if self.nextIndex[k - 1] > self.getLastIndex() and not hb:
                print("Node {0} is up to date".format(k))
                logging.debug("Node {0} is up to date".format(k))
                return True
            hb = False  # HB flag is set to false because we do not need to loop this indefinitely
            if not self.log:
                print("Log is empty, Therefore values would be empty as well. This would be a heartbeat")
                logging.debug("Log is empty, Therefore values would be empty as well. This would be a heartbeat")
            else:
                print("Length " + str(len(self.log)) + " k: " + str(k) + " nextIndex " + str(
                    len(self.nextIndex)) + " nextIndexValue: " + str(self.nextIndex[k - 1]))
                logging.debug("Length " + str(len(self.log)) + " k: " + str(k) + " nextIndex " + str(
                    len(self.nextIndex)) + " nextIndexValue: " + str(self.nextIndex[k - 1]))
                if not (self.nextIndex[k - 1] > self.getLastIndex()):  # need to do this check again for HB without
                    # entries
                    values.append(self.log[self.nextIndex[k - 1]])
            if len(values) == 0:
                info['values'] = None
            else:
                info['values'] = pickle.dumps(values)
                # print(info['values'])
                # print(pickle.loads(info['values']))
            if self.state is State.LEADER:
                result, term = v.appendEntries(info)
                print("RESULT: {0} Term {1}".format(result, term))
                logging.debug("RESULT: {0} Term {1}".format(result, term))
                if result:
                    # update the nextIndex and matchindex
                    if values:
                        id = values[-1].id
                        if self.matchIndex[k - 1] <= id:
                            self.matchIndex[k - 1] = id
                        self.nextIndex[k - 1] = id + 1
                    continue
                    # return True
                else:
                    if term > self.currentTerm:
                        print("Node {0} is no longer the leader. converting to Follower".format(self.id))
                        logging.debug("Node {0} is no longer the leader. converting to Follower".format(self.id))
                        self.state = State.FOLLOWER
                        return False
                    else:
                        print("AppendEntry was rejected by node {0}".format(k))
                        print("Reducing the next index value for node {0}".format(k))
                        logging.debug("AppendEntry was rejected by node {0}".format(k))
                        logging.debug("Reducing the next index value for node {0}".format(k))
                        self.nextIndex[k - 1] = self.nextIndex[k - 1] - 1 if self.nextIndex[k - 1] > 1 else 0
                        print("try again with the last ")
            else:
                print("Something happened. Node {0} is no longer the leader".format(self.id))
                logging.debug("Something happened. Node {0} is no longer the leader".format(self.id))
                return False

    def printLog(self):
        print("Printing the log of node {0}".format(self.id))
        logging.debug("Printing the log of node {0}".format(self.id))
        for e in self.log:
            print(e, end='')
            logging.debug(e)
        print("")
        logging.debug("")

    def main(self):
        print('Number of arguments:', len(sys.argv), 'arguments.')
        print('Argument List:', str(sys.argv))

        if len(sys.argv) > 1:
            print("Server ip is {0}".format(sys.argv[1]))
            self.HOST = sys.argv[1]
            print("Server Ip updated")

        if len(sys.argv) > 2:
            print("Client's ip is {0}".format(sys.argv[2]))
            self.clientip = sys.argv[2]

        else:
            print("User did not choose a client ip default is 127.0.0.1")
            self.clientip = "127.0.0.1"

        if len(sys.argv) > 3:
            print("user inputted client port {0}".format(sys.argv[3]))
            self.clientPort = int(sys.argv[3])
        else:
            print("User did not choose a port for the node. Random port between 55000-63000 will be selected")
            port = random.randint(55000, 63000)
            print("Random port {0} selected".format(port))
            self.clientPort = port

        self.initializeTheNode()
        self.sendNodePort()
        self.createRPCServer()

        print("Ready to start the Raft Server. Please wait until all the nodes are ready to continue. Then press Enter")
        if input() == "":
            print("Started Creating the Raft Server")
            self.mapofNodes = self.getMapData()
            print(self.mapofNodes)
            print("Creating the proxy Map")
            self.createProxyMap()
            print(self.map)
            logging.debug(self.map)
            for k, v, in self.map.items():
                if k < 100:
                    self.noOfNodes +=1

            # self.createThreadToListen()
            # self.createHeartBeatThread()
            self.menu(self)

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
            strReq = self.createJSONReq(1)
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

    def createJSONReq(self, typeReq, nodes=None, slot=None):
        # Initialize node
        if typeReq == 1:
            request = {"req": "1"}
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

    def getJsonObj(self, input):
        jr = json.loads(input)
        return jr

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

    def printTest(self):
        print("I am node {0}".format(self.id))

    def menu(self, d):
        self.createTimeoutThread()
        self.createGameStateUpdateThread()
        while True:
            print("Display Raft DashBoard\t[d]")
            print("Print log\t[p]")
            print("Print Game State\t[g]")
            resp = input("Choice: ").lower().split()
            if not resp:
                continue
            elif resp[0] == 'r':
                self._diagnostics()
            elif resp[0] == 'p':
                self.printLog()
            elif resp[0] == 'g':
                self.displayState()
            elif resp[0] == 'e':
                exit(0)

    def _diagnostics(self):
        print("Printing Diagnostics")
        print("Node {0}".format(self.id))
        print("ServerIP: {0}".format(self.HOST))
        print("Raft Server IP: {0}".format(self.clientip))
        print("Raft Port: {0}".format(self.clientip))
        print("CommitIndex: {0}".format(self.commitIndex))
        print("ServerIP: {0}")
        print("ServerIP: {0}")

    def updateCommittedEntries(self):
        temp = self.commitIndex
        for i in range(temp + 1):
            self.log[i].iscommitted = True

    def getLeaderInfo(self):
        # returns leader's id or None if there is no leader at the moment
        if self.state == State.FOLLOWER:
            return self.votedFor
        elif self.state == State.CANDIDATE:
            return None
        else:
            return self.id


    def setPlayer(self, id, input):
        if self.state is State.LEADER:
            flag = True
            for e in self.log:
                if e.choice == input:
                    flag = False
            if flag:
                entry = Entry(0, self.currentTerm)            
                self.log.append(entry)                 
                entry.player = id
                entry.choice = input
                entry.move = "c"
                entry.id = len(self.log) - 1
                print("Entry ID: {0}".format(entry.id))
                logging.debug("Entry ID: {0}".format(entry.id))

                for k, v in self.map.items():
                    if k != self.id and k < 100:
                        self.callAppendEntryForaSingleNode(k, v)

                return 1
            else:
                return 2
        else:
            print("Node {0} is not the leader. cannot add the entry. Try the leader".format(self.id))
            logging.debug("Node {0} is not the leader. cannot add the entry. Try the leader".format(self.id))
            return 3

    def playerMove(self, id, input):
        if self.state is State.LEADER:

            entry = Entry(0, self.currentTerm)             
            self.log.append(entry)
            entry.player = id
            entry.move = input
            entry.id = len(self.log) - 1 
            print("Entry ID: {0}".format(entry.id))
            logging.debug("Entry ID: {0}".format(entry.id))

            for k, v in self.map.items():
                if k != self.id and k < 100:
                    self.callAppendEntryForaSingleNode(k, v)

            if id == self.blueID:
                oppID = self.redID
                oppState = self.redState
            else:
                oppID = self.blueID
                oppState = self.blueState
            if input == "q":
                if oppState == "s":
                    return 1
                else:
                    if random.random() < 0.10:
                        return int(oppID)
                    else:
                        return 2
            elif input == "w":
                if oppState == "a":
                    return 1
                else:
                    if random.random() < 0.10:
                        return int(oppID)
                    else:
                        return 2
            else:
                return 0
        else:
            print("Node {0} is not the leader. cannot add the entry. Try the leader".format(self.id))
            logging.debug("Node {0} is not the leader. cannot add the entry. Try the leader".format(self.id))
            return False


    
    def displayState(self):
        print("Blue Node: "+ str(self.blueID))
        print("Blue State: "+ str(self.blueState))
        print("Red Node: "+ str(self.redID))
        print("Red State: "+ str(self.redState))

    def createGameStateUpdateThread(self):
        thread = threading.Thread(target=self.stateUpdate)
        thread.daemon = True
        thread.start()

    def stateUpdate(self):
        while True:
            if self.stateIndex < self.commitIndex+1:
                for e in range(self.stateIndex, self.commitIndex+1):
                    print(self.log[e])
                    if self.log[e].move == "c":
                        if self.log[e].choice == "1":
                            self.redID = self.log[e].player
                        elif self.log[e].choice == "2":
                            self.blueID = self.log[e].player
                    elif self.log[e].move == "q" or self.log[e].move == "w":
                        if self.redID == self.log[e].player:
                            self.redState = None
                        else:
                            self.blueState = None
                    elif self.log[e].move == "a":
                        if  self.redID == self.log[e].player:
                            self.redState = "a"
                        else:
                            self.blueState = "a"
                    elif self.log[e].move == "s":
                        if self.redID == self.log[e].player:
                            self.redState = "s"
                        else:
                            self.blueState = "s"
                    self.stateIndex+=1

class State(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3


class Entry:
    def __init__(self, id, term):
        self.id = id
        self.term = term
        self.player = None
        self.choice = None
        self.move = None
        self.iscommitted = False

    def __str__(self):
        return "Entry id:{0} term:{1} Player:{2} Choice:{3} Move:{4} isCommitted: {5}\t".format(self.id, self.term, self.player, self.choice, self.move, self.iscommitted)


class Vote:
    def __init__(self):
        self.votes = 0
        self.mutex = threading.Lock()

    def getVotes(self):
        return self.votes

    def addVote(self):
        self.mutex.acquire()
        self.votes = self.votes + 1
        self.mutex.release()




if __name__ == "__main__":
    raft = Raft(1)
    raft.main()
