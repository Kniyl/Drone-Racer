from requests import request, RequestException
from threading import Thread
from sys import stderr
import traceback
try:
    import simplejson as json
except ImportError:
    import json


_REST_ADDR = 'http://localhost/'


def _execute_request(verb, path, **kwargs):
    try:
        request(verb, _REST_ADDR + path, **kwargs)
    except RequestException as e:
        print('REST request', path[:-1], 'failed:', file=stderr)
        for pretty_print in traceback.format_exception_only(type(e), e):
            print(pretty_print, file=stderr)

def _do_request(path, args=None):
    if args:
        thread = Thread(target=_execute_request,
                name='rest-post',
                args=('POST', path),
                kwargs={'timeout':15, 'data':json.dumps(args)})
    else:
        thread = Thread(target=_execute_request,
                name='rest-get',
                args=('GET', path),
                kwargs={'timeout':15})
    thread.start()

def setup(game_name, rules, *people):
    """
    Setup object:
    -------------
     - pilotes: Array of driver objects
            -> pilotes pour la course
     - course: Race object
            -> configuration de la course

    Race object:
    ------------
     - nom: string
            -> type de jeu
     - temps: number or null
            -> temps disponible pour finir la course, si pertinent
     - tours: number or null
            -> nombre de tours à réaliser pour finir la course, si pertinent
     - portes: Array of strings
            -> identifiants des portes actives pour la course

    Driver object:
    --------------
     - id: number
            -> identifiant de la balise donnée au pilote pour la course
     - nom: string
            -> nom du pilote
     - drone: string
            -> type de son drone
    """
    setup = rules.get_setup()
    setup.update({'nom': game_name})
    data = {'pilotes': people, 'course': setup}
    _do_request('setup/', data)

def warmup(text):
    """
    Warmup object:
    --------------
     - texte: string
            -> texte à afficher
     - start: bool
            -> savoir si on doit démarrer la course (chrono, classement, etc.)
    """
    _do_request('warmup/', text)

def update(drone):
    """
    Drone object:
    -------------
     - id: number
            -> identifiant de la balise portée par le drone
     - position: number
            -> position du drone dans la course
     - points: number
            -> nombre de points engrangés par le drone jusqu’ici
     - temps: number
            -> temps depuis le début du tour
     - retard: number
            -> retard accumulé sur le drone de tête
     - tour: number or null
            -> temps du dernier tour, si pertinent
     - finish: bool or null
            -> état du drone à la fin de la course (finish/dead), si pertinent
     - tours: number
            -> nombre de tours réalisés par le drone
     - porte: string or null
            -> identifiant de la dernière porte traversée, si pertinent
    """
    _do_request('update/', drone)

def cancel():
    """Pas de données"""
    _do_request('cancel/')

def finish():
    """Pas de données"""
    _do_request('finish/')

def leaderboard(*drones):
    """Array of drone objects.
    
    Drone object:
    -------------
     - id: number
            -> identifiant de la balise portée par le drone
     - position: number
            -> position du drone dans la course
     - points: number
            -> nombre de points engrangés par le drone jusqu’ici
     - temps: number
            -> temps depuis le début du tour
     - retard: number
            -> retard accumulé sur le drone de tête
     - tour: number or null
            -> temps du dernier tour, si pertinent
     - finish: bool or null
            -> état du drone à la fin de la course (finish/dead), si pertinent
     - tours: number
            -> nombre de tours réalisés par le drone
     - porte: string or null
            -> identifiant de la dernière porte traversée, si pertinent
    """
    _do_request('leaderboard/', drones)
