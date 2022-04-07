from enum import Enum


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
    def appendEntries(self, message):
        print("Appending Entries in node {0} by the leader".format(self.id))

    # Request RPC is the method that is invoked by a candidate to request the vote
    def requestVote(self, info):
        # info is a dict: nodeid, term, lastindexofthelog
        candidateid = info['nodeid']
        term = info['term']
        candidateslastindexofthelog = info['lastindexofthelog']
        candidateslastlogterm = info['lastlogterm']

        if term < self.currentTerm:
            return False
        else:
            # Need to implement this
            return True


    # invoking appendEntries of other nodes
    # This method should not be exposed to invoke
    def _invokeAppendEntries(self):
        pass

    # This method should invoke heartbeat function of other nodes
    # This method should not be exposed to invoke
    def _invokeHeartBeat(self):
        pass

    def getSimpleMajority(self):
        if self.noOfNodes % 2 == 0:
            return int(self.noOfNodes / 2 + 1)
        else:
            return int(self.noOfNodes / 2) + 1


class State(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3
