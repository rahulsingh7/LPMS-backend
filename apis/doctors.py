from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import Doctor, Doctors
from . import api
import sys
from flask_jwt_extended import jwt_required, get_jwt_identity

doctor_ns = api.namespace("doctor", description="doctor Related Apis")


@doctor_ns.route("/info")
class doctorinfolist(Resource):
    # parser = reqparse.RequestParser()
    # parser.add_argument('name',type=str, required=True)
    # parser.add_argument('phone',type=str, required=True)
    # parser.add_argument('email', type=str)
    # parser.add_argument('fax', type=str)
    
    @jwt_required
    def get(self):
        """
        returns a list of doctors
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Doctors().details(), 200
        except KeyError:
            return "Doctor does not exist", 404
        except ValueError:
            return "Validation error", 422  


    # @api.expect(parser)
    @jwt_required
    def post(self):
        """
        Adds a new doctor to the list
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            #args = self.parser.parse_args()
            args = request.json
            return Doctor(item=args).details(), 200
        except KeyError:
            return "?", 404



@doctor_ns.route("/info/<string:key>")
class doctorinfo(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name',type=str)
    parser.add_argument('phone',type=str)
    parser.add_argument('fax', type=str)
    
    @jwt_required
    def get(self, key):
        """
        Displays a doctor details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
           return Doctor(key=key).details(), 200
        except KeyError:
            return "Doctor does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            item = request.json
            return Doctor(key=key).update(item), 200
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
        Edits a selected doctor
        """
        pass

@doctor_ns.route("/summary/<string:key>")
class doctorsummary(Resource):
    @jwt_required
    def get(self, key):
        """
        Displays a doctor's information summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
           return Doctor(key=key).summary(), 200
        except :
            pass