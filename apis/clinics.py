from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import Clinic, Clinics
from . import api
from flask_jwt_extended import jwt_required, get_jwt_identity

clinic_ns = api.namespace("clinic", description="Clinic Related APIs")

@clinic_ns.route("/info")
class Clinicinfolist(Resource):
    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Clinics().details(), 200
        except KeyError:
            return "Clinic does not exist", 404
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422  

    @jwt_required
    def post(self):
        """
        Add a new Clinic
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            args = request.json
            return Clinic(item=args).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "?", 404
        except Exception as e:
            print(e, flush=True)


@clinic_ns.route("/info/<string:key>")
class Clinicinfo(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str)
    parser.add_argument('phone', type=str)
    parser.add_argument('fax', type=str)

    @jwt_required
    def get(self, key):
        """
        Display a Clinic's details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Clinic(key=key).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Clinic does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self,key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            args = request.json
            return Clinic(key=key).update(item=args), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "?", 404
        except Exception as e:
            print(e, flush=True)


    def delete(self, key):
        """
        Delete a Clinic
        """
        pass

@clinic_ns.route("/summary/<string:key>")
class Clinicsummary(Resource):
    @jwt_required
    def get(self, key):
        """
        Get a Clinic's information summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Clinic(key=key).summary(), 200
        except:
            pass
