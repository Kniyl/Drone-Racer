Drone Racer
===========

Drone Racer is a project primarily developed for the DroneFest organized as part
of the [FabLab Festival 2015](http://fablabfestival.fr/). Its aim is to provide
an all-in-one interface for races organizers to:
 * create different events for drones competition;
 * register contestants and their associated drones;
 * classify drones into categories;
 * create several routes with their own set of rules for each event;
 * setup and monitor races on a designated route.

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

 * [Python GObject Introspection](https://wiki.gnome.org/Projects/PyGObject)
 * [Font Awesome](http://fortawesome.github.io/Font-Awesome/)
 * Some images under resources/img that are not provided under version control.


A Note on Data
==============

Data are read on the GPIO port and comes from gates or stakes. Each gate, when
a drone passes by send a signal containing the gate identification letter (or
letters when there is more than 26 gates) and the drone beacon number.

Data readers can expect other kind of informations but they are expected to
provide a (or several) letter(s) and a number to the rest of the application.
The route planner and the race setup are built on the same assumptions.

