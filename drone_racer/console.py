from threading import Timer
from enum import Enum

from . import rest


class ConsoleError(Exception):
    """Exception raised if a race is wrongly configured or if a problem
    occurs during a race.
    """
    pass


class Console:
    """Manage the various informations influencing the progress of a race."""

    def __init__(self, timer, update):
        """Initiate the race manager for the lifetime of the application.

        Parameters:
          - timer: function to call when a race is started to get the time
            elapsed since the beginning of said race
          - update: function to call when informations about a drone has changed
        """
        # TODO lock to synchronize compute and edit~?
        self.gates = None
        self.scores = None
        self.extra_data = None
        self.rules = None
        self.timer = timer
        self.update = update

    def setup_race(self, nb_drones, rules):
        """Initialize a new race.

        Parameters:
          - nb_drones: the amount of drones attending the race
          - rules: the Rules object owning the rules of this race
        """
        # Check that no other race is currently started
        if self.extra_data is not None:
            raise ConsoleError(
                    'Une course est déjà en cours. '
                    'Attendez sa fin ou forcez son arrêt.')
        self.scores = [{
            'id': id+1,
            'position': 1,
            'points': 0,
            'temps': 0.0,
            'retard': 0.0,
            'tour': None,
            'finish': None,
            'porte': None,
            'tours': 0,
        } for id in range(nb_drones)]
        # Faster lookup to decide whether or not to compute
        # the signal from a given gate
        self.gates = rules.gates.keys()
        self.rules = rules

    def cancel_race(self):
        """Cancel the last race configured. Does not matter if it was
        started or not.
        """
        # Check that a race has already been configured
        if self.rules is None:
            raise ConsoleError(
                    'Aucune course n’a été configurée. '
                    'Impossible d’annuler.')
        # Every drone get the same meaningless informations
        for drone in self.scores:
            drone['position'] = None
            drone['points'] = None
            drone['temps'] = None
            drone['tours'] = None
            drone['finish'] = False
            drone['retard'] = None
        # Cancel each drone's timer if there was a time limit
        if self.extra_data and self.rules.timeout:
            for data in self.extra_data:
                data['timer'].cancel()
        self.rules = None
        self.extra_data = None
        rest.cancel()

    def start_race(self):
        """Start monitoring events for the last configured race."""
        # Check that there is not a race already started
        if self.extra_data is not None:
            raise ConsoleError(
                    'Une course est déjà en cours. '
                    'Attendez sa fin ou forcez son arrêt.')
        # Check that a race has already been configured
        if self.rules is None:
            raise ConsoleError(
                    'Impossible de démarrer : '
                    'aucune course configurée')
        start = self.rules.common_start
        t_out = self.rules.timeout
        self.extra_data = [{
            'offset': 0 if start else None,
            'time_laps': 0,
            'timer': Timer(t_out, self._check_laps, (id,)) if t_out else None,
        } for id in range(len(self.scores))]
        # Start every drone's timer right now if there is no starting mark
        if t_out and start:
            for data in self.extra_data:
                data['timer'].start()

    def stop_race(self):
        """Halt the current race and stop monitoring for events."""
        # Check that there is a race already started
        if self.extra_data is None:
            raise ConsoleError('Il n’y a pas de course démarrée.')
        rest.finish()
        # Update status for drones that don't already cleared the race
        time = self.timer()
        for drone, extra in zip(self.scores, self.extra_data):
            if self.rules.timeout:
                extra['timer'].cancel()
            if drone['finish'] is None:
                offset = extra['offset'] or 0
                drone['finish'] = not self.rules.timed_out(time - offset)
                self.update(drone)
        self.rules = None
        self.extra_data = None

    def _check_laps(self, drone):
        """Monitoring function that get call for each drone at the end of its
        timer.

        Check if a drone has a remaining lap to clear and update its status
        accordingly.
        """
        drone = self.scores[drone]
        # Nothing to do if the drone already cleared the race
        if drone['finish'] is not None:
            return
        pos = drone['position']
        # FIXME the algorithm is broken and does not account for strict timeouts
        try:
            previous, = filter(lambda d: d['position'] == pos-1, self.scores)
        except ValueError:
            pass
        else:
            if previous['tours'] == drone['tours']:
                drone['finish'] = True
                rest.update(drone)
                self.update(drone)

    def compute_data(self, gate, drone):
        """React to events on the race as sent by the reader thread and
        update drone statuses accordingly.
        """
        # Does not process anything when no race is started
        if self.extra_data is None:
            return
        # Does not process data for a gate that is not activated for this race
        if not (gate in self.gates and 0 <= drone < len(self.scores)):
            return
        time = self.timer()
        time -= data['offset'] or 0
        data = self.extra_data[drone]
        # FIXME something, somewhere, seems wrong
        score, pos, delay, turn, on_going, start =\
                self.rules.compute_score(gate, drone, time)
        drone = self.scores[drone]
        if start and data['offset'] is None:
            data['offset'] = time
            time = 0
            drone['tours'] -= int(turn)
            timer = data['timer']
            if timer:
                timer.start()
        else:
            drone['temps'] = (time - data['time_laps']) / 10
        drone['points'] += score
        drone['porte'] = gate
        if turn:
            data['time_laps'] = time
            drone['tours'] += 1
            drone['tour'] = drone['temps']
            drone['temps'] = 0.0
            drone['finish'] = True if (not on_going or
                    self.rules.race_done(drone['tours'])) else None
        if pos > 0:
            if pos != drone['position']:
                drone['retard'] = delay if pos > 1 else 0.0
                delay = 0.0 if pos> 1 else delay
                for d in filter(lambda x: x['position'] >= pos, self.scores):
                    d['position'] += 1
                    d['retard'] += delay
                    rest.update(d)
                    self.update(d)
                drone['position'] = pos
            else:
                drone['retard'] = delay
        rest.update(drone)
        self.update(drone)
        if not [True for d in self.scores if d['finish'] is None]:
            self.stop_race()

    def edit_score(self, drone, amount):
        """Manually modify the score associated to a drone.
        
        Parameters:
          - drone: identification number of the beacon attached to
            the drone to modify
          - amount: the quantity of points to add to this drone
        """
        # Account for line 46
        drone = self.scores[drone-1]
        drone['points'] += amount
        rest.update(drone)
        self.update(drone)

    def kill_drone(self, drone):
        """Declare that a drone is no good anymore and won't be able to
        finish the race.

        Parameter:
          - drone: identification number of the beacon attached to the drone
        """
        # Account for line 46
        drone = self.scores[drone-1]
        drone['finish'] = False
        rest.update(drone)
        self.update(drone)


class Gates(Enum):
    """Officially supported types of gates"""
    TIME = 0
    TIME_START = 1
    TIME_END = 2
    TIME_MASTER = 3
    POINTS = 4
    @property
    def description(self):
        return (
            'Porte de temps',
            'Ligne de départ',
            'Ligne d’arrivée',
            'Ligne de départ et d’arrivée',
            'Porte de points',
        )[self.value]
    @property
    def is_time(self):
        return self.value < 4
    @property
    def is_points(self):
        return self.value > 3
    @property
    def is_start(self):
        return bool(self.value & 1)
    @property
    def is_end(self):
        return bool(self.value & 2)


class Rules:
    """Route and custom set of rules that defines a race. Also help to
    compute data when a drone goes through a gate."""

    def __init__(self, timeout, strict, nb_laps, gates):
        """Create a route and check its validity.

        Parameters:
          - timeout: allotted time to clear the race
          - strict: whether the race should stop immediately after the timeout
            or if late drones have a chance of finishing their lap
          - nb_laps: number of laps required to clear the race
          - gates: list of 4-items-sequences defining the active gates for
            the race:
              - identification letter(s) for the gate
              - kind of gate as defined by the Gates enum
              - number of points associated to this gate
              - identification letter(s) for the next gate after this one
        """
        if strict and not timeout:
            raise ConsoleError(
                    'Un temps de course doit être défini '
                    'lorsque l’option stricte est activée')
        # Account for the fact that the timer counts in tenths of seconds
        # and the timeout value is given in seconds
        self.timeout = timeout * 10 or None
        self.strict = strict
        self.nb_laps = nb_laps or None
        # Check the route validity
        gates_type = [v[1] for v in gates]
        # Check that there is at most one starting mark
        self.common_start = len(b for b in gates_type if Gates(b).is_start)
        if self.common_start > 1:
            raise ConsoleError('Trop de portes de départ')
        # Whether or not all drones share the same timer
        self.common_start = not self.common_start
        # Check that there is one and only one finish line
        if len(b for b in gates_type if Gates(b).is_end) != 1:
            raise ConsoleError('Une (et une seule) ligne d’arrivée '
                               'doit être définie')
        # Check for the route ordering
        self.gates = {v[0]: {
                'type': v[1],
                'pts': v[2],
                'next': v[3],
                'times': {} if (Gates(v[1]).is_end or
                    self.common_start) else None,
            } for v in gates}
        try:
            for b,v in self.gates.items():
                self.gates[v['next']]['previous'] = b
        except KeyError:
            raise ConsoleError(
                    'La porte suivant la porte "{0}" '
                    'a été définie à "{1}" mais la porte "{1}" '
                    'n’existe pas'.format(b, v['next']))

    def get_setup(self):
        """Return this route and rules definition in a JSON-ready
        representation.
        """
        return {
            'temps': self.timeout,
            'tours': self.nb_laps,
            'portes': sorted(self.gates.keys()),
        }

    def compute_score(self, gate, drone, time):
        """Calcule les points reçus par un drone au passage d’une porte.

        Paramètres:
         - gate
            nom de la porte qui vient d’être passée par le drone ;
         - drone
            numéro du drone qui vient de franchir la porte ;
         - time
            temps mis par le drone pour franchir la porte depuis son départ.

        Retourne un 6-uplet:
         - nombre de points obtenus au franchissement de la porte ;
         - position du drone pendant la course ;
         - retard accumulé sur (avance du) le premier drone ;
         - indication de tour complété ;
         - indication de temps limite dépassé ;
         - indication si le drone passe par la porte de départ.
        """
        # FIXME everything is broken here
        gate = self.gates[gate]
        type, pts, times = gate['type'], gate['pts'], gate['times']
        # Calcul des points
        start = Gates(type).is_start and not self.common_start
        end = Gates(type).is_end
        remaining = self.timeout - time if self.timeout is not None else 0
        running = remaining >= 0
        pts = Gates(type).is_points and pts or remaining*pts if running else 0
        # Calcul de position
        pos, delay = -1, 0
        if times is not None:
            drone_times = times.setdefault(drone, [])
            drone_times.append(time)
            laps = len(drone_times) - 1
            everyones_time = sorted(
                    [t[laps] for t in times.values() if len(t) > laps])
            pos = everyones_time.index(time)
            if pos:
                delay = everyones_time[pos] - everyones_time[0]
            elif len(everyones_time) > 1:
                delay = everyones_time[1] - everyones_time[0]
        return pts, pos+1, delay/10, end, running, start

    def timed_out(self, time):
        """Return whether or not the race has stopped at a given moment
        of time.

        Parameter:
          - time: the moment in time to check for
        """
        return self.timeout is not None and time > self.timeout

    def race_done(self, lap):
        """Return whether or not the race has stopped at a given number
        of laps.

        Parameter:
          - lap: the number of laps to check for
        """
        return self.nb_laps is not None and lap >= self.nb_laps


class FreeForAll(Rules):
    """Custom set of rules that does not enforce a specific ordering
    of the gates during the race.
    """
    pass
