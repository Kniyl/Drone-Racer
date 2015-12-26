import os

from argparse import ArgumentParser
import drone_racer


os.chdir(os.path.dirname(os.path.abspath(__file__)))

parser = ArgumentParser(description='Interface graphique "Drone Racer"')

# GUI args
parser.add_argument('--fancy-title', dest='fancy', action='store_true',
                    help='Utilise une barre de titre un peu plus Gtk3')

# XBee args
parser.add_argument('--serial-port', dest='serial', metavar='FILE',
                    default=None, help='Spécifie le port série à utiliser '
                    'pour récupérer les informations provenant du XBee')
parser.add_argument('--zigbee', dest='zigbee', action='store_true',
                    help='Spécifie si le module XBee est un ZigBee')
parser.add_argument('--baudrate', dest='baudrate', metavar='BPS',
                    type=int, default=9600, help='Débit du port série '
                    'utilisé pour la connexion avec le module XBee')

# UDP args
parser.add_argument('--interface', dest='iface', metavar='NAME',
                    default=None, help='Spécifie l’interface sur laquelle '
                    'écouter les messages UDP')
parser.add_argument('--port', dest='port', metavar='NUM', type=int,
                    default=4387, help='Port à utiliser pour l’écoute UDP')

args = parser.parse_args()
if args.serial is not None:
    reader = drone_racer.XBeeReader(
            args.serial, args.baudrate, zigbee=args.zigbee)
elif args.iface is not None:
    reader = drone_racer.UDPReader(args.iface, args.port)
else:
    reader = drone_racer.StdInReader

app = drone_racer.Application(reader, args.fancy)
app.run()
