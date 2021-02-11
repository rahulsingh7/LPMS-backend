from flask_restplus import Resource, Api, reqparse
from flask import request, g
import sys
from objects import Patient, Patients
from . import api
from flask_jwt_extended import jwt_required, get_jwt_identity


patient_ns = api.namespace("patient", description="Patient Related APIs")

@patient_ns.route("/info")
class Patientinfolist(Resource):
    @jwt_required
    def get(self):
        """
        Get a list of Patients
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Patients().details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Patient does not exist", 404
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422  

    @jwt_required
    def post(self):
        """
        Add a new Patient
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            args = request.json
            print(args, flush=True)
            return Patient(item=args).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "?", 404
        except Exception as e:
            print(e, flush=True)


@patient_ns.route("/info/<string:key>")
class Patientinfo(Resource):
    @jwt_required
    def get(self, key):
        """
        Display a Patient's details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Patient(key=key).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Patient does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self, key):
        """
        Edit a Patient's information
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            item = request.json
            return Patient(key=key).update(item), 200
        except KeyError as e:
            print('KeyError: ', e, file=sys.stderr, flush=True)
            return "Patient not found", 404
        except ValueError as e:
            print('ValueError: ', e, file=sys.stderr, flush=True)
            return "?", 422
        except Exception as e:
            print(e, flush=True)

    def delete(self, key):
        """
        Delete a Patient
        """
        pass

@patient_ns.route("/summary/<string:key>")
class Patientsummary(Resource):
    @jwt_required
    def get(self, key):
        """
        Get a Patient's information summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Patient(key=key).summary(), 200
        except :
            pass
