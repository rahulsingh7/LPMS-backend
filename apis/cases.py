from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api, jwt
from objects import Case, Cases, Log, Logs
import sys
import pandas as pd
from functools import wraps
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity,verify_jwt_in_request, get_jwt_claims)

case_ns = api.namespace("case", description="Order Related Apis")

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        who = get_jwt_identity()
        g.org = who['org']['key']
        g.user = who['user']['key']
        claims = get_jwt_claims()
        g.claims = (claims['roles']['org'], claims['roles']['user'])
        df = pd.read_csv('test.csv').set_index(['org_catagory','user_role','endpoint','method']).sort_index()
        endpoint = str(request.url_rule)
        print('URL_RULE:',endpoint,flush=True)
        print('METHOD:', request.method, flush=True)
        print('KEY:', (g.claims[0],g.claims[1],endpoint,request.method), flush=True)
        print('DF:', df.loc[(g.claims[0],g.claims[1],endpoint,request.method)], flush=True) 
        if df.loc[(g.claims[0],g.claims[1],endpoint,request.method)].can:
            return fn(*args, **kwargs)
        else:
            return 'Access Denied',403
    return wrapper

@jwt.user_claims_loader
def add_claims_to_access_token(response):
    return {'roles': {
        'org': response['org']['category'],
        'user': response['user']['role']
        },
    'org': response['user']['org']
    }


@case_ns.route("/") 
class Caseinfolist(Resource):
    
    @auth_required
    @jwt_required
    def get(self):
        """
        returns a list of orders
        """
        try:
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key'] 
            return Cases().summaries(), 200
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422  
        except Exception as e:
            print(e, file=sys.stderr, flush=True)
            return "Miscelleneous Error", 422

    @auth_required
    @jwt_required
    def post(self):
        """
        Adds a new user to the list
        """
        args = request.json
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 
        
        try:
            return Case(item=args, who=who['user']['key']).details(), 200
        except ValueError:
            return "Validation error", 422
        except Exception as e:
            print(e, file=sys.stderr, flush=True)
            return f"Error: {e.args}", 406


@case_ns.route("/<string:key>")
class Caseinfo(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('patient_id', type=str)
    parser.add_argument('lawyer_id',type=str)
    parser.add_argument('is_lop',type=bool)

    @auth_required
    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 

        try:
            return Case(key=key).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Order does not exist", 404
        except ValueError:
            return "Validation error", 422

    @auth_required
    @jwt_required
    def put(self, key):
        """
        Edits a selected case
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key'] 

        try:
            item = request.json
            return Case(key=key).update_items(item ,who=who['user']['key']), 200
        except Exception as e:
            print(e, flush=True)

    def delete(self, key):
        """
        Edits a selected user
        """
