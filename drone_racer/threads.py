"""Collection of classes to create threaded objects allowing to read
data from various sources.

Readers should be created with whatever parameter they require and
then allow to be called with a callback function. This call return
the threaded object reading data.

These threaded objects are started immediatly and monitor incomming
data to normalize them before feeding them into the callback function.
They can easily be halted using their `stop` method.
"""


import sys
import socket
from threading import Thread
try:
    from serial import Serial
    from xbee import XBee, ZigBee
except ImportError:
    XBee = None

from .i18n import translations


_, _N = translations('utils')


class BaseReader(Thread):
    """Base class for custom data readers."""

    def __init__(self):
        """Spawn a thread that will continuously read data for drones
        statuses.
        """
        super().__init__(name="reader")

    def __call__(self, update_function):
        """Starts the thread with the given callback function to
        process data with.
        
        Parameter:
          - update_function: the function that will be called each time
            a valid data is read.
        """
        self._update_data = update_function
        self._should_continue = True
        self.start()
        # Return ourselves to allow for duck typing and other classes
        # to return other kind of objects (see XBeeReader).
        return self

    def run(self):
        """The main action of the thread.

        Wait for data, read them and send them to the rest of the
        application for further computation.
        """
        while self._should_continue:
            try:
                gate, drone = self.read_new_value()
            except TypeError:
                # read_new_value returned None, errors already handled
                pass
            else:
                self._update_data(gate, drone)

    def stop(self):
        """Signal that the thread has to stop reading its inputs."""
        self._should_continue = False

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier,
        drone number). Subclasses must implement this method.
        """
        raise NotImplementedError(_("Subclasses must implement this method"))


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


class UDPReader(BaseReader):
    """Read data from UDP datagrams. Used when communicating via
    WiFi with the gates.
    """

    def __init__(self, port):
        """Spawn a thread that continuously read data for drones
        statuses.
        
        Parameter:
          - port: the socket port to listen on.
        """
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        iface = socket.gethostname()
        self.socket.bind((iface, port))
        # Non-blocking read so this thread will shut down with the application
        self.socket.settimeout(1)

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier,
        drone number).

        Decode an UDP datagram containing b"C:3" to the tuple ('C', 2).
        """
        try:
            msg = self.socket.recv(128) # Way too much for messages like <A:1>
        except socket.timeout:
            return
        try:
            gate, drone = msg.split(b':')
            gate = gate.decode()
            # Compensate for the drone numbering vs. its indexing
            drone = int(drone) - 1
        except (UnicodeError, ValueError) as e:
            print(_('Received unparsable message: {}').format(msg),
                    file=sys.stderr)
            print(e, file=sys.stderr)
        else:
            return gate, drone


class TCPReader(BaseReader):
    """Read data from TCP frames. Used when communicating via
    WiFi with the gates.
    """

    def __init__(self, port):
        """Spawn a thread that continuously read data for drones
        statuses.
        
        Parameter:
          - port: the socket port to listen on.
        """
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        iface = socket.gethostname()
        self.socket.bind((iface, port))
        self.socket.listen(10)
        # Non-blocking read so this thread will shut down with the application
        self.socket.settimeout(1)

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier,
        drone number).

        Decode an UDP datagram containing b"C:3" to the tuple ('C', 2).
        """
        try:
            connection = self.socket.accept()
            msg = connection.recv(128) # Way too much for messages like <A:1>
        except socket.timeout:
            return
        try:
            gate, drone = msg.split(b':')
            gate = gate.decode()
            # Compensate for the drone numbering vs. its indexing
            drone = int(drone) - 1
        except (UnicodeError, ValueError) as e:
            print(_('Received unparsable message: {}').format(msg),
                    file=sys.stderr)
            print(e, file=sys.stderr)
        else:
            return gate, drone


if XBee is None:
    class XBeeReader(BaseReader):
        """Read data from a serial port bound to an XBee.
        Dummy implementation because xbee module could not be loaded.
        """

        def __init__(self, *args, **kwargs):
            """Accepts arguments to be compatible with the "real"
            XBeeReader but prints a warning and terminate gracefully
            instead.
            """
            super().__init__()
            print(_('Can not load XBee module. No data will be received'),
                    file=sys.stderr)

        def read_new_value(self):
            """Cancel this thread to avoid burning resources."""
            self._should_continue = False

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
                print(_('Received unparsable message: {}').format(
                        response_dict['rf_data']), file=sys.stderr)
                print(e, file=sys.stderr)
            except KeyError as e:
                print(_('Received empty frame'), file=sys.stderr)
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
        """Wrapper around the xbee module to integrate our
        _BeeReaderMixin into the appropriate base class.
        """

        def __init__(self, *args, **kwargs):
            """Save parameters for future use.

            Every parameter is used to initialize a serial.Serial
            object except for the named attribute 'zigbee' which
            define the base class to use.

            Parameter:
              - zigbee: whether to use the xbee.ZigBee base class or
                the xbee.XBee one
            """
            zigbee = kwargs.pop('zigbee', False)
            base_cls = ZigBee if zigbee else XBee
            self._serial = Serial(*args, **kwargs)
            self._cls = type('XBeeReader', (_BeeReaderMixin, base_cls), {})

        def __call__(self, callback):
            """Generate the appropriate object to read data.

            Parameter:
              - callback: the function that will be called each
                time a valid data is read.
            """
            return self._cls(self._serial, callback)
