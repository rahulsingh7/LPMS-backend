from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import MasterProcedureSummary
from . import api
from flask_jwt_extended import jwt_required, get_jwt_identity


master_ns = api.namespace("master", description="Master data Related Apis")


@master_ns.route("/procedures")
class ProcedureSummaryList(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of Master procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return MasterProcedureSummary().summary(), 200
        except KeyError:
            return "MasterProcedure does not exist", 404
        except ValueError:
            return "Validation error", 422  

