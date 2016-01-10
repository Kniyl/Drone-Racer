from requests import request, RequestException
from requests.auth import HTTPBasicAuth
from local_server import *
from threading import Thread
from sys import stderr
import traceback
try:
    import simplejson as json
except ImportError:
    import json

from .i18n import translations


_, _N = translations('utils')

# Default address for the server providing the REST API
_REST_ADDR = 'http://localhost/'


def _execute_request(verb, path, **kwargs):
    """Send an HTTP request to the REST API.

    Parameters:
        verb: HTTP verb to use for the request (mainly 'GET' and 'POST').
        path: URL of the target page.
        kwargs: extra arguments for the request such as POST data or timeout.
    """
    kwargs.update({'auth': HTTPBasicAuth(basic_user, basic_password)})
    try:
        request(verb, _REST_ADDR + path, **kwargs)
    except RequestException as e:
        print(_('REST request {} failed:').format(path[:-1]), file=stderr)
        for pretty_print in traceback.format_exception_only(type(e), e):
            print(pretty_print, file=stderr)

def _do_request(path, args=None):
    """Execute a request on a separate thread to avoid waiting on I/O.

    Parameters:
        path: URL of the target page.
        args: POST data for the page that will be json encoded.
    """
    if args:
        thread = Thread(target=_execute_request,
                name='rest-post',
                args=('POST', path),
                kwargs={'timeout':15, 'data':{'data':json.dumps(args)}})
    else:
        thread = Thread(target=_execute_request,
                name='rest-get',
                args=('GET', path),
                kwargs={'timeout':15})
    thread.start()

def setup(game_name, rules, *people):
    """Tell the REST API about a new race that is likely to be started soon.

    Parameters:
        game_name: name for the route and custom rules used for this race.
        rules: route and custom rules data for this race.
        people: informations on the drivers of this race.
    """
    """JSON
    Setup object:
    -------------
     - pilotes: Array of driver objects
            -> drivers for this race
     - course: Race object
            -> rules for this race

    Race object:
    ------------
     - nom: string
            -> name for the set of rules
     - temps: number or null
            -> time available before the race ends, if relevant
     - tours: number or null
            -> number or laps needed to clear the race, if relevant
     - portes: Array of strings
            -> active gates identificators for this race

    Driver object:
    --------------
     - id: number
            -> identification of the beacon given to the driver for the race
     - nom: string
            -> name of the driver
     - drone: string
            -> kind of its drone
    """
    setup = rules.get_setup()
    setup.update({'nom': game_name})
    data = {'pilotes': people, 'course': setup}
    _do_request('setup/', data)

def warmup(text, start):
    """Tell the REST API that a race is being started and provide a
    text to display.
    """
    """JSON
    Warm-up object:
    --------------
     - texte: string
            -> text to display
     - start: bool
            -> whether the race should be started (timer, leader-board, etc.)
    """
    _do_request('warmup/', {'texte': text, 'start': start})

def update(drone):
    """Tell the REST API that a drone had its status changed."""
    """JSON
    Drone object:
    -------------
     - id: number
            -> identification number of the beacon attached on the drone
     - position: number
            -> ranking of the drone at this moment of the race
     - points: number
            -> number of points for the drone at this moment of the race
     - temps: number
            -> elapsed time from the beginning of the race
     - retard: number or null
            -> delay accumulated over the first overall drone, if relevant
     - tour: number or null
            -> timing of the last lap for this drone, if relevant
     - finish: bool or null
            -> whether the drone finished the race or was declared dead,
                if it is not still flying
     - tours: number
            -> number of laps performed by the drone
     - porte: string or null
            -> identification of the last gate the drone passed by, if relevant
    """
    _do_request('update/', drone)

def cancel():
    """Tell the REST API that a race has been canceled."""
    """JSON
    No data
    """
    _do_request('cancel/')

def finish():
    """Tell the REST API that a race just finished.
    Leader-board may still change.
    """
    """JSON
    No data
    """
    _do_request('finish/')

def leaderboard(*drones):
    """Send the final leader-board to the REST API."""
    """JSON
    Array of drone objects.

    Drone object:
    -------------
     - id: number
            -> identification number of the beacon attached on the drone
     - position: number
            -> ranking of the drone at this moment of the race
     - points: number
            -> number of points for the drone at this moment of the race
     - temps: number
            -> time required by the drone to clear the race
     - retard: number or null
            -> delay accumulated over the first overall drone, if relevant
     - tour: number or null
            -> timing of the best lap for this drone, if relevant
     - finish: bool or null
            -> whether the drone finished the race or was declared dead,
                if it is not still flying
     - tours: number
            -> number of laps performed by the drone
     - porte: string or null
            -> identification of the last gate the drone passed by, if relevant
    """
    _do_request('leaderboard/', {'drones': drones})

