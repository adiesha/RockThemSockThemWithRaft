import pickle
from xmlrpc.client import ServerProxy
from rpc_server_wth_class import Apple  # do not optimize the imoprts otherwise you would remove this

proxy = ServerProxy('http://localhost:3000')

if __name__ == '__main__':
    print(proxy.print())

    # receiving pickled object
    data = proxy.sendBinary().data

    a = pickle.loads(data)
    print(True if type(a) == Apple else False)
    print(a.a)
    print(proxy.printB())
    print(proxy.printParameter(2))
    try:
        print(proxy.printDict({"a": 12, "b": 45, 3: "12"}))
    except TypeError:
        print("Dictionary keys should be strings")

    # As long as keys are strings, you can send stuff using rpc, if you want to send
    # an object convert it to byte array and send it as a value
    print(proxy.printDict({"a": 12, "b": 45, "c": pickle.dumps(Apple())}))
