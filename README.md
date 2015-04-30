Drone Racer
===========

Drone Racer is a project primarily developed for the DroneFest organized as part
of the [FabLab Festival 2015](http://fablabfestival.fr/). Its aim is to provide
an all-in-one interface for races organizers to:
 * create different events for drones competition;
 * register contestants and their associated drones;
 * classify drones into categories;
 * create several routes with their own set of rules for each event;
 * setup and monitor races on a designated route;
 * gather statistics on races for drivers, event or kind of route.

This project is targeted for raspberry pi where input data for drone along the
race will be provided on the GPIO port. Data readers are however extensible to
provide additional support.

To reduce the overhead of having extraneous services for database access, Drone
Racer makes use of the python's built-in sqlite module. It uses it to store
informations on the contestants, the drones, the different type of routes and
the races leaderboards.

Additionally, setup, updates & leaderboard for each race can be sent to a REST
API for the audience.


Dependencies
============

GUI
---

 * [Python GObject Introspection](https://wiki.gnome.org/Projects/PyGObject)
 * [Font Awesome](http://fortawesome.github.io/Font-Awesome/)
 * Some images under resources/img that are not provided under version control.

Readers (optional)
------------------

 * [pySerial](http://pyserial.sourceforge.net/)
 * [python-xbee](https://pypi.python.org/pypi/XBee)


A Note on Data
==============

The software ships with 2 different data readers. Each reader should server as
an interface between signals sent from gates and the internal representation
needed by the software.

Provided readers are an StdInReader that converts input from the command line
and an XBeeReader that expects data coming with the ZigBee protocol on a
serial port.

It is easy to provide any other kind of reader, given the following
constraints:
 * it is recommended that the reader is a subclass of threading.Thread;
 * as such, it has to provide a start() method;
 * a stop() method should be implemented for cleanup purposes;
 * the constructor must accept a callback method as unique parameter.

The callback method is a two parameters function that must be called each time
a drone passes by a gate. The first parameter is the gate identification letter
(or letters if there are more than 26 gates) and the second parameters is the
0-based drone identification number.

Other than that, readers can be implemented freely and expect any kind of input
data.
