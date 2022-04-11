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
        # vote for itself
        # loop the nodes and call the RequestVoteRPC
        pass

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
