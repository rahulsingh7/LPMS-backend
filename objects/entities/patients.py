# import data
from models import Data
from flask import g
from marshmallow import Schema, fields, ValidationError
from ..schemas import NameSchema, ContactSchema, AddressSchema

import uuid
import datetime as dt
import time

class PatientSchema(Schema):
    key = fields.String()
    name = fields.Nested(NameSchema, required=True)
    contact = fields.Nested(ContactSchema, required=True)
    dob = fields.Date(required=True)
    address = fields.Nested(AddressSchema)
    note = fields.String(default=None, allow_none=True)
    age = fields.Method('compute_age', dump_only=True)
    modified = fields.DateTime()
    created = fields.DateTime()

    def compute_age(self, patient):
        return (dt.datetime.utcnow().date() - patient['dob']).days//365

class Patient(object):
    schema = PatientSchema()
    schema_2json = PatientSchema(exclude=('name.display', 'name.middle_initial', \
        'address.summary', 'age', 'contact.action'))
    summary_schema = PatientSchema(only=('key','name.salutation','name.display', \
        'dob', 'contact.phone', 'contact.email','address.summary', 'note','created'))
    update_schema = PatientSchema(only=('name', 'contact', 'dob', 'address', 'note'), partial=True)
    
    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org=g.org, dataset='entities/patients')
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
            raise ValueError("No Patient")
           
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

    def update(self, item):
        # data = Data(org=self.org, dataset='entites/patients')
        if item is not None:
            item = {k:v for k,v in item.items() if v is not None}
            errors = self.update_schema.validate(item)
            if not errors:
                tmp = self.update_schema.load(item)
                tmp['modified'] = dt.datetime.utcnow()
                item = self.schema_2json.dump(tmp)
                self.data = self.schema.load(self._data.update(self.key, item))
                return self.summary_schema.dump(self.data)
            else:
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")

class Patients:
    schema = PatientSchema(many=True)
    summary_schema = PatientSchema(only=('key','name.salutation','name.display', 'dob', 'age', \
        'contact.phone', 'contact.email', 'address.summary', 'note','created'), 
                                    many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='entities/patients')
        if query is not None:
            tmp_list = self._data.query(filters=query)
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)
