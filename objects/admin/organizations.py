# import models as data
from models import Data
from marshmallow import Schema, fields
from ..schemas import ContactSchema, AddressSchema
from flask import g
import uuid
import datetime as dt
import time

class OrgSchema(Schema):
    key = fields.String(required=True)
    name = fields.String(required=True)
    category = fields.String(required=True)
    modified = fields.DateTime()
    created = fields.DateTime()
    contact = fields.Nested(ContactSchema, default=None, allow_none=True)
    address = fields.Nested(AddressSchema, default=None, allow_none=True)
    note = fields.String(allow_none=True)

class Organization(object):
    schema = OrgSchema()
    schema_2data = OrgSchema(exclude=('address.summary', 'contact.action'))
    summary_schema = OrgSchema(only=('key','name','category','address.summary'))

    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org='common', dataset='admin/organizations')
        #self._data = Data(org=g.org, dataset='admin/organizations')
        if key is not None:
            self.key = key
            tmp_dict = self._data.get(self.key)
            self.data = self.schema.load(tmp_dict)
        elif item is not None:
            tmp = self.schema.load(item)
            tmp_key = tmp['key']
            tmp['created'] = dt.datetime.utcnow()
            tmp['modified'] = tmp['created']
            tmp_json = self.schema_2data.dump(tmp)
            tmp_dict = self._data.insert(tmp_key, tmp_json)
            self.data = self.schema.load(tmp_dict)
            self.key = self.data['key']
            Data(org=self.key)
        elif query is not None:
            tmp_dict = self._data.query(filters=query, limit=1)
            self.data = self.schema.load(tmp_dict[0])
            self.key = self.data['key']
            pass
        else:
            raise ValueError("No Organization Found")
           
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

class Organizations:
    schema = OrgSchema(many=True)
    summary_schema = OrgSchema(only=('key','name','category','address.summary'), many=True)

    def __init__(self, query=None):
        self._data = Data(org='common', dataset='admin/organizations')
        if query is not None:
            tmp_list = self._data.query(filters=query)
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)
