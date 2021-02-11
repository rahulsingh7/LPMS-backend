from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import CustomProcedureSummary, CustomProcedure
from . import api
from flask_jwt_extended import jwt_required, get_jwt_identity


custom_ns = api.namespace("custom", description="custom procedures Related Apis")


@custom_ns.route("/procedure")
class CustomProcedureSummaryinfolist(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of Custom procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return CustomProcedureSummary().summary(), 200 
        except KeyError:
            return "MasterProcedure does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @jwt_required
    def post(self):
        """
        Add a new Custom Procedure
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            #args = self.parser.parse_args()
            args = request.json
            return CustomProcedure(item=args).details(), 200
        except KeyError:
            return "?", 404


@custom_ns.route("/procedure/<string:key>")
class CustomProcedureAPI(Resource):
    
    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return CustomProcedure(key=key).details(), 200
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
            item = request.json
            return CustomProcedure(key=key).update(item=item), 200
        except KeyError as e:
            print(e, flush=True)
            return "Procedure does not exist", 404
        except ValueError:
            return "Validation error", 422  



