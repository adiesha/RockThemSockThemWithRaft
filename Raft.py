import random
import threading
from enum import Enum
from time import sleep


class Raft:
    def __init__(self, id):
        # these attributes should be persistent
        self.id = id
        self.currentTerm = 0
        self.votedFor = None
        self.log = None
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

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the heartbeat for leader
    # We can create a daemon that issues appendEntries to all the nodes if they are the leader
    def heartbeat(self, message):
        print("heartbeat invoked in node {0}".format(self.id))

    # This is the remote procedure call for leader to invoke in nodes
    # This is not the procedure call that does the appendEntries for leader
    def appendEntries(self, info):
        # First check whether this is a initial heartbeat by a leader.

        self.receivedHeartBeat = True
        self.leader = info['nodeid']
        self.state = State.FOLLOWER
        print("Appending Entries in node {0} by the leader".format(self.id))

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

        info = self.createInfo()
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

        for k, v in self.map.items():
            if k != self.id:
                # result = self.createDaemon(v.requestVote, inf)
                self.requestVoteFromNode(v, inf, vote)

        if vote.getVotes() >= self.getSimpleMajority():
            print("Found the majority. Making node {0} the leader".format(self.id))
            self.state = State.LEADER
            # send a heartbeat
            return True
        else:
            return False

    def createDaemon(self, func, inf):
        thread = threading.Thread(target=func, args=(inf,))
        thread.daemon = True
        thread.start()
        return thread

    def requestVoteFromNode(self, proxy, inf, vote):
        result = proxy.requestVote(inf)
        if result:
            vote.addVote()

    def getSimpleMajority(self):
        if self.noOfNodes % 2 == 0:
            return int(self.noOfNodes / 2 + 1)
        else:
            return int(self.noOfNodes / 2) + 1

    def getLastTerm(self):
        if self.log is None:
            return 0
        else:
            return self.log[-1].term

    def getLastIndex(self):
        return 0 if self.log is None else len(self.log) - 1

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
                    print("Timeout occurred but Heartbeat was received earlier. Picking a new timeout")
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
                # send heartbeats
                for k, v in self.map.items():
                    if k != self.id:
                        v.appendEntries(self.id)

                sleep(randomTimeout)
                print("Sending Heartbeats")
                pass

    def createTimeoutThread(self):
        thread = threading.Thread(target=self.timeout)
        thread.daemon = True
        thread.start()
        return thread


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
