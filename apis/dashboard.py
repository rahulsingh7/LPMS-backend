from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api
from analytics import Dashboard
from flask_jwt_extended import jwt_required, get_jwt_identity

dashboard_ns = api.namespace("dashboard", description="dashboard Related Apis")

@dashboard_ns.route("/info")
class Dashboardinfolist1(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity() 
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard1(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422

@dashboard_ns.route("/info2")
class Dashboardinfolist2(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard2(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422

@dashboard_ns.route("/info3")
class Dashboardinfolist3(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard3(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422


@dashboard_ns.route("/info4")
class Dashboardinfolist4(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard4(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422


@dashboard_ns.route("/info5")
class Dashboardinfolist5(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard5(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422


@dashboard_ns.route("/info6")
class Dashboardinfolist6(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard6(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422


@dashboard_ns.route("/info7")
class Dashboardinfolist7(Resource):

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        try:
            return Dashboard().dashboard7(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422
        except Exception as e:
            print(e, flush=True)
            return "Miscelleneous Error", 422
