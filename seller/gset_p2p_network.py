import socket
import time
from threading import Thread

SERVER_PORT = 8484
CLIENT_PORT = 4848
DEBUG = True
ENERGY_METER_PORT = 7711
ENERGY_READING_PORT = 2201
ENERGY_ORDER_PORT = 2202


def get_local_ip_address():
    return '10.64.194.14'
    #with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    #    s.connect(("8.8.8.8", 1))
    #    return s.getsockname()[0]

class NetServer:

    def __init__(self, host, port=SERVER_PORT):
        self.host = host
        self.port = port

    def encode_message(self, msg):
        return '#'.join(map(str, msg)).encode('utf-8')

    def send_message(self, client_host, client_port, message=[]):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            client_addr = (client_host, client_port)
            message = self.encode_message(message)
            if len(message) > 0:
                s.sendto(message, client_addr)

    def test(self):
        for i in range(2):
            relay_number = i + 1
            energy_to_transmit = relay_number * 100
            self.send_message(get_local_ip_address(), CLIENT_PORT, [relay_number, energy_to_transmit])
            time.sleep(1)
        self.send_message(get_local_ip_address(), CLIENT_PORT, ['STOP'])
        print('Bye!')


class NetClient:

    def __init__(self, host, port=CLIENT_PORT):
        self.host = host
        self.port = port
        self.force_stop = False
 
    def stop(self):
        print("#### FORCE STOP NET CLIENT!")
        self.force_stop = True
      

    def decode_message(self, msg):
        return msg.decode('utf-8').split('#')

    def recv_message(self, handler=None):
        self.force_stop = False
 
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while not self.force_stop:
                data, addr = s.recvfrom(1024)
                message = self.decode_message(data)
                print("message")
                if message[0] == 'STOP':
                    print('See You!')
                    break
                if handler is not None:
                    handler(message)
                time.sleep(2)
        

    def test(self):
        self.recv_message()

def start_client():
    print('start client')
    print(get_local_ip_address())
    client = NetClient(get_local_ip_address())
    client.test()

def start_server():
    print('start server')
    server = NetServer(get_local_ip_address())
    server.test()

def test_networking():
    client_thread = Thread(target=start_client)
    server_thread = Thread(target=start_server)
    client_thread.start()
    server_thread.start()
    server_thread.join()
    client_thread.join()


if __name__=="__main__":
    test_networking()


