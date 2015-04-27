import os
import sys
from threading import Thread
try:
    from RPi import GPIO
except ImportError:
    GPIO = None


class BaseReader(Thread):
    """Base class for custom data readers."""

    def __init__(self, update_function):
        """Spawn a thread that continuously read data for drones statuses.
        
        Parameter:
            update_function: the function that will be called each time a
            valid data is read.
        """
        super().__init__(name="reader")
        self.update_data = update_function
        self.should_continue = True
        self.start()

    def run(self):
        """The main action of the thread.

        Wait for data, read them and send them to the rest of the application
        for further computation.
        """
        while self.should_continue:
            gate, drone = self.read_new_value()
            self.process_value(gate, drone)

    def stop(self):
        """Signal that the thread has to stop reading its inputs."""
        self.should_continue = False

    def read_new_value(self):
        """Read input data and return them as a tuple (gate identifier, drone
        number). Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def process_value(self, gate, drone):
        """Send input data to the rest of the application.

        Parameters:
            gate: the gate identification letter(s)
            drone: the drone identification number (1-based)
        """
        if drone < 0:
            return
        self.update_data(gate, drone)


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


if GPIO is None:
    from time import sleep

    class GPIOReader(BaseReader):
        """Read data from GPIO.
        Dummy implementation on non-raspberrypi systems."""

        def read_new_value(self):
            while self.should_continue:
                sleep(1)
            return '?', -1
else:
    class GPIOReader(BaseReader):
        """Read data from GPIO."""

        def read_new_value(self):
            # TODO: actually read data
            return '?', -1
