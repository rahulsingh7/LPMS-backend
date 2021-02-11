from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api
from objects import Order, Procedure, Procedures, Case
from flask_jwt_extended import jwt_required, get_jwt_identity

procedure_ns = api.namespace("procedure", description="procedure Related Apis")

@procedure_ns.route("/")
class ProceduresAPI(Resource):
    parser = reqparse.RequestParser()

    @jwt_required
    def post(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            for arg in args:
                case_id = Order(key=arg['order']).add_procedure(item=arg, who=who['user']['key'])
            return Case(key=case_id).details(), 200
        except KeyError as e:
            return f'KeyError: {e.args}', 404
        except ValueError as e:
            return f'ValueError: {e.args}', 422
        except Exception as e:
            print(e, flush=True)
            return f'Error: {e.args}', 406

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Procedures().details(), 200
        except KeyError:
            return "Procedure does not exist", 404
        except ValueError:
            return "Validation error", 422  

@procedure_ns.route("/<string:key>")
class ProcedureAPI(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str)
    parser.add_argument('base_procedure', type=str)
    parser.add_argument('body_part', type=str)
    parser.add_argument('area', type=str)
    parser.add_argument('scan_type', type=str)
    parser.add_argument('procedure_code', type=str)

    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Procedure(key=key).details(), 200
        except KeyError:
            return "Procedure does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            who = get_jwt_identity()
            item = request.json
            return Procedure(key=key).update_items(item=item, who= who['user']['key']), 200
        except Exception as e:
            print(e, flush=True)

    def delete(self, key):
        """
        Edits a selected user
        """

@procedure_ns.route("/<string:key>/charge")
class ProcedureChargeUpdateAPI(Resource):
    @jwt_required
    def put(self,key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            who = get_jwt_identity()
            Procedure(key=key).update_charge(item=args)
            return 'Charge Updated', 200
        except ValueError:
            return "Validation Error", 422
