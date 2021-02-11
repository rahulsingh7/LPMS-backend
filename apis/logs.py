from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api
import objects
#from objects import Case, Cases, Log, Logs
import sys
from flask_jwt_extended import jwt_required, get_jwt_identity

log_ns = api.namespace("log", description="Log Related Apis")

@log_ns.route("/")
class LogInfolist(Resource):

    @jwt_required
    def get(self):
        """
        returns a list of orders
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return objects.Logs().details(), 200
        except ValueError:
            return "Validation error", 422  
        except Exception as e:
            print(e, file=sys.stderr, flush=True)


    @jwt_required
    def post(self): 
        args = request.json        
        # print("POST: /logs :", args, flush=True)
        who = get_jwt_identity() 
        g.user = who['user']['key']
        g.org = who['org']['key']       
        try:
            if args['ref_type'] == 'CASE':
                log = objects.Log(item=args).details()
                objects.Case(key=args['ref_key']).add_log(item=log['key'])
                return 'Log Added', 200
            elif args['ref_type'] == 'ORDER':
                log = objects.Log(item=args).details()
                objects.Order(key=args['ref_key']).add_log(item=log['key'])
                return 'Log Added', 200
            elif args['ref_type'] == 'PROCEDURE':
                log = objects.Log(item=args).details()
                objects.Procedure(key=args['ref_key']).add_log(item=log['key'])
                return 'Log Added', 200
            elif args['ref_type'] == 'APPOINTMENT':
                log = objects.Log(item=args).details()
                objects.Appointment(key=args['ref_key']).add_log(item=log['key'])
                return 'Log Added', 200
            else:
                return "Reference Not Found", 404
        except ValueError:
            return "Validation error", 422
        except Exception as e:
            print(e, file=sys.stderr, flush=True) 

