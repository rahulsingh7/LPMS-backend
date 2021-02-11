from flask import request, g
from . import api, jwt
from functools import wraps
import pandas as pd
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity,verify_jwt_in_request, get_jwt_claims)

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
