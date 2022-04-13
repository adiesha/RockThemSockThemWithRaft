import random
import threading
from enum import Enum
from time import sleep

import numpy as np


class Raft:
    def __init__(self, id):
        # these attributes should be persistent
        self.id = id
        self.currentTerm = 0
        self.votedFor = None
        self.log = []
        self.map = None  # Map about the other nodes
        self.noOfNodes = None

        self.state = State.FOLLOWER
        self.leader = None

        # volatile states
        self.commitIndex = 0
        self.lastApplied = 0

        # volatile state on leader
        self.nextIndex = None
        self.matchIndex = None

        # check this flag every after every timeout
        # if false issue go for election
        # if not set this to false and choose another timeout and check after that time
        self.receivedHeartBeat = False

        self.mutex = threading.Lock()

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the heartbeat for leader
    # We can create a daemon that issues appendEntries to all the nodes if they are the leader
    def heartbeat(self, message):
        print("heartbeat invoked in node {0}".format(self.id))

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the appendEntries for leader
    def appendEntries(self, info):
        # First check whether this is a initial heartbeat by a leader.
        check = self.checkwhetheritsaheratbeat(info)
        if check is not None:
            return check, self.currentTerm
        else:
            if info['term'] < self.currentTerm:
                return False, self.currentTerm
            prevLogIndex = info['previouslogindex']
            prevLogTerm = info['previouslogterm']

            if prevLogIndex == -1:
                pass
            else:
                if self.log[prevLogIndex].term != prevLogTerm:
                    return False, self.currentTerm

            # received actual appendEntry do the logic
            entries = info['values']
            for e in entries:
                print("Appending Entries in node {0} by the leader".format(self.id))
                print("Id of the entry that we are adding is {0}".format(e.id))
                if e.id != len(self.log):
                    print("Entry that we are adding is not at the correct log index {0} log length {1}".format(e.id,
                                                                                                               len(self.log)))
                    raise Exception(
                        "Entry that we are adding is not at the correct log index {0} log length {1}".format(e.id,
                                                                                                             len(self.log)))
                else:
                    self.log.append(e)
        return True, self.currentTerm

    def checkwhetheritsaheratbeat(self, info):
        if info['values'] is None:
            if info['term'] < self.currentTerm:
                return False
            else:
                print("Heartbeat received by node {0} from the leader {1}".format(self.id, info['leaderid']))
                self.leader = info['leaderid']
                self.state = State.FOLLOWER
                self.receivedHeartBeat = True
                self.currentTerm = info['term']
                return True
        else:
            return None

    # Request RPC is the method that is invoked by a candidate to request the vote
    def requestVote(self, info):
        # info is a dict: nodeid, term, lastindexofthelog lastlogterm
        candidateid = info['nodeid']
        term = info['term']
        candidateslastindexofthelog = info['lastindexofthelog']
        candidateslastlogterm = info['lastlogterm']

        if term < self.currentTerm:
            return False
        else:  # term >= self.currentTerm
            # Need to implement this
            if self.votedFor is None:
                # Compare the term of the last entry against candidates last term
                # if they are the same then compare the last log index
                if candidateslastlogterm < self.getLastTerm():
                    print("Candidates last term is smaller than the current term of the node {0}".format(self.id))
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
                            return False
                        else:
                            self.votedFor = candidateid
                            return True
                    else:
                        self.votedFor = candidateid
                        return True
                pass
            else:  # Already voted for someone
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
        info['value'] = entry

        # Node is the leader
        for k, v, in self.map.items():
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

        self.state = State.CANDIDATE
        self.currentTerm = self.currentTerm + 1
        self.votedFor = self.id
        vote.addVote()
        inf = self.createInfo()
        print(
            "Node:{0} Term: {1} state: {2} votedFor: {3}".format(self.id, self.currentTerm, self.state, self.votedFor))

        for k, v in self.map.items():
            if k != self.id:
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
        dict['previouslogindex'] = self.getLastIndex() - 1
        dict['previouslogterm'] = self.getLastTerm()
        dict['values'] = None
        dict['leadercommit'] = self.commitIndex

        return dict

    def timeout(self):
        while True:
            randomTimeout = random.randint(2, 5)
            if self.state == State.FOLLOWER:
                print("Chosen timeout for node {0} is {1}".format(self.id, randomTimeout))
                sleep(randomTimeout)
                if self.receivedHeartBeat:
                    self.receivedHeartBeat = False
                    print(
                        "Timeout occurred but Heartbeat was received by the node {0} earlier. Picking a new timeout".format(
                            self.id))
                    continue
                    # pick a new timeout
                else:
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
                            elif self.state == State.FOLLOWER:
                                print("Looks like we found a leader for the term, leader is {0}".format(self.votedFor))
            elif self.state == State.LEADER:
                randomTimeout = random.randint(1, 2)
                # send heartbeats
                info = self.createApppendEntryInfo()
                info['value'] = None
                for k, v in self.map.items():
                    if k != self.id:
                        self.callAppendEntryForaSingleNode(k, v, hb=True)
                        # v.appendEntries(info)

                sleep(randomTimeout)
                print("Sending Heartbeats")
                pass

    def createTimeoutThread(self):
        thread = threading.Thread(target=self.timeout)
        thread.daemon = True
        thread.start()
        return thread

    def addRequest(self, entry):
        if self.state is State.LEADER:
            # add the entry to the log
            entry = Entry(0, self.currentTerm)  # id is not the correct one so we update it in the next two lines
            self.log.append(entry)
            entry.id = len(self.log) - 1
            print("Entry ID: {0}".format(entry.id))

            for k, v in self.map.items():
                if k != self.id:
                    self.callAppendEntryForaSingleNode(k, v)

        else:
            print("Node {0} is not the leader. cannot add the entry. Try the leader".format(self.id))
            return False

    def callAppendEntryForaSingleNode(self, k, v, hb=False):
        # this method should spawn a thread
        while True:
            info = self.createApppendEntryInfo()
            values = []
            if self.nextIndex[k - 1] > self.getLastIndex() and not hb:
                print("Node {0} is up to date".format(k))
                return True
            values.append(self.log[self.nextIndex[k - 1]])
            info['values'] = values
            if self.state is State.LEADER:
                result, term = v.appendEntries(info)
                print("RESULT: {0} Term {1}".format(result, term))
                if result:
                    # update the nextIndex and matchindex
                    id = values[-1].id
                    if self.matchIndex[k - 1] <= id:
                        self.matchIndex[k - 1] = id
                    self.nextIndex[k - 1] = id + 1
                    continue
                    # return True
                else:
                    if term > self.currentTerm:
                        print("Node {0} is no longer the leader. converting to Follower".format(self.id))
                        self.state = State.FOLLOWER
                        return False
                    else:
                        print("AppendEntry was rejected by node {0}".format(k))
                        print("Reducing the next index value for node {0}".format(k))
                        self.nextIndex[k - 1] = self.nextIndex[k - 1] - 1
                        print("try again with the last ")
            else:
                print("Something happened. Node {0} is no longer the leader".format(self.id))
                return False

    def printLog(self):
        print("Printing the log of node {0}".format(self.id))
        for e in self.log:
            print(e, end='')
        print("")


class State(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3


class Entry:
    def __init__(self, id, term):
        self.value = None
        self.id = id
        self.term = term
        self.iscommitted = False

    def __str__(self):
        return "id:{0} term:{1} val:{2}\t".format(self.id, self.term, self.value)


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
