from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import Lawyer, Lawyers
from . import api
import sys
from flask_jwt_extended import jwt_required, get_jwt_identity


lawyer_ns = api.namespace("lawyer", description="Lawyer Related Apis")

@lawyer_ns.route("/info")
class Lawyerinfolist(Resource):
    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Lawyers().details(), 200
        except KeyError:
            return "Lawyer does not exist", 404
        except ValueError:
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)

    @jwt_required
    def post(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            args = request.json
            return Lawyer(item=args).details(), 200
        except KeyError:
            return "?", 404


@lawyer_ns.route("/info/<string:key>")
class Lawyerinfo(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name',type=str)
    parser.add_argument('phone',type=str)
    parser.add_argument('fax', type=str)

    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Lawyer(key=key).details(), 200
        except KeyError:
            return "Lawyer does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            item = request.json
            return Lawyer(key=key).update(item), 200
        except KeyError as e:
            print('KeyError: ', e, file=sys.stderr, flush=True)
            return "Lawyer not found", 404
        except ValueError as e:
            print('ValueError: ', e, file=sys.stderr, flush=True)
            return "?", 422
        except Exception as e:
            print(e, flush=True)


    def delete(self, key):
        """
        Edits a selected lawyer
        """

@lawyer_ns.route("/summary/<string:key>")
class Lawyersummary(Resource):
    @jwt_required
    def get(self, key):
        """
        Displays a lawyer information summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
           return Lawyer(key=key).summary(), 200
        except :
            pass