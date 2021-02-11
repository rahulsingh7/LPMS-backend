from models import Data
from flask import g
from .. import Credential
import objects
from marshmallow import Schema, fields, post_load

import uuid
import datetime as dt
import time

class UserSchema(Schema):
    key = fields.Str()
    name = fields.Str(required=True)
    phone = fields.Str(required=True)
    email = fields.Email(default=None, allow_none=True)
    org = fields.Str(required=True)
    role = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)
    log = fields.List(fields.Str(), missing=None, allow_none=True, many=True)
    modified = fields.DateTime()
    created = fields.DateTime()
    note = fields.Str(allow_none=True)

class User(object):
    schema = UserSchema()
    data_schema = UserSchema(exclude=('password',))
    summary_schema = UserSchema(only=('key','name','phone','email','org','role'), partial=True)
    update_schema = UserSchema(only=('name','phone','role','note','log','modified'), partial=True)

    def __init__(self, key=None, item=None):
        # print("APIS: step-2", flush=True)
        if key is None:
            if item is not None:
                self._data = Data(org=item['org'], dataset='admin/users')
                self.org = item['org']
                tmp = self.schema.load(item)
                tmp['created'] = dt.datetime.utcnow()
                tmp['modified'] = tmp['created']

                tmp_json = self.schema.dump(tmp)

                try:
                    Credential(username=item["email"])
                    raise ValueError('User Exists')
                except KeyError:
                    self.data = self.data_schema.load(self._data.create(tmp_json))
                    self.key = self.data['key']

                    Credential(item={
                        "username": item["email"],
                        "password": item["password"],
                        "key": self.key,
                        "org": item['org']
                    })
            else:
                raise ValueError("No user_id provided")
        else:
            self._data = Data(org=g.org, dataset='admin/users')
            self.org = g.org
            self.key = key
            self.data = self.data_schema.load(self._data.get(self.key))
        

    
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

    def update(self, item):
        # data = Data(org=self.org, dataset='admin/users')
        if item is not None:
            item = {k:v for k,v in item.items() if v is not None}
            errors = self.update_schema.validate(item)
            if not errors:
                tmp = self.update_schema.load(item)
                tmp['modified'] = dt.datetime.utcnow()
                item = self.update_schema.dump(tmp)
                self.data = self.data_schema.load(self._data.update(self.key, item))
                return self.summary_schema.dump(self.data)
            else:
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")

    def add_log(self, key=None, item=None):
        if item is not None:
            log = objects.Log(item=item).details()
            key = log['key']
        elif key is not None:
            pass
        else:
            return None

        if 'log' in self.data and self.data['log'] is not None:
            self.data['log'].append(key)
        else:
            self.data['log'] = [key]
        self.update(item={'log': self.data['log']})
        

class Users:
    schema = UserSchema(many=True, exclude=('password',))
    summary_schema = UserSchema(only=('key','name','phone','email','org','role'), many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='admin/users')
        self.org = g.org
        if query is not None:
            tmp_list = self._data.query(filters=query)[0]
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)
