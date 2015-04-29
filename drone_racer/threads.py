import os
import sys
from threading import Thread
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
            update_function: the function that will be called each time a
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
            gate, drone = self.read_new_value()
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
            gate: the gate identification letter(s)
            drone: the drone identification number (1-based)
        """
        if drone < 0:
            return
        self._update_data(gate, drone)


class StdInReader(BaseReader):
    """Read data from stdin. Primarily used for tests and debug."""

    def read_new_value(self):
        raw = input('[@] ').split()
        if len(raw) != 2:
            return '?', -1
        try:
            value = (chr(int(raw[0])+65), int(raw[1]))
        except:
            value = '?', -1
        return value


if XBee is None:
    class _BeeReader(BaseReader):
        """Read data from a serial port bound to an XBee.
        Dummy implementation when xbee module can not be loaded."""

        def read_new_value(self):
            self._should_continue = False
            return '?', -1

    def XBeeReader(*args, **kwargs):
        print('xbee module not found. This reader is up to no good',
                file=sys.stderr)
        return _BeeReader
else:
    class _BeeReaderMixin:
        """Read data from a serial port bound to an XBee."""

        def __init__(self, serial, callback):
            super().__init__(serial, callback=self._process_value)
            self._update_data = callback

        def _process_value(self, response_dict):
            print(response_dict)
            self._update_data('A', 0)

        def stop(self):
            self.halt()
            self.serial.close()

    class XBeeReader:
        def __init__(self, serial_name, zigbee=False):
            self.name = serial_name
            self._base_cls = ZigBee if zigbee else XBee

        def __call__(self, callback):
            serial = Serial(serial_name)
            return type('XBeeReader', (_BeeReaderMixin, self._base_cls), {})(
                    serial, callback)
