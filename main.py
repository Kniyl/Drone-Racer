from argparse import ArgumentParser
import drone_racer

parser = ArgumentParser(description='Interface graphique "Drone Racer"')
parser.add_argument('--fancy-title', dest='fancy', action='store_true',
                    help='Utilise une barre de titre un peu plus Gtk3')
args = parser.parse_args()
app = drone_racer.Application(args.fancy)
app.run()
