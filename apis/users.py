from functools import wraps
from flask import request, g
from flask_restplus import Resource, Api, reqparse
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity,verify_jwt_in_request, get_jwt_claims)
from . import api, jwt

from objects import User, Credential, Users, Organization

import string
import random

import sendgrid
from sendgrid.helpers.mail import * 

user_ns = api.namespace("user", description="User Related Apis")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt_claims()
        if claims['roles']['org'] == 'client':
            if claims['roles']['user'] == 'admin':
                return fn(*args, **kwargs)
            else:
                return 'Access Denied',403
        else:
            return fn(*args, **kwargs)
    return wrapper


@jwt.user_claims_loader
def add_claims_to_access_token(response):
    return {'roles': {
        'org': response['org']['category'],
        'user': response['user']['role']
    },
    'org': response['user']['org']
    }


@user_ns.route("/auth")
class UserLogin(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, required=True)
    parser.add_argument('password', type=str, required=True)

    @api.expect(parser)
    def post(self):
        # print("BASE URL",request.base_url,flush=True)
        args = self.parser.parse_args()    
        try:
            user_info = Credential(username=args['username']).verify(args)
            g.user = user_info['key']
            g.org = user_info['org']
            user = User(key=user_info['key']).summary()
            org = Organization(key=user['org']).summary()

            response = {
                'user': user,
                'org': org
            }

            response['access_token'] = create_access_token(identity=response)
            return response, 200
        except KeyError as e:
            print(e, flush=True)
            return "User does not exist", 404
        except ValueError:
            return "Login unsuccessful", 422 
        except Exception as e:
            print(e, flush=True)


@user_ns.route("/settings/<string:key>")
class UserChangePassword(Resource):
#    self.parser = reqparse.RequestParser()
#    self.parser.add_argument('current_password', type=str, required=True)
#    self.parser.add_argument('new_password', type=str, required=True)

    @jwt_required
    def put(self, key):
        # args = self.parser.parse_args()
        args = request.json    
        current_password = args['current_password']
        new_password = args['new_password']

        try:
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key']
            username = User(key=key).data['email']

            credential = Credential(username=username)
            test = credential.verify({
                'username': username,
                'password': current_password
            })

            if test:
                credential.update(new_password)
                return "Password Updated", 200
            else:
                return "Password Mismatch", 422           
        except ValueError:
            return "Password Mismatch", 422 
        except Exception as e:
            print(e, flush=True)

    @jwt_required
    def patch(self, key):

        new_password = ''.join(random.choices(string.digits + string.ascii_letters, k=10))

        try:
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key']
            user = User(key=key).data
            username = user['email']

            credential = Credential(username=username)
            credential.update(new_password)

            sg = sendgrid.SendGridAPIClient(api_key='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')
            from_email= Email('orders@breezemri.com')
            to_email = Email(username)
            subject = 'Password Reset'

            template = '\n\n'.join([
                f"Dear {user['name']},",
                f"Your password has been changed on request. Your new password is {new_password}",
                f"Bia Imaging"
            ])

            content = Content("text/plain", template)
            mail = Mail(from_email, subject, to_email, content)

            response = sg.client.mail.send.post(request_body=mail.get())

            return "Password Reset", 200
        except Exception as e:
            print(e, flush=True)
            return e, 422

        
@user_ns.route("/info")
class Userinfolist(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('email', type=str, required=True)
    parser.add_argument('password', type=str, required=True)
    parser.add_argument('name',type=str, required=True)
    parser.add_argument('phone',type=str, required=True)
    
    @admin_required
    def get(self):
        """
        returns a list of user
        """
        claims = get_jwt_claims()
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            if claims['roles']['org'] == 'client':
                return Users(query={
                    'org': claims['org']
                }).details(), 200
            else:
                return Users().details(), 200
        except KeyError:
            return "User does not exist", 404
        except ValueError:
            return "Validation error", 422  

    @admin_required
    def post(self):
        """
        Adds a new user to the list
        """
        args = request.json
        # print('ARGS:', args, flush=True)
        claims = get_jwt_claims()
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        if claims['roles']['org'] == 'client':    
            args['org'] = claims['org'] 
        elif claims['roles']['org'] == 'host':
            if args['org'] is None:
                args['org'] = claims['org']
        elif claims['roles']['org'] == 'dev':
            if args['org'] is None:
                args['org'] = claims['org']
        # print('ARGS2:', args, flush=True)

        try:
            return User(item=args).summary(), 200
        except KeyError:
            return "User exists", 404
        except ValueError as e:
            return e.args, 422  
        except Exception as e:
            print(e, flush=True)
            return "Validation Error", 422

@user_ns.route("/info/<string:key>")
class Userinfo(Resource):
    @admin_required
    def get(self, key):
        """
        Displays a user details
        """
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']

        try:
            claims = get_jwt_claims()
            return User(key=key).details(), 200
        except KeyError:
            return "User does not exist", 404
        except ValueError:
            return "Validation error", 422  


    @jwt_required
    def put(self, key):
        args = request.json
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']

        User(key=key).update(args)
        return "Updated Successfully", 204

    def delete(self, key):
        """
        Edits a selected user
        """

@user_ns.route("/secret")
class SecretResource(Resource):
    @jwt_required
    def get(self):
        return {
            'logged_in_as' : get_jwt_identity(),
            'current_roles': get_jwt_claims()
        }
