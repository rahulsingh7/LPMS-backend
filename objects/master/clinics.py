# import data
from models import Data
from flask import g
import json
import pandas as pd
from marshmallow import Schema, fields, post_load

import uuid
import datetime as dt
import time

class ContactSchema(Schema):
    phone = fields.String(required=True)
    alt_phone = fields.String(default=None, allow_none=True)
    fax = fields.String(default=None, allow_none=True)
    email = fields.Email(default=None, allow_none=True)
    preferred = fields.String(required=True)

class AddressSchema(Schema):
    line1 = fields.String(default=None, allow_none=True)
    line2 = fields.String(default=None, allow_none=True)
    city = fields.String(default='', allow_none=True)
    state = fields.String(default='', allow_none=True)
    zipcode = fields.String(default='', allow_none=True)
    summary = fields.Method('summarize_address', dump_only=True)

    def summarize_address(self, address):
        components = {k: address[k] if address[k] is not None else '' for k in ['state', 'zipcode']}
        components['city'] = f"{address['city']}," if address['city'] is not None else ''
        return f"{components['city']} {components['state']} {components['zipcode']}".strip()

class ClinicSchema(Schema):
    key = fields.String()
    name = fields.String(required=True)
    contact = fields.Nested(ContactSchema, required=True)
    # dob = fields.Date(required=True)
    address = fields.Nested(AddressSchema)
    note = fields.String(default=None, allow_none=True)
#    age = fields.Function(lambda obj: (dt.datetime.utcnow() - obj.dob).years, dump_only=True)
    modified = fields.DateTime()
    created = fields.DateTime()

class Clinic(object):
    schema = ClinicSchema()
    schema_2json = ClinicSchema(exclude=('address.summary', ))
    summary_schema = ClinicSchema(only=('key','name','contact','address.summary'))
    update_schema = ClinicSchema(only=('contact','modified','address'))
    
    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org=g.org, dataset='master/clinics')
        self.org = g.org
        if key is not None:
            self.key = key
            tmp_dict = self._data.get(self.key)
            self.data = self.schema.load(tmp_dict)
        elif item is not None:
            tmp = self.schema.load(item)
            tmp['created'] = dt.datetime.utcnow()
            tmp['modified'] = tmp['created']
            tmp_json = self.schema_2json.dump(tmp)
            tmp_dict = self._data.create(tmp_json)
            self.data = self.schema.load(tmp_dict)
            self.key = self.data['key']
        elif query is not None:
            tmp_dict = self._data.query(filters=query, limit=1)
            self.data = self.schema.load(tmp_dict[0])
            self.key = self.data['key']
            pass
        else:
            raise ValueError("No Clinic_id provided")
           
    def details(self):
        return self.schema.dump(self.data)

    def update(self, item):
        # data = Data(org=self.org, dataset='entities/doctors')
        if item is not None:
            item = {k:v for k,v in item.items() if v is not None}
            errors = self.update_schema.validate(item)
            if not errors:
                tmp = self.update_schema.load(item)
                tmp['modified'] = dt.datetime.utcnow()
                item = self.update_schema.dump(tmp)
                self.data = self.schema.load(self._data.update(self.key, item))
                return self.summary_schema.dump(self.data)
            else:
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")
    
    def summary(self):
        return self.summary_schema.dump(self.data)

class Clinics:
    schema = ClinicSchema(many=True)
    summary_schema = ClinicSchema(only=('key','name','contact','address.summary'), many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='master/clinics')
        if query is not None:
            tmp_list = self._data.query(filters=query)
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)

    def dashboard_func(self):
        with open(f'./orgs/{g.org}/data/master/clinics.json','r') as f:
            clinics = json.load(f)
        df = pd.DataFrame(clinics).transpose()
        return df
            