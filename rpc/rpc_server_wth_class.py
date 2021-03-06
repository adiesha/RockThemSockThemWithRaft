# RPC tests
import os
import pickle
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer


def main():
    print("Hello from the other side!")
    # Define server
    server = SimpleXMLRPCServer(('localhost', 3000), logRequests=True, allow_none=True)
    # Register the functions that needs to be served
    a = Apple()
    a.b = 67
    server.register_instance(a)

    try:
        print("Serving........")
        server.serve_forever()
    except KeyboardInterrupt:
        print("Exiting")


def list_directory(dir):
    return os.listdir(dir)


class Apple:
    def __init__(self):
        self.a = 6
        self.b = 0

    def print(self):
        print("Apple")
        return "Apple"
        # Note that we can pass any primitive data type as the return value. if we need to pass binary objects then
        # it is tricky

    def sendBinary(self):
        print("hahahsa")
        a = Apple()
        a.a = 10
        pickledmsg = pickle.dumps(a)
        return xmlrpc.client.Binary(pickledmsg)

    def changeApple(self, apple):
        print("Serving 42")
        print(apple.b)
        apple.b = "42"
        pickledmsg = pickle.dumps(apple)
        return xmlrpc.client.Binary(pickledmsg)

    def printB(self):
        return self.b

    def printParameter(self, p):
        print(p)
        pass

    def printDict(self, d):
        print(d)

    def printThread(self):
        print('Threading')

    def multipleReturnVsalues(self):
        return 2, False


if __name__ == '__main__':
    main()
