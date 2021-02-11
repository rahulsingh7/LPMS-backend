from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import Preference, Preferences
from . import api
import sys
from flask_jwt_extended import jwt_required, get_jwt_identity

preference_ns = api.namespace("preference", description="prefrences Related Apis")

@preference_ns.route("/info")
class prefrencesinfolist(Resource):
    @jwt_required
    def get(self):
        """
        returns a list of prefrences
        """
        print("Prefrences APIS")
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Preferences().details(), 200
        except KeyError:
            return "Prefrence does not exist", 404
        except ValueError:
            return "Validation error", 422  


    
@preference_ns.route("/info/<string:key>")
class Preferenceinfo(Resource):
        
    @jwt_required
    def get(self, key):
        """
        Displays a prefrence details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
           return Preference(key=key).details(), 200
        except KeyError:
            return "Prefrence does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            item = request.json
            return Preference(key=key).update(item), 200
        except KeyError as e:
            print('KeyError: ', e, file=sys.stderr, flush=True)
            return "Prefrence not found", 404
        except ValueError as e:
            print('ValueError: ', e, file=sys.stderr, flush=True)
            return "?", 422
        except Exception as e:
            print(e, flush=True)

@preference_ns.route("/summary/<string:key>")
class preferencesummary(Resource):
    @jwt_required
    def get(self, key):
        """
        Displays a prefrence's information summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
           return Preference(key=key).summary(), 200
        except :
            pass

