from threading import Timer
from enum import Enum
import rest


class ConsoleError(Exception):
    """Exception levée lors d’une mauvaise configuration de course
    ou d’une erreur lors de son déroulement.
    """
    pass


class Console:
    def __init__(self, timer, update):
        # TODO synchronize compute and edit~?
        self.beacons = None
        self.scores = None
        self.extra_data = None
        self.rules = None
        self.timer = timer
        self.update = update

    def setup_race(self, nb_drones, rules):
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
        self.rules = rules
        self.beacons = rules.beacons.keys()

    def cancel_race(self):
        if self.rules is None:
            raise ConsoleError(
                    'Aucune course n’a été configurée. '
                    'Impossible d’annuler.')
        for drone in self.scores:
            drone['position'] = None
            drone['points'] = None
            drone['temps'] = None
            drone['tours'] = None
            drone['finish'] = False
            drone['retard'] = None
        if self.extra_data and self.rules.timeout:
            for data in self.extra_data:
                data['timer'].cancel()
        self.rules = None
        self.extra_data = None
        rest.cancel()

    def start_race(self):
        if self.extra_data is not None:
            raise ConsoleError(
                    'Une course est déjà en cours. '
                    'Attendez sa fin ou forcez son arrêt.')
        if self.rules is None:
            raise ConsoleError(
                    'Impossible de démarrer : '
                    'aucune course configurée')
        start = self.rules.common_start
        t_out = self.rules.timeout
        self.extra_data = [{
            'offset': 0 if start else None,
            'time_laps': 0,
            'timer': Timer(t_out, self.check_laps, (id,)) if t_out else None,
        } for id in range(len(self.scores))]
        if t_out and start:
            for data in self.extra_data:
                data['timer'].start()

    def stop_race(self):
        if self.extra_data is None:
            raise ConsoleError('Il n’y a pas de course démarrée.')
        rest.finish()
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

    def check_laps(self, drone):
        drone = self.scores[drone]
        # On ne tient pas compte des drones qui ont déjà fini
        if drone['finish'] is not None:
            return
        pos = drone['position']
        # Try/except nécessaire tant que la position n’est pas bien calculée
        try:
            previous, = filter(lambda d: d['position'] == pos-1, self.scores)
        except ValueError:
            pass
        else:
            # FIXME : meilleure vérification de qui est à la traine
            if previous['tours'] == drone['tours']:
                drone['finish'] = True
                rest.update(drone)
                self.update(drone)

    def compute_data(self, beacon, drone):
        if self.extra_data is None:
            return
        if not (beacon in self.beacons and 0 <= drone < len(self.scores)):
            return
        time = self.timer()
        pending = self.rules.timed_out(time)
        data = self.extra_data[drone]
        time -= data['offset'] or 0
        score, pos, delay, turn, on_going, start =\
                self.rules.compute_score(beacon, drone, time)
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
        # FIXME : quelque chose ne va pas dans le calcul du retard
        drone['points'] += score
        drone['porte'] = beacon
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
        drone = self.scores[drone]
        drone['points'] += amount
        rest.update(drone)
        self.update(drone)

    def kill_drone(self, drone):
        drone = self.scores[drone]
        drone['finish'] = False
        rest.update(drone)
        self.update(drone)


class Beacons(Enum):
    """Différents types de portes"""
    TIME = 0
    TIME_START = 1
    TIME_END = 2
    TIME_MASTER = 3
    POINTS = 4
    @property
    def description(self):
        return [
            'Porte de temps',
            'Ligne de départ',
            'Ligne d’arrivée',
            'Ligne de départ et d’arrivée',
            'Porte de points',
        ][self.value]
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
    """Règles définissant un parcours :
     - définit un parcours valide ;
     - calcule les points reçus au passage d’une porte.
    """

    def __init__(self, timeout, nb_laps, beacons):
        """Constructeur. Vérifie la validité du parcours défini dans
        ```beacons```.

        Paramètres:
         - timeout
            le temps de course après lequel les points ne comptent plus ;
         - nb_laps
            le nombre de tours à réaliser avant de terminer la course ;
         - beacons
            liste de 4-uplets définissant un parcours:
            (nom_porte, type, nb_points, nom_porte_suivante).
        """
        # Timeout est un temps en secondes mais le timer va s’incrémenter
        # tous les dizièmes de secondes pour gérér des entiers et éviter
        # de se payer des erreurs d’arrondi.
        self.timeout = timeout * 10 or None
        self.nb_laps = nb_laps or None
        # Vérifications de la validité du parcours.
        beacon_types = [v[1] for v in beacons]
        # Si une porte de départ est définie, les drones ont un temps découplé
        # du timer principal. On compte donc le nombre de portes de départ.
        self.common_start = len(b for b in beacon_types if Beacons(b).is_start)
        if self.common_start > 1:
            raise ConsoleError('Trop de portes de départ')
        self.common_start = not self.common_start
        # On vérifie qu’une porte d’arrivée est définie.
        if len(b for b in beacon_types if Beacons(b).is_end) != 1:
            raise ConsoleError('Une (et une seule) ligne d’arrivée '
                               'doit être définie')
        # On vérifie l’ordre du parcours.
        self.beacons = {v[0]: {
                'type': v[1],
                'pts': v[2],
                'next': v[3],
                'times': {} if (Beacons(v[1]).is_end or
                    self.common_start) else None,
            } for v in beacons}
        try:
            for b,v in self.beacons.items():
                self.beacons[v['next']]['previous'] = b
        except KeyError:
            raise ConsoleError(
                    'La porte suivant la porte "{0}" '
                    'a été définie à "{1}" mais la porte "{1}" '
                    'n’existe pas'.format(b, v['next']))

    def get_setup(self):
        """Retourne la définition du parcours dans un format json-ready."""
        return {
            'temps': self.timeout,
            'tours': self.nb_laps,
            'portes': sorted(self.beacons.keys()),
        }

    def compute_score(self, beacon, drone, time):
        """Calcule les points reçus par un drone au passage d’une porte.

        Paramètres:
         - beacon
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
        beacon = self.beacons[beacon]
        type, pts, times = beacon['type'], beacon['pts'], beacon['times']
        # Calcul des points
        start = Beacons(type).is_start and not self.common_start
        end = Beacons(type).is_end
        remaining = self.timeout - time if self.timeout is not None else 0
        running = remaining >= 0
        pts = Beacons(type).is_points and pts or remaining*pts if running else 0
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
        """Indique si un temps est au dela du temps limite.
        
        Paramètre:
         - time
            le temps à tester.
            
        Retourne un booléen.
        """
        return self.timeout is not None and time > self.timeout

    def race_done(self, lap):
        """Indique si ce tour marque la fin de la course pour un drone.

        Paramètre:
         - lap
            le tour à tester.

        Retourne un booléen.
        """
        return self.nb_laps is not None and lap >= self.nb_laps


class FreeForAll(Rules):
    pass
