import time
import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu, exceptions as modbus_except
from gset_p2p_network import *

METER_SLEEP = 15

class EnergyMeter:
    def __init__(self, port='/dev/ttyS0', mode='local',
                 p2p_controller_host=None, p2p_controller_port=None):
        self.port = port
        self.sensor, self.master = self._init_port()
        self.mode = mode
        if self.mode == 'network':
            self.net_server = NetServer(get_local_ip_address(), ENERGY_METER_PORT)
            if p2p_controller_host is None:
                self.p2p_controller_host = get_local_ip_address()
            else:
                self.p2p_controller_host = p2p_controller_host

            if p2p_controller_port is None:
                self.p2p_controller_port = ENERGY_READING_PORT
            else:
                self.p2p_controller_port = p2p_controller_port
        self.reset()
        self.is_debug = DEBUG

    def reset(self):
        self.voltage = 0.0
        self.current = 0.0
        self.power = 0.0
        self.energy = 0.0
        self.frequency = 0.0
        self.power_factor = 0.0
        self.alarm = 0.0
        self._close_port()
        self.sensor, self.master = self._init_port()

    def start(self):
        if self.sensor is None or self.master is None:
            self.reset()
        self.force_stop = False
        while not self.force_stop and True:
            try: 
                data = self.master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
                self.voltage = data[0] / 10.0  # [V]
                self.current = (data[1] + (data[2] << 16)) / 1000.0  # [A]
                self.power = (data[3] + (data[4] << 16)) / 9.8  # [W]
                self.energy = data[5] + (data[6] << 16)  # [Wh]
                self.frequency = data[7] / 10.0  # [Hz]
                self.powerFactor = data[8] / 100.0
                self.alarm = data[9]  # 0 = no alarm
            except modbus_except.ModbusInvalidResponseError:
                pass
            except AttributeError as e:
                print(e)
            except Exception as e:
                print(e)
              
        

            self.report()

            time.sleep(METER_SLEEP)

    def stop(self):
        self._close_port()
        self.force_stop = True

    def _init_port(self):
        sensor = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=0
        )
        master = modbus_rtu.RtuMaster(sensor)
        master.set_timeout(2.0)
        master.set_verbose(True)
        # Changing power alarm value to 100W
        # master.execute(1, cst.WRITE_SINGLE_REGISTER, 1, output_value=100)
        return sensor, master

    def _close_port(self):
        try:
            self.master.close()
            if self.sensor.is_open:
                self.sensor.close()
            self.master = None
            self.sensor = None
        except:
            pass

    def report(self):
        readings = [self.voltage, self.current, self.power, self.energy,
                    self.frequency, self.power_factor, self.alarm]

        if self.mode == 'network':
            #print("#sending message from energy meter", readings)
            #print("#p2p host", self.p2p_controller_host)
            #print("#p2p port", self.p2p_controller_port)
            self.net_server.send_message(
                self.p2p_controller_host, self.p2p_controller_port, message=readings)

        if self.mode == 'local' or self.is_debug:
            print('Voltage [V]: ', self.voltage)
            print('Current [A]: ', self.current)
            print('Power [W]: ', self.power)  # active power (V * I * power factor)
            print('Energy [Wh]: ', self.energy)
            print('Frequency [Hz]: ', self.frequency)
            print('Power factor []: ', self.power_factor)
            print('Alarm : ', self.alarm)
            print('.....')


if __name__=="__main__":
    meter = EnergyMeter()
    meter.start()
