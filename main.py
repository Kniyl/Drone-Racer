from argparse import ArgumentParser
import drone_racer

parser = ArgumentParser(description='Interface graphique "Drone Racer"')
parser.add_argument('--fancy-title', dest='fancy', action='store_true',
                    help='Utilise une barre de titre un peu plus Gtk3')
parser.add_argument('--serial-port', dest='serial', metavar='FILE',
                    default=None, help='Spécifie le port série à utiliser '
                    'pour récupérer les informations provenant du XBee')
parser.add_argument('--zigbee', dest='zigbee', action='store_true',
                    help='Spécifie si le module XBee est un ZigBee')
args = parser.parse_args()
if args.serial is not None:
    reader = drone_racer.XBeeReader(
            args.serial, baudrate=115200, zigbee=args.zigbee)
else:
    reader = drone_racer.StdInReader
app = drone_racer.Application(reader, args.fancy)
app.run()
