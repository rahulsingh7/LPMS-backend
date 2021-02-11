from functools import wraps
from flask_restplus import Resource, Api, reqparse
from flask import request, g
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity,verify_jwt_in_request, get_jwt_claims)
import sys
from objects import Organization, Organizations
from . import api, jwt

org_ns = api.namespace("org", description="Organization Related APIs")

def org_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt_claims()
        if claims['roles']['org'] == 'client':
            return 'Access Denied',403
        else:
            return fn(*args, **kwargs)
    return wrapper



@org_ns.route("/info")
class OrganizationInfoList(Resource):
    @org_required
    def get(self):
        """
        Get a list of Organizations
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Organizations().details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Organization does not exist", 404
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422  

    @org_required
    def post(self):
        """
        Add a new Organization
        """
        try:
            args = request.json
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key']
#            print(args, flush=True)
            return Organization(item=args).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "?", 404
        except Exception as e:
            print(e, flush=True)
            return "Something went wrong", 422

@org_ns.route("/info/<string:key>")
class OrganizationInfo(Resource):
    @org_required
    def get(self, key):
        """
        Display Organization details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Organization(key=key).details(), 200
        except KeyError as e:
            print('KeyError', e, flush=True)
            return "Organization does not exist", 404
        except ValueError as e:
            print('ValueError', e, flush=True)
            return "Validation error", 422  
        except Exception as e:
            print(e, flush=True)
            return "Something went wrong", 422

    def delete(self, key):
        """
        Delete an Organization
        """
        pass

@org_ns.route("/summary/<string:key>")
class OrganizationSummary(Resource):
    @org_required
    def get(self, key):
        """
        Get Organization summary
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Organization(key=key).summary(), 200
        except :
            pass
