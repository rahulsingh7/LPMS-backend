from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import MasterProcedure, MasterProcedureSummary 
from . import api
from models import Data
# from data import Data
import json
from flask_jwt_extended import jwt_required, get_jwt_identity


master_ns = api.namespace("master", description="Master procedures Related Apis")


@master_ns.route("/procedure/")
class MasterProcedureSummaryinfolist(Resource):

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

@master_ns.route("/procedure/<string:key>")
class MasterProcedureinfo(Resource):

    @jwt_required
    def get(self, key):
        """
        returns a list of Master procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return MasterProcedure(key=key).details(), 200
        except KeyError:
            return "MasterProcedure does not exist", 404
        except ValueError:
            return "Validation error", 422  

@master_ns.route("/procedure/area")
class MasterProcedureArea(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of Master procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        data = Data(org='master', dataset='master/master_areas')
        area=list(data.items())
        try:
            return area,200
        except KeyError:
            return "MasterProcedure Area does not exist", 404
        except ValueError:
            return "Validation error", 422  


@master_ns.route("/procedure/body_part")
class MasterProcedureBodypart(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of Master procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        data = Data(org='master', dataset='master/master_body_parts')
        body_part=list(data.items())
        try:
            return body_part,200
        except KeyError:
            return "MasterProcedure bodypart does not exist", 404
        except ValueError:
            return "Validation error", 422  

@master_ns.route("/procedure/base")
class MasterProcedureBase(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of Master procedures
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        data = Data(org='master', dataset='master/master_base')
        base=list(data.items())
        try:
            return base,200
        except KeyError:
            return "MasterProcedure bodypart does not exist", 404
        except ValueError:
            return "Validation error", 422  
