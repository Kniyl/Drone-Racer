import os.path
from random import shuffle
from sqlite3 import connect, DatabaseError, IntegrityError


class SQLError(Exception):
    """Exception raised by this module when a configuration
    error occurs. It may be due to database access, broken
    work-flow or compromised data integrity.
    """
    pass


class Database:
    """Abstraction layer on top of an SQLite database.
    Provide access to underlying data through methods rather than SQL queries.
    """

    def __init__(self, filename, create=False):
        """Open a database and quickly check its integrity.

        Parameter:
          - create: whether or not this database is new and should have its
            tables created
        """
        try:
            c = connect(filename)
            c.execute('PRAGMA foreign_keys = ON')
            if create:
                with c:
                    cur = c.cursor()
                    cur.execute('CREATE TABLE check_integrity '
                            '(id integer PRIMARY KEY)')
                    cur.execute('INSERT INTO check_integrity VALUES (0)')
                    cur.execute('CREATE TABLE events '
                            '(id integer PRIMARY KEY, '
                            'nom text UNIQUE NOT NULL, '
                            'nb_portes integer NOT NULL)')
                    cur.execute('CREATE TABLE pilotes '
                            '(id integer PRIMARY KEY, '
                            'nom text UNIQUE NOT NULL, '
                            'telephone text NOT NULL, '
                            'mail text NOT NULL)')
                    cur.execute('CREATE TABLE drones '
                            '(id integer PRIMARY KEY, '
                            'designation text UNIQUE NOT NULL, '
                            'category text)')
                    cur.execute('CREATE TABLE pilotes_drones_lien '
                            '(id integer PRIMARY KEY, '
                            'pilote_id integer NOT NULL, '
                            'drone_id integer NOT NULL, '
                            'FOREIGN KEY(pilote_id) REFERENCES pilotes(id), '
                            'FOREIGN KEY(drone_id) REFERENCES drones(id))')
                    cur.execute('CREATE TABLE jeux '
                            '(id integer PRIMARY KEY, '
                            'event_id integer NOT NULL, '
                            'intitule text NOT NULL, '
                            'nb_drones integer NOT NULL, '
                            'temps_max integer NOT NULL, '
                            'tours_min integer NOT NUlL, '
                            'free_fly boolean NOT NULL, '
                            'strict boolean NOT NULL, '
                            'UNIQUE(event_id, intitule) ON CONFLICT ROLLBACK, '
                            'FOREIGN KEY(event_id) REFERENCES events(id))')
                    cur.execute('CREATE TABLE portes_jeu '
                            '(id integer PRIMARY KEY, '
                            'jeu_id integer NOT NULL, '
                            'porte text NOT NULL, '
                            'type integer NOT NULL, '
                            'points integer NOT NULL, '
                            'suivant text NOT NULL, '
                            'FOREIGN KEY(jeu_id) REFERENCES jeux(id))')
                    cur.execute('CREATE TABLE courses '
                            '(id integer PRIMARY KEY, '
                            'jeu_id integer NOT NULL, '
                            'FOREIGN KEY(jeu_id) REFERENCES jeux(id))')
                    cur.execute('CREATE TABLE coureurs '
                            '(id integer PRIMARY KEY, '
                            'course_id integer NOT NULL, '
                            'pilote_id integer NOT NULL, '
                            'drone_id integer NOT NULL, '
                            'balise_id integer NOT NULL, '
                            'position integer, '
                            'points integer, '
                            'temps real, '
                            'tours integer, '
                            'best real, '
                            'termine boolean, '
                            'retard integer, '
                            'FOREIGN KEY(course_id) REFERENCES courses(id), '
                            'FOREIGN KEY(pilote_id) REFERENCES pilotes(id), '
                            'FOREIGN KEY(drone_id) REFERENCES drones(id))')
            test = c.execute('SELECT * FROM check_integrity').fetchall()
        except DatabaseError as e:
            # Warn the user if the database can not be created nor fetched
            raise SQLError(*e.args)
        else:
            # Quick integrity check, just in case the opened database has
            # nothing to do with our application
            if test != [(0,)]:
                raise SQLError('La base de donnée est corrompue. Abandon.')
        self.conn = c
        self.id = -1

    def _execute(self, query, *args):
        """Convenient wrapper to auto-commit changes.
        Also help at packing query arguments into a tuple.
        """
        with self.conn:
            cursor = self.conn.execute(query, args)
        return cursor

    def close(self):
        """Close the connection to the database."""
        self.conn.close()
        self.id = -1

    def get_events(self):
        """Return a generator of every event registered in the database."""
        query = 'SELECT nom FROM events'
        return (row[0] for row in self._execute(query))

    def load_event(self, event_name, nb_gates):
        """Bind this object to a specific event. Optionally create the event
        before if it does not exists in the database.

        Parameters:
          - event_name: name of the event to bind/create
          - nb_gates: number of tracking gates available for this event

        Return the list of identifiers that must be used on the gates for this
        event.
        """
        try:
            query = 'INSERT INTO events(nom, nb_portes) VALUES (?, ?)'
            self._execute(query, event_name, nb_gates)
        except IntegrityError:
            pass

        query = 'SELECT id,nb_portes FROM events WHERE nom=?'
        self.id, count = self._execute(query, event_name).fetchone()

        LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # Create the list ['A', 'B', ..., 'AA', 'AB', ..., 'BA', 'BB', ...]
        # as long as needed to fit the number of gates
        possibilities = [x for x in LETTERS]
        while len(possibilities) < count:
            others = ([y+x for x in possibilities] for y in LETTERS)
            for other in others:
                possibilities += other
        return possibilities[:count]

    def get_event_settings(self, event_name):
        """Return the number of tracking gate registered for a given event.

        Parameter:
          - event_name: the name of the event to query
        """
        query = 'SELECT nb_portes FROM events WHERE nom=?'
        count, = self._execute(query, event_name).fetchone()
        return count

    def register_driver(self, name, phone, email):
        """Register new contestant or update the informations of an existing
        one.

        Parameters:
          - name: the name of the contestant
          - phone: its phone number
          - email: its email address

        Return whether or not the contestant has been created (as opposed to
        updated).
        """
        try:
            query = 'INSERT INTO pilotes(nom, telephone, mail) VALUES (?,?,?)'
            self._execute(query, name, phone, email)
            created = True
        except IntegrityError:
            query = 'UPDATE pilotes SET telephone=?, mail=? WHERE nom=?'
            self._execute(query, phone, email, name)
            created = False
        return created

    def register_drones_for_driver(self, driver, *drones):
        """Register new drones if need be and associate them to a given
        contestant.

        Parameters:
          - driver: the name of the contestant to associate drones with
          - drones: a list of (drone name, drone category) pairs that belong
            to the contestant
        """
        query = 'INSERT INTO drones(designation, category) VALUES (?,?)'
        for drone, category in drones:
            try:
                self._execute(query, drone, category)
            except IntegrityError:
                pass
        query = 'SELECT id FROM pilotes WHERE nom=?'
        driver_id, = self._execute(query, driver).fetchone()
        query = 'DELETE FROM pilotes_drones_lien WHERE pilote_id=?'
        self._execute(query, driver_id)
        query = 'SELECT id FROM drones WHERE designation=?'
        up_query = 'INSERT INTO pilotes_drones_lien'\
                   '(pilote_id, drone_id) VALUES (?,?)'
        for drone, _ in drones:
            drone_id, = self._execute(query, drone).fetchone()
            self._execute(up_query, driver_id, drone_id)

    def register_game(self, name, num, time, laps, free, strict, gates):
        """Register or update a new route with a set of custom rules and
        associate it to the event bound to this object.

        Parameters:
          - name: the name of this configuration
          - num: the maximum number of drones allowed to fly at once on
          - this configuration
          - time: the maximum number of time allotted to the races on this
            configuration
          - laps: the number of laps required to clear races on this
            configuration
          - free: whether or not the drones can pass through the gates in
            the order they want to
          - strict: whether or not the time limit declares the end of a
            race (or if drivers can still finish their lap)
          - gates: array of 4-item-sequence describing what happen when
            drone goes through a given gate
                -> identification of the gate
                -> kind of the gate (as per .console.Gates)
                -> number of points granted by this gate
                -> the next gate after this one that drones must
                    reach in a non-free configuration

        Return whether or not the entry in the database has been created (as
        opposed to updated).
        """
        if self.id < 0:
            # Can't register the route if no event is bound to this object
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible de voir les jeux associés.')
        try:
            query = 'INSERT INTO jeux(event_id, intitule, nb_drones, '\
                    'temps_max, tours_min, free_fly, strict) '\
                    'VALUES (?,?,?,?,?,?,?)'
            self._execute(query, self.id, name, num, time, laps, free, strict)
            created = True
        except IntegrityError:
            query = 'UPDATE jeux SET nb_drones=?, temps_max=?, tours_min=?, '\
                    'free_fly=?, strict=? WHERE event_id=? and intitule=?'
            self._execute(query, num, time, laps, free, strict, self.id, name)
            created = False
        query = 'SELECT id FROM jeux WHERE event_id=? and intitule=?'
        game_id, = self._execute(query, self.id, name).fetchone()
        query = 'DELETE FROM portes_jeu WHERE jeu_id=?'
        self._execute(query, game_id)
        query = 'INSERT INTO portes_jeu(jeu_id, porte, type, points, suivant) '\
                'VALUES (?,?,?,?,?)'
        # Gate id, type, points, next
        for g,t,p,n in gates:
            self._execute(query, game_id, g, t, p, n)
        return created

    def register_new_race(self, game_name, contestants):
        """Create a new race associated to the event bound to this object.

        Parameters:
          - game_name: name of the route and custom set of rules used
            for this race
          - contestants: a list of (driver name, drone type) pairs that
            will attend the race
        """
        if self.id < 0:
            # Can't register the race if no event is bound to this object
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible d’enregistrer une course.')
        query = 'SELECT id FROM jeux WHERE event_id=? and intitule=?'
        game_id, = self._execute(query, self.id, game_name).fetchone()
        query = 'INSERT INTO courses(jeu_id) VALUES (?)'
        race_id = self._execute(query, game_id).lastrowid
        shuffle(contestants)
        beacon = len(contestants)
        for driver, drone in contestants:
            query = 'SELECT id FROM pilotes WHERE nom=?'
            driver_id, = self._execute(query, driver).fetchone()
            query = 'SELECT id FROM drones WHERE designation=?'
            drone_id, = self._execute(query, drone).fetchone()
            query = 'INSERT INTO coureurs(course_id, pilote_id, '\
                    'drone_id, balise_id) VALUES (?,?,?,?)'
            self._execute(query, race_id, driver_id, drone_id, beacon)
            beacon -= 1
        return race_id

    def get_drivers(self):
        """Fetch the name of all registered contestants."""
        query = 'SELECT nom FROM pilotes'
        return (row[0] for row in self._execute(query))

    def get_driver_info(self, driver):
        """Fetch personal informations on a given contestant.
        
        Parameter:
          - driver: the name of the contestant
        """
        query = 'SELECT telephone,mail FROM pilotes WHERE nom=?'
        return self._execute(query, driver).fetchone()

    def get_drones_for(self, driver):
        """Fetch the list of drones associated to a given contestant.

        Parameter:
          - driver: the name of the contestant
        """
        query = 'SELECT id FROM pilotes WHERE nom=?'
        driver_id, = self._execute(query, driver).fetchone()
        query = 'SELECT designation '\
                'FROM pilotes_drones_lien INNER JOIN drones '\
                'ON pilotes_drones_lien.drone_id=drones.id '\
                'WHERE pilotes_drones_lien.pilote_id=?'
        return (row[0] for row in self._execute(query, driver_id))

    def get_drones(self):
        """Fetch the name of all registered drones."""
        query = 'SELECT designation FROM drones'
        return (row[0] for row in self._execute(query))

    def get_categories(self):
        """Fetch the name of all registered drones categories."""
        query = 'SELECT DISTINCT category FROM drones'
        return (row[0] for row in self._execute(query))

    def get_category_for_drone(self, drone):
        """Fetch the category for a given kind of drone.

        Parameter:
          - drone: the name of the drone to look the category for
        """
        query = 'SELECT category FROM drones WHERE designation=?'
        category, = self._execute(query, drone).fetchone()
        return category or ''

    def get_game_names(self):
        """Fetch the names of all set of custom rules registered for
        the event bound to this object.
        """
        if self.id < 0:
            # Can't query the routes names if no event is bound to this object
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible de voir les jeux associés.')
        query = 'SELECT intitule FROM jeux WHERE event_id=?'
        return (row[0] for row in self._execute(query, self.id))

    def get_games_for_event(self, event):
        """Fetch the names of all set of custom rules registered for
        the specified event.
        """
        query = 'SELECT id FROM events WHERE nom=?'
        event_id, = self._execute(query, event).fetchone()
        query = 'SELECT intitule FROM jeux WHERE event_id=?'
        return (row[0] for row in self._execute(query, event_id))

    def get_game_name(self, game_id):
        """Fetch the name of the given set of custom rules."""
        query = 'SELECT intitule, event_id FROM jeux WHERE id=?'
        name, event_id = self._execute(query, game_id).fetchone()
        query = 'SELECT nom FROM events WHERE id=?'
        event, = self._execute(query, event_id).fetchone()
        return name, event

    def get_game_settings(self, game_name):
        """Fetch a specific route and set of rules from the event bound to
        this object.

        Parameter:
          - game_name: the name of the route to fetch
        """
        if self.id < 0:
            # Can't query the routes custom rules if no event
            # is bound to this object
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible de voir les jeux associés.')
        query = 'SELECT id,nb_drones,temps_max,tours_min,free_fly,strict '\
                'FROM jeux WHERE event_id=? and intitule=?'
        game_id, count, time, laps, free, strict =\
                self._execute(query, self.id, game_name).fetchone()
        query = 'SELECT porte,type,points,suivant '\
                'FROM portes_jeu WHERE jeu_id=?'
        beacons = self._execute(query, game_id).fetchall()
        return (count, time, laps, free, strict, beacons)

    def get_race_drivers(self, race_id):
        """Fetch the list of contestant for a given race.

        Parameter:
          - race_id: the identification number of the race to query from

        Return a list of 3-item-sequences:
          - identification of the beacon attached to the drone for this race
          - name of the driver of the drone
          - kind of drone used by the driver for this race
        """
        query = 'SELECT balise_id, pilote_id, drone_id FROM coureurs '\
                'WHERE course_id=?'
        race_setup = sorted(self._execute(query, race_id).fetchall())
        result = []
        for id, driver, drone in race_setup:
            query = 'SELECT nom FROM pilotes WHERE id=?'
            driver, = self._execute(query, driver).fetchone()
            query = 'SELECT designation FROM drones WHERE id=?'
            drone, = self._execute(query, drone).fetchone()
            result.append((id, driver, drone))
        return result

    def get_races_for_driver(self, driver_name):
        query = 'SELECT id FROM pilotes WHERE nom=?'
        driver, = self._execute(query, driver_name).fetchone()
        query = 'SELECT designation, category, position, points, temps, '\
                'tours, best, termine, jeu_id FROM coureurs INNER JOIN '\
                'drones ON coureurs.drone_id=drones.id INNER JOIN '\
                'courses ON coureurs.course_id=courses.id WHERE pilote_id=?'
        return self._execute(query, driver).fetchall()

    def get_races_for_game(self, game_name):
        query = 'SELECT id FROM jeux WHERE intitule=?'
        game, = self._execute(query, game_name).fetchone()
        query = 'SELECT nom, designation, category, position, points, temps, '\
                'tours, best, termine, course_id FROM coureurs INNER JOIN '\
                'drones ON coureurs.drone_id=drones.id INNER JOIN '\
                'pilotes ON coureurs.pilote_id=pilotes.id INNER JOIN '\
                'courses ON coureurs.course_id=courses.id WHERE jeu_id=?'
        return self._execute(query, game).fetchall()

    def get_races(self, game_name):
        query = 'SELECT id FROM jeux WHERE intitule=?'
        game, = self._execute(query, game_name).fetchone()
        query = 'SELECT id FROM courses WHERE jeu_id=?'
        return (row[0] for row in self._execute(query, game))

    def get_results_for_race(self, race_id):
        query = 'SELECT nom, designation, category, position, points, temps, '\
                'tours, best, termine FROM coureurs INNER JOIN drones '\
                'ON coureurs.drone_id=drones.id INNER JOIN pilotes ON '\
                'coureurs.pilote_id=pilotes.id WHERE course_id=?'
        return self._execute(query, int(race_id)).fetchall()

    def update_race(self, race_id, *drivers_status):
        """Updates the informations on a given race to create a leader-board
        when it is done.

        Parameters:
          - race_id: the identification number of the race to update
          - drivers_status: a list of mappings containing the informations
            to update from. The following keys are used from the mapping:
              - id: identification of the beacon attached to the drone
              - position: ranking of the drone for the race
              - points: points earned by the drone during the race
              - temps: amount of time needed by the drone to clear the race
              - tours: number of laps achieved at the end of the race
              - tour: best laps' time
              - finish: whether or not the drone did finish the race
              - retard: delay accumulated on the leader drone, if relevant
        """
        query = 'UPDATE coureurs SET position=?, points=?, temps=?, tours=?, '\
                'best=?, termine=?, retard=? WHERE course_id=? and balise_id=?'
        for info in drivers_status:
            self._execute(query, info['position'], info['points'],
                    info['temps'], info['tours'], info['tour'],
                    info['finish'], info['retard'], race_id, info['id'])

    def set_category_for_drone(self, drone, category):
        """Change the category associated to a given kind of drone.

        Parameters:
          - drone: the kind of drone to update
          - category: the name of the new category for the drone
        """
        query = 'UPDATE drones SET category=? WHERE designation=?'
        self._execute(query, category, drone)


def sql_create(filename):
    """Open a file to create a new database into it.

    Ensure that the filename ends with '.sqlite' and make sure it
    doesn't already exists on the filesystem before opening it.

    Return the database wrapper object around this file.
    """
    if os.path.splitext(filename)[-1] != '.sqlite':
        filename += '.sqlite'
    if os.path.isfile(filename):
        raise SQLError(
                'Une base de donnée ne peut pas être créée '
                'car le fichier existe déjà')
    return Database(filename, True)

def sql_open(filename):
    """Open a file to manage the database in it.

    Ensure that the filename exists on the filesystem before opening it.

    Return the database wrapper object around this file.
    """
    if not os.path.isfile(filename):
        raise SQLError(
                'La base de donnée ne peut pas être ouverte '
                'car le fichier n’existe pas')
    return Database(filename)
