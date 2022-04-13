from time import sleep

from Raft import Raft, State, Entry


def main():
    testSimpleMajorityMethod()
    testRequestVoteMethod()
    testingTimoutMethod()


def testSimpleMajorityMethod():
    raft = Raft(1)
    raft.noOfNodes = 10
    print(raft.getSimpleMajority())

    raft.noOfNodes = 11
    print(raft.getSimpleMajority())

    raft.noOfNodes = 17
    print(raft.getSimpleMajority())


def testRequestVoteMethod():
    r1 = Raft(1)
    r1.noOfNodes = 2
    r2 = Raft(2)
    r2.noOfNodes = 2

    nodeMap = {1: r1, 2: r2}
    r1.map = nodeMap
    r2.map = nodeMap

    votes = 1
    r1.state = State.CANDIDATE
    r1.currentTerm = r1.currentTerm + 1
    r1.votedFor = r1.id
    inf = r1.createInfo()
    vote2 = r2.requestVote(inf)
    if vote2:
        votes = votes + 1
    if votes >= r1.getSimpleMajority():
        r1.state = State.LEADER


def testingTimoutMethod():
    r1 = Raft(1)
    r1.noOfNodes = 3
    r2 = Raft(2)
    r2.noOfNodes = 3
    r3 = Raft(3)
    r3.noOfNodes = 3

    nodeMap = {1: r1, 2: r2, 3: r3}
    r1.map = nodeMap
    r2.map = nodeMap
    r3.map = nodeMap
    r1.createTimeoutThread()
    r2.createTimeoutThread()
    r3.createTimeoutThread()

    sleep(5)

    e = Entry(1, 2)
    r1.addRequest(e)
    r2.addRequest(e)
    r3.addRequest(e)

    print(r1.nextIndex)
    print(r2.nextIndex)
    print(r3.nextIndex)


    e = Entry(2, 3)
    r1.addRequest(e)
    r2.addRequest(e)
    r3.addRequest(e)

    r1.printLog()
    r2.printLog()
    r3.printLog()

    sleep(4)
    print(r1.matchIndex)
    print(r2.matchIndex)
    print(r3.matchIndex)


    print(r1.nextIndex)
    print(r2.nextIndex)
    print(r3.nextIndex)

    r1.printLog()
    r2.printLog()
    r3.printLog()

    sleep(1000)


if __name__ == '__main__':
    main()