from Raft import Raft


def main():
    testSimpleMajorityMethod()


def testSimpleMajorityMethod():
    raft = Raft(1)
    raft.noOfNodes = 10
    print(raft.getSimpleMajority())

    raft.noOfNodes = 11
    print(raft.getSimpleMajority())

    raft.noOfNodes = 17
    print(raft.getSimpleMajority())


def testRequestVoteMethod():
    pass


if __name__ == '__main__':
    main()
