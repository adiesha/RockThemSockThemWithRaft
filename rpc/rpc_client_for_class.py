import pickle
from xmlrpc.client import ServerProxy
from rpc_server_wth_class import Apple # do not optimize the imoprts otherwise you would remove this

proxy = ServerProxy('http://localhost:3000')


if __name__ == '__main__':
    print(proxy.print())

    # receiving pickled object
    data = proxy.sendBinary().data

    a = pickle.loads(data)
    print(True if type(a) == Apple else False)
    print(a.a)
    print(proxy.printB())