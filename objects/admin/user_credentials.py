# import data as data
from models import Data
from marshmallow import Schema, fields, post_load
from passlib.context import CryptContext
 
import uuid
import datetime as dt
import time
 

class CredentialSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True) 
    key = fields.Str(required=True)
    org = fields.Str(required=True)
    modified = fields.DateTime()
    created = fields.DateTime()

class Credential(object):
    schema = CredentialSchema() 

    def __init__(self, username=None, item=None):
        self._data = Data(org='common', dataset='admin/user_credentials')
        #self.org = 'common'
        self.pwd_context = CryptContext(
            schemes=["pbkdf2_sha256"],
            default="pbkdf2_sha256",
            pbkdf2_sha256__default_rounds=3000 #30000
		)

        if username is None:
            if item is not None:
                tmp = self.schema.load({
                    "username": item["username"],
                    "password": self.pwd_context.encrypt(item["password"]),
                    "key": item["key"],
                    "org": item["org"]
                })

                tmp['created'] = dt.datetime.utcnow()
                tmp['modified'] = tmp['created']

                tmp_json = self.schema.dump(tmp)

                self.data = self.schema.load(self._data.insert(tmp_json['username'],tmp_json))
                self.key = self.data['username']
            else:
                raise ValueError("No username provided")
        else:
            self.key = username
            self.data = self.schema.load(self._data.get(self.key))
            # print(self.key, self.data, flush=True)

    def verify(self, args):
        #data = Data(org=self.org, dataset='user_credentials')
        username = args['username']
        password = args['password']

        credential = self._data.get(username)

        if self.pwd_context.verify(password, credential['password']):
            return self.data
        else:
            raise ValueError("Password Mismatch")

    def update(self, password):
        # data = Data(org=self.org, dataset='user_credentials')
        self.data['password'] = self.pwd_context.encrypt(password)
        self.data['modified'] = dt.datetime.utcnow()
        tmp_json = self.schema.dump(self.data)

        self.data = self.schema.load(self._data.update(tmp_json['username'],tmp_json))