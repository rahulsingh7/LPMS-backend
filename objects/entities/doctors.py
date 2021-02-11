# import data
from models import Data
from flask import g
from marshmallow import Schema, fields, post_load

import uuid
import datetime as dt
import time

class NameSchema(Schema):
    salutation = fields.String(required=True)
    first = fields.String(required=True)
    middle = fields.String(default='', allow_none=True)
    last = fields.String(required=True)
    middle_initial = fields.Method('abbreviate_middle', dump_only=True)
    display = fields.Method('build_display_name', dump_only=True)

    def abbreviate_middle(self, name):
        if name is not None and name['middle'] is not None:
            return name['middle'][0].upper() + '.'
        else:
            return None

    def build_display_name(self, name):
        if name['middle'] is not None:
            return f"{name['first']} {self.abbreviate_middle(name)} {name['last']}"
        else:
            return f"{name['first']} {name['last']}"

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

class DoctorSchema(Schema):
    key = fields.String()
    name = fields.Nested(NameSchema, required=True)
    contact = fields.Nested(ContactSchema, required=True)
#    dob = fields.Date(required=True)
    practise = fields.String(required=True)
    degree = fields.String(allow_none=True, missing=None)
    npi_physician = fields.String(default=None, allow_none=True)
    npi_practise = fields.String(default=None, allow_none=True)
    address = fields.Nested(AddressSchema)
    note = fields.String(default=None, allow_none=True)
#    age = fields.Function(lambda obj: (dt.datetime.utcnow() - obj.dob).years, dump_only=True)
    modified = fields.DateTime()
    created = fields.DateTime()

class DoctorSchema2(Schema):
    key = fields.Str()
    name = fields.Str(required=True)
    phone = fields.Str(required=True)
    email = fields.Email(default=None, allow_none=True)
    fax = fields.Str(default=None, allow_none=True)
    modified = fields.DateTime()
    created = fields.DateTime()

class Doctor(object):
    schema = DoctorSchema()
    schema_2json = DoctorSchema(exclude=('name.display', 'name.middle_initial', 'address.summary'))
    summary_schema = DoctorSchema(only=('key','name.salutation','degree','name.display','practise' ,'note',\
                                        'contact.phone', 'contact.email','address.summary'))
#    update_schema = DoctorSchema(only=('name','phone','fax','modified'), partial=True)
    update_schema = DoctorSchema(only=('name', 'contact', 'npi_physician','degree',\
                                        'practise', 'npi_practise', 'address', 'note'), partial=True)
    
    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org=g.org, dataset='entities/doctors')
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
            raise ValueError("No Doctor_id provided")
           
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

    def update(self, item):
        # data = Data(org=self.org, dataset='entities/doctors')
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

class Doctor2(object):
    schema = DoctorSchema2()
    summary_schema = DoctorSchema2(only=('key','name','phone','email','fax'))
    update_schema = DoctorSchema2(only=('name','phone','fax'), partial=True)

    def __init__(self, key=None, item=None):
        self._data = Data(org=g.org, dataset='entities/doctors')
        self.org = g.org
        if key is None:
            if item is not None:
                tmp = self.schema.load(item)
                tmp['created'] = dt.datetime.utcnow()
                tmp['modified'] = tmp['created']

                tmp_json = self.schema.dump(tmp)

                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
            else:
                raise ValueError("No doctor_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
        

    
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

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

class Doctors:
    schema = DoctorSchema(many=True)
    summary_schema = DoctorSchema(only=('key','name.salutation','degree','practise','name.display','contact.phone','address.summary'), many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='entities/doctors')
        if query is not None:
            tmp_list = self._data.query(filters=query)
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)
