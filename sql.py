from sqlite3 import connect, DatabaseError, IntegrityError
from random import shuffle
import os.path


class SQLError(Exception):
    pass


class Database:
    def __init__(self, filename, create=False):
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
                            'temps integer, '
                            'tours integer, '
                            'termine boolean, '
                            'retard integer, '
                            'FOREIGN KEY(course_id) REFERENCES courses(id), '
                            'FOREIGN KEY(pilote_id) REFERENCES pilotes(id), '
                            'FOREIGN KEY(drone_id) REFERENCES drones(id))')
            test = c.execute('SELECT * FROM check_integrity').fetchall()
        except DatabaseError as e:
            raise SQLError(*e.args)
        else:
            if test != [(0,)]:
                raise SQLError('La base de donnée est corrompue. Abandon.')
            self.conn = c
            self.id = -1

    def _execute(self, query, *args):
        with self.conn:
            cursor = self.conn.execute(query, args)
        return cursor

    def close(self):
        self.conn.close()
        self.id = -1

    def get_events(self):
        query = 'SELECT nom FROM events'
        return (row[0] for row in self._execute(query))

    def load_event(self, event_name, nb_beacons):
        try:
            query = 'INSERT INTO events(nom, nb_portes) VALUES (?, ?)'
            self._execute(query, event_name, nb_beacons)
        except IntegrityError:
            pass

        query = 'SELECT id,nb_portes FROM events WHERE nom=?'
        self.id, count = self._execute(query, event_name).fetchone()

        LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        possibilities = [x for x in LETTERS]
        while len(possibilities) < count:
            others = ([y+x for x in possibilities] for y in LETTERS)
            for other in others:
                possibilities += other
        return possibilities[:count]

    def get_event_settings(self, event_name):
        query = 'SELECT nb_portes FROM events WHERE nom=?'
        count, = self._execute(query, event_name).fetchone()
        return count

    def register_driver(self, name, phone, mail):
        try:
            query = 'INSERT INTO pilotes(nom, telephone, mail) VALUES (?,?,?)'
            self._execute(query, name, phone, mail)
            created = True
        except IntegrityError:
            query = 'UPDATE pilotes SET telephone=?, mail=? WHERE nom=?'
            self._execute(query, phone, mail, name)
            created = False
        return created

    def register_drones_for_driver(self, driver, *drones):
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

    def register_game(self, name, num, time, laps, free, strict, beacons):
        if self.id < 0:
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible de voir les jeux associés.')
        try:
            query = 'INSERT INTO jeux(event_id, intitule, nb_drones, '\
                    'temps_max, tours_min, free_fly, strict) '
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
        for b,t,p,n in beacons:
            self._execute(query, game_id, b, t, p, n)
        return created

    def register_new_race(self, game_name, contestants):
        if self.id < 0:
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
        query = 'SELECT nom FROM pilotes'
        return (row[0] for row in self._execute(query))

    def get_driver_info(self, driver):
        query = 'SELECT telephone,mail FROM pilotes WHERE nom=?'
        return self._execute(query, driver).fetchone()

    def get_drones_for(self, driver_name):
        query = 'SELECT id FROM pilotes WHERE nom=?'
        driver_id, = self._execute(query, driver_name).fetchone()
        query = 'SELECT designation '\
                'FROM pilotes_drones_lien INNER JOIN drones '\
                'ON pilotes_drones_lien.drone_id=drones.id '\
                'WHERE pilotes_drones_lien.pilote_id=?'
        return (row[0] for row in self._execute(query, driver_id))

    def get_drones(self):
        query = 'SELECT designation FROM drones'
        return (row[0] for row in self._execute(query))

    def get_categories(self):
        query = 'SELECT DISTINCT category FROM drones'
        return (row[0] for row in self._execute(query))

    def get_category_for_drone(self, drone):
        query = 'SELECT category FROM drones WHERE designation=?'
        category, = self._execute(query, drone).fetchone()
        return category or ''

    def get_game_names(self):
        if self.id < 0:
            raise SQLError(
                'Vous n’avez pas chargé d’évènement. '
                'Impossible de voir les jeux associés.')
        query = 'SELECT intitule FROM jeux WHERE event_id=?'
        return (row[0] for row in self._execute(query, self.id))

    def get_game_settings(self, game_name):
        if self.id < 0:
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

    def update_race(self, race_id, *drivers_status):
        query = 'UPDATE coureurs SET position=?, points=?, temps=?, tours=?, '\
                'termine=?, retard=? WHERE course_id=? and balise_id=?'
        for info in drivers_status:
            self._execute(query, info['position'], info['points'],
                    info['temps'], info['tours'], info['finish'],
                    info['retard'], race_id, info['id'])

    def set_category_for_drone(self, drone, category):
        query = 'UPDATE drones SET category=? WHERE designation=?'
        self._execute(query, category, drone)


def sql_create(filename):
    if os.path.splitext(filename)[-1] != '.sqlite':
        filename += '.sqlite'
    if os.path.isfile(filename):
        raise SQLError(
                'Une base de donnée ne peut pas être créée '
                'car le fichier existe déjà')
    return Database(filename, True)

def sql_open(filename):
    if not os.path.isfile(filename):
        raise SQLError(
                'La base de donnée ne peut pas être ouverte '
                'car le fichier n’existe pas')
    return Database(filename)
