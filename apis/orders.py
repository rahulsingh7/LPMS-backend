from flask_restplus import Resource, Api, reqparse
from flask import request, g
from objects import Order, Orders, Case
from flask_jwt_extended import jwt_required, get_jwt_identity

from .utils import auth_required
from . import api, jwt

# from functools import wraps
# import pandas as pd
# from flask_jwt_extended import (
#     JWTManager, jwt_required, create_access_token,
#     get_jwt_identity,verify_jwt_in_request, get_jwt_claims)


order_ns = api.namespace("order", description="Order Related Apis")

# def auth_required(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         verify_jwt_in_request()
#         who = get_jwt_identity()
#         g.org = who['org']['key']
#         g.user = who['user']['key']
#         claims = get_jwt_claims()
#         g.claims = (claims['roles']['org'], claims['roles']['user'])
#         df = pd.read_csv('test.csv').set_index(['org_catagory','user_role','endpoint','method']).sort_index()
#         endpoint = str(request.url_rule)
#         print('URL_RULE:',endpoint,flush=True)
#         print('METHOD:', request.method, flush=True)
#         print('KEY:', (g.claims[0],g.claims[1],endpoint,request.method), flush=True)
#         print('DF:', df.loc[(g.claims[0],g.claims[1],endpoint,request.method)], flush=True) 
#         if df.loc[(g.claims[0],g.claims[1],endpoint,request.method)].can:
#             return fn(*args, **kwargs)
#         else:
#             return 'Access Denied',403
#     return wrapper

# @jwt.user_claims_loader
# def add_claims_to_access_token(response):
#     return {'roles': {
#         'org': response['org']['category'],
#         'user': response['user']['role']
#         },
#     'org': response['user']['org']
#     }


@order_ns.route("/")
class OrdersAPI(Resource):
    @auth_required    
    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Orders().details(), 200
        except KeyError:
            return "User does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @auth_required
    @jwt_required
    def post(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            Case(key=args['case']).add_order(item=args, who=who['user']['key'])
            return Case(key=args['case']).details(), 200
        except KeyError as e:
            return f'KeyError: {e.args}', 404
        except ValueError as e:
            return f'ValueError: {e.args}', 422
        except Exception as e:
            print('Exception', e, flush=True)
            return f'Error: {e.args}', 406


@order_ns.route("/<string:key>")
class OrderAPI(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('doctor_id', type=str)

    @auth_required
    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Order(key=key).details(), 200
        except KeyError:
            return "Order does not exist", 404
        except ValueError:
            return "Validation error", 422  
    
    @auth_required
    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            item = self.parser.parse_args()
            return Order(key=key).update_items(item=item, who=who['user']['key']), 200
        except Exception as e:
            print(e, flush=True)

    def delete(self, key):
        """
        Edits a selected user
        """

