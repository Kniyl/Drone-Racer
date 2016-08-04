from serial import Serial
from drone_racer.threads import XBeeReader
from time import sleep
from datetime import datetime

class XBeeManager:
    def __init__(self, iface, baud):
        self.serial = Serial(iface, baud)
        while self.serial.inWaiting():
            self.serial.read()

    def __enter__(self):
        sleep(2)
        self.write('+++', False)
        return self

    def __exit__(self, eType, eValue, traceback):
        self.write('ATCN')
        sleep(1)

    def write(self, message, endline=True):
        msg = message.encode()
        if endline:
            msg += b'\r'
        self.serial.write(msg)
        char = b''
        print('[', datetime.now(), '] ', end='')
        while char != b'\r':
            char = self.serial.read()
            print(char.decode(), end='')
        print('')

def writeConsole(iface):
    iface.write("ATRE")
    iface.write("ATCH1A")
    iface.write("ATID6666")
    iface.write("ATDH0")
    iface.write("ATDL0")
    iface.write("ATMY6600")
    iface.write("ATMM1")
    iface.write("ATCE1")
    iface.write("ATNIConsole")
    #iface.write("ATBD6")
    iface.write("ATAP1")
    iface.write("ATWR")

def resetData(iface):
    iface.write("ATRE")
    iface.write("ATWR")

def writeData(iface):
    iface.write("ATRE")
    iface.write("ATCH1A")
    iface.write("ATID6666")
    iface.write("ATDH0")
    iface.write("ATDL0")
    iface.write("ATMYFFFF")
    iface.write("ATMM1")
    iface.write("ATCE0")
    iface.write("ATNIPorte")
    iface.write("ATBD6")
    iface.write("ATAP1")
    iface.write("ATWR")

def readData(iface):
    iface.write("ATCH")
    iface.write("ATID")
    iface.write("ATDH")
    iface.write("ATDL")
    iface.write("ATMY")
    iface.write("ATMM")
    iface.write("ATCE")
    iface.write("ATNI")
    iface.write("ATBD")
    iface.write("ATAP")

def main(args=None):
    if not args or not args.serial:
        return
    if args.listen:
        reader = XBeeReader(args.serial, args.baud or 9600)
        thread = reader(lambda x,y: print('[', datetime.now(), '] Porte :', x, '\t\tDrone :', y+1))
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            thread.stop()
    else:
        func = readData if args.baud else (writeConsole if args.console else writeData)
        if args.reset:
            func = resetData
        with XBeeManager(args.serial, args.baud or 9600) as iface:
            func(iface)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Flasher un XBee vite fait')
    parser.add_argument('--serial-port', dest='serial', metavar='FILE',
                        default=None, help='Spécifie le port série à utiliser '
                        'pour récupérer les informations provenant du XBee')
    parser.add_argument('--baudrate', dest='baud', metavar='BPS',
                        type=int, help='Débit du port série '
                        'utilisé pour la connexion avec le module XBee')
    parser.add_argument('--reset', dest='reset', action='store_true',
                        help='Reset le XBee en config usine')
    parser.add_argument('--console', dest='console', action='store_true',
                        help='Écrit la config console sur le XBee')
    parser.add_argument('--listen', dest='listen', action='store_true',
                        help='Utilise le XBee pour écouter les messages reçu')
    args = parser.parse_args()
    main(args)

