# RPC tests
import os
from xmlrpc.server import SimpleXMLRPCServer


def main():
    print("Hello from the other side!")
    # Define server
    server = SimpleXMLRPCServer(('localhost', 3000), logRequests=True, allow_none=True)
    # Register the functions that needs to be served
    server.register_function(list_directory)

    try:
        print("Serving........")
        server.serve_forever()
    except KeyboardInterrupt:
        print("Exiting")


def list_directory(dir):
    return os.listdir(dir)


if __name__ == '__main__':
    main()
