from threading import Thread
import os, sys


class BaseReader(Thread):
    def __init__(self, console):
        super().__init__(name="reader")
        self.console = console
        self.should_continue = True

    def run(self):
        while self.should_continue:
            beacon, drone = self.read_new_value()
            self.process_value(beacon, drone)

    def read_new_value(self):
        raise NotImplementedError("Subclasses must implement this method")

    def process_value(self, beacon, drone):
        if drone < 0:
            return
        self.console.compute_data(beacon, drone)


class StdInReader(BaseReader):
    def read_new_value(self):
        raw = input('[@] ').split()
        if len(raw) != 2:
            return '?', -1
        try:
            value = (chr(int(raw[0])+65), int(raw[1]))
        except:
            value = '?', -1
        return value


class GPIOReader(BaseReader):
    pass


def test():
    from threading import Timer
    class DummyConsole:
        def compute_data(self, b, d):
            print(b, d)

    r = StdInReader(DummyConsole(),sys.stdin.fileno())

    def stop_thread():
        r.terminate()

    t = Timer(10.0, stop_thread)
    print("Starting timer and thread")
    r.start()
    t.start()
    r.join()
    print("Thread terminated, exiting")

if __name__ == "__main__":
    test()
