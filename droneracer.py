"""Drone Racer is a project primarily developed for the DroneFest
organized as part of the FabLab Festival 2015. Its aim is to provide
an all-in-one interface for races organizers to:

  - create different events for drones competition;
  - register contestants and their associated drones;
  - classify drones into categories;
  - create several routes with their own set of rules for each event;
  - setup and monitor races on a designated route;
  - gather statistics on races for drivers, event or kind of route.

To reduce the overhead of having extraneous services for database
access, Drone Racer makes use of the python's built-in sqlite module.
It uses it to store informations on the contestants, the drones, the
different type of routes and the races leaderboards.

Additionally, setup, updates & leaderboard for each race can be sent
to a RESTful API for the audience.
"""


import os

from argparse import ArgumentParser
from drone_racer.i18n import translations
import drone_racer


_, _N = translations('cli')
XBEE_NAMES = 'xbee', 'bee', 'serial'
UDP_NAMES = 'udp', 'wifi'


parser = ArgumentParser(description=_('"Drone Racer"\'s Graphical User Interface'))
parser.add_argument(
        '--fancy-title', dest='fancy', action='store_true',
        help=_('Use a fancier (Gtk3 like) titlebar for the GUI'))
subparsers = parser.add_subparsers(
        title='communication', dest='reader', description=_('List off all '
        'communication channels to get data from the gates. If none is '
        'selected, data will be read from stdin.'), metavar='DATA_LINK',
        help=_('More options are available per channel'))

name, *aliases = XBEE_NAMES
bee_parser = subparsers.add_parser(
        name, aliases=aliases, help=_('Communication through XBee frames'))
bee_parser.add_argument(
        'device', metavar='FILE', default=None,
        help=_('Serial file mapped to the XBee pins'))
bee_parser.add_argument(
        '--zigbee', dest='zigbee', action='store_true',
        help=_('Switch indicating wether it is an XBee or a ZigBee'))
bee_parser.add_argument(
        '--baudrate', dest='baudrate', metavar='BPS', type=int, default=9600,
        help=_('Serial port communication speed'))

name, *aliases = UDP_NAMES
udp_parser = subparsers.add_parser(
        name, aliases=aliases, help=_('Communication through UDP datagrams'))
udp_parser.add_argument(
        '--port', dest='port', metavar='NUM', type=int, default=4387,
        help=_('Socket port to listen on'))

# Choose the appropriate reader
args = parser.parse_args()
if args.reader in XBEE_NAMES:
    reader = drone_racer.XBeeReader(
            args.serial, args.baudrate, zigbee=args.zigbee)
elif args.reader in UDP_NAMES:
    reader = drone_racer.UDPReader(args.port)
else:
    reader = drone_racer.StdInReader()

# Be sure to be at the right place for relative path of images in Gtk
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Launch the GUI (which will, in turn, start the reader)
app = drone_racer.Application(reader, args.fancy)
app.run()
