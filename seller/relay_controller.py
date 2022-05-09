from relay import relay_factory, on_relay, off_relay, off_all_relay
from energy_meter import EnergyMeter, METER_SLEEP
from gset_p2p_network import *
from threading import Thread
from random import randint
import time


class RelayController:
    def __init__(self):
        self.relay = relay_factory('default')
        self.test_relay()
        self.host = get_local_ip_address()
        self.energy_reading_port =  ENERGY_READING_PORT
        self.order_receiving_port = ENERGY_ORDER_PORT
        self.energy_meter_port = '/dev/ttyS0'
        self.energy_transmitted = 0.0
        self.energy_ordered = 0.0
        self.is_transmit_energy = False
        self.energy_meter = EnergyMeter(
            self.energy_meter_port, 'network', self.host, self.energy_reading_port)
        self.energy_meter_net_client = NetClient(self.host, self.energy_reading_port)

        self.controller_client = NetClient(self.host, self.order_receiving_port)
        self.is_terminated = False
        self.T = 3600 / METER_SLEEP
        self.relay_number = 0

    def test_relay(self):
        print('test relay...')
        on_relay(self.relay, 1)
        time.sleep(2)
        off_relay(self.relay, 1) 
        time.sleep(2)

    def start_energy_meter(self):
        self.energy_meter.start()

    def stop_energy_meter(self):
        self.energy_meter.stop()

    def on_energy_read(self, message):
        voltage, current, power, energy_wh, freq, power_factor, alarm = message
        self.energy_transmitted = self.energy_transmitted + float(power) / self.T
        print("Energy transmitted {}W".format(self.energy_transmitted))

        if self.energy_transmitted >= self.energy_ordered:
            self.is_transmit_energy = False
            print("Energy transmission DONE", self.is_transmit_energy)
            self.energy_meter_net_client.stop()

    def do_energy_reading(self): 
        self.start_energy_meter()

    def do_check_energy_transmitted(self):
        self.energy_meter_net_client.recv_message(self.on_energy_read)
        off_relay(self.relay, self.relay_number)
        self.stop_energy_meter()

    def do_transmit_energy(self, relay_number, energy_ordered):
        self.energy_transmitted = 0.0
        self.energy_ordered = energy_ordered

        self.relay_number = relay_number
        self.is_transmit_energy = True
        self.relay.h.close()
        time.sleep(2)
        self.relay = relay_factory('default')
        on_relay(self.relay, relay_number)
        print('opened relay#{}'.format(relay_number))

        self.energy_meter = EnergyMeter(
            self.energy_meter_port, 'network', self.host, self.energy_reading_port)
   
        time.sleep(2)       

        meter_thread = Thread(target=self.do_energy_reading)
        relay_thread = Thread(target=self.do_check_energy_transmitted)
        relay_thread.start()
        meter_thread.start()        
        
        print("Start transmitting {}W via relay#{}".format(
            energy_ordered, relay_number))

        relay_thread.join()
        meter_thread.join()

        print("Transmitted {}W via relay#{}".format(
            self.energy_transmitted, relay_number))

    def on_order_received(self, message):
        print('recv_order:', message)
        if len(message[0]) > 0:
            if message[0] == 'STOP':
                self.is_terminated = True

            relay_number = int(message[0])
            energy_ordered = float(message[1])

            self.do_transmit_energy(relay_number, energy_ordered)

    def receive_order(self):
        while True:
            print('waiting for energy order...')
            self.controller_client.recv_message(self.on_order_received)
            off_all_relay(self.relay)
            self.stop_energy_meter()
            time.sleep(60)

    def do_receive_energy(self, relay_number, energy_ordered):
        self.energy_received = 0.0
        self.energy_ordered = energy_ordered

        print('open relay#{}'.format(relay_number))
        on_relay(self.relay, relay_number)

        self.relay_number = relay_number
        self.is_transmit_energy = True

        meter_thread = Thread(target=self.do_energy_reading)
        relay_thread = Thread(target=self.do_check_energy_transmitted)
        relay_thread.start()
        meter_thread.start()

        print("Start receiving {}W via relay#{}".format(
            energy_ordered, relay_number))

        relay_thread.join()
        meter_thread.join()

        print("Received {}W via relay#{}".format(
            self.energy_transmitted, relay_number))

    def send_order(self, relay_number=1, energy_to_buy=5):
        energy_master = NetServer(get_local_ip_address(), SERVER_PORT)
        energy_order_host = get_local_ip_address()
        print('energy_order_host', energy_order_host)
        rn = relay_number
        energy = energy_to_buy
        message = [rn, energy]
        energy_master.send_message(energy_order_host, ENERGY_ORDER_PORT, message)

        self.do_receive_energy(relay_number, energy_to_buy)

        energy_master.send_message(energy_order_host, ['STOP'])


def test_energy_order():
    energy_master = NetServer(get_local_ip_address(), SERVER_PORT)
    energy_order_host = get_local_ip_address()
    print('energy_order_host', energy_order_host)
    for i in range(1):
        rn = 1
        energy = 200 
        message = [rn, energy]
        energy_master.send_message(energy_order_host, ENERGY_ORDER_PORT, message)
        time.sleep(15)

    energy_master.send_message(energy_order_host, ['STOP'])


def test_relay_controller_thread():
    rc = RelayController()
    rc_thread = Thread(target=rc.receive_order)
    eo_thread = Thread(target=test_energy_order)
    print("start simulation")

    rc_thread.start()
    time.sleep(2)
    eo_thread.start()

    eo_thread.join()
    rc_thread.join()
    print("end simulation")


def test_receive_order():
    rc = RelayController()
    rc.receive_order()


def test_send_order():
    rc = RelayController()
    rc.send_order()


if __name__=="__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == '-r':
        test_receive_order()
    else:
        test_send_order()
