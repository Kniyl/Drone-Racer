# Lots of duck typing in this file, maybe we can try to do better

import os
import sys
import socket
from threading import Thread
from select import select
try:
    from serial import Serial
    from xbee import XBee, ZigBee
except ImportError:
    XBee = None


class BaseReader(Thread):
    """Base class for custom data readers."""

    def __init__(self, update_function):
        """Spawn a thread that continuously read data for drones statuses.
        
        Parameter:
          - update_function: the function that will be called each time a
            valid data is read.
        """
        super().__init__(name="reader")
        self._update_data = update_function
        self._should_continue = True
        self.start()

    def run(self):
        """The main action of the thread.

        Wait for data, read them and send them to the rest of the application
        for further computation.
        """
        while self._should_continue:
            try:
                gate, drone = self.read_new_value()
            except TypeError:
                pass
            else:
                self._process_value(gate, drone)

    def stop(self):
        """Signal that the thread has to stop reading its inputs."""
        self._should_continue = False

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier, drone
        number). Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def _process_value(self, gate, drone):
        """Send input data to the rest of the application.

        Parameters:
          - gate: the gate identification letter(s)
          - drone: the drone identification number (0-based)
        """
        if drone < 0:
            return
        self._update_data(gate, drone)


class StdInReader(BaseReader):
    """Read data from stdin. Primarily used for tests and debug."""

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier,
        drone number).

        Convert data such as "0 1" to the tuple ('A', 1).
        """
        raw = input('[@] ').split()
        try:
            gate, drone = raw
            return chr(int(gate) + ord('A')), int(drone)
        except ValueError:
            pass


class _UDPReader(BaseReader):
    """Read data from UDP datagrams. Used when communicating via WiFi
    with the gates.
    """

    def __init__(self, iface, port, update_function):
        """Spawn a thread that continuously read data for drones statuses.
        
        Parameter:
          - iface: the address of the interface to listen on.
          - port: the socket port to listen on.
          - update_function: the function that will be called each time a
            valid data is read.
        """
        com = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        com.bind((iface, port))
        self._socket = [com]
        super().__init__(update_function)

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier,
        drone number).

        Decode an UDP datagram containing b"C:3" to the tuple ('C', 2).
        """
        # Non-blocking read so this thread will shut down with the application
        ready, _, _ = select(self._socket, [], [], 0)
        for socket in ready:
            msg = socket.recv(128) # Way too much for messages like <A:1>
            try:
                gate, drone = msg.split(b':')
                gate = gate.decode()
                # Compensate for the drone numbering vs. its indexing
                drone = int(drone) - 1
            except (UnicodeError, ValueError) as e:
                print('Le message', msg, 'a été reçu mais n’est pas'
                      'compris par l’application.', file=sys.stderr)
                print(e, file=sys.stderr)
            else:
                return gate, drone


class UDPReader:
    """Factory of _UDPReaders."""

    def __init__(self, port):
        """Save parameters for future use.

        Parameter:
          - port: the socket port to listen on.
        """
        self._port = port

    def __call__(self, callback):
        """Generate the appropriate class to read data.

        Parameter:
          - callback: the function that will be called each
            time a valid data is read.
        """
        return _UDPReader(socket.gethostname(), self._port, callback)


if XBee is None:
    class _BeeReader(BaseReader):
        """Read data from a serial port bound to an XBee.
        Dummy implementation because xbee module could not be loaded.
        """

        def read_new_value(self):
            """Cancel this thread to avoid burning resources."""
            self._should_continue = False

    def XBeeReader(*args, **kwargs):
        """Wrapper around the xbee module to integrate our _BeeReaderMixin
        into the appropriate base class.
        Dummy implementation because xbee module could not be loaded.
        """
        print('Le module XBee est instrouvable. Aucune donnée ne pourra',
              'être lue', file=sys.stderr)
        return _BeeReader
else:
    class _BeeReaderMixin:
        """Read data from a serial port bound to an XBee."""

        def __init__(self, serial, callback):
            """Initialize the XBee reader thanks to the mro.

            Parameters:
              - serial: the serial port object to read data from
              - callback: the function that will be called each
                time a valid data is read.
            """
            self._update_data = callback
            super().__init__(serial, callback=self._process_value)

        def _process_value(self, response_dict):
            """Convert a raw data received in a frame by the XBee
            into suitable data for the application.

            Should be called each time a frame is read by the XBee.
            """
            try:
                gate, drone = response_dict['rf_data'].split(b':')
                gate = gate.decode()
                # Compensate for the drone numbering vs. its indexing
                drone = int(drone) - 1
            except (UnicodeError, ValueError) as e:
                print('Le message', response_dict['rf_data'],
                      'a été reçu mais n’est pas compris par l’application.',
                      file=sys.stderr)
                print(e, file=sys.stderr)
            except KeyError as e:
                print('Un message ne contenant pas de données a été reçu.',
                      file=sys.stderr)
                print(e, file=sys.stderr)
            else:
                self._update_data(gate, drone)

        def stop(self):
            """Halt the thread from reading its input and close the
            underlying serial port.
            """
            self.halt()
            self.serial.close()

    class XBeeReader:
        """Wrapper around the xbee module to integrate our _BeeReaderMixin
        into the appropriate base class.
        """

        def __init__(self, *args, **kwargs):
            """Save parameters for future use.
            Everything is used to initialize a serial.Serial object
            except for the named attribute 'zigbee' which define the
            base class to use.

            Parameter:
              - zigbee: whether to use the xbee.ZigBee base class or
                the xbee.XBee one
            """
            zigbee = kwargs.pop('zigbee', False)
            self._args = args
            self._kwargs = kwargs
            self._base_cls = ZigBee if zigbee else XBee

        def __call__(self, callback):
            """Generate the appropriate class to read data.

            Parameter:
              - callback: the function that will be called each
                time a valid data is read.
            """
            serial = Serial(*self._args, **self._kwargs)
            self._args = None
            self._kwargs = None
            return type('XBeeReader', (_BeeReaderMixin, self._base_cls), {})(
                    serial, callback)
