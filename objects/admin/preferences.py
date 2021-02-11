from models import Data
from marshmallow import Schema, fields
from ..schemas import ContactSchema, AddressSchema
from flask import g
import uuid
import datetime as dt
import time
import pandas as pd

class PreferenceSchema(Schema):
    key = fields.Integer(required=True)
    name = fields.String(required=True)
    component = fields.String(required=True)
    value = fields.Integer(required=True)
    description = fields.String(missing=None, allow_none=True)
    

class Preference(object):
    schema = PreferenceSchema()
    schema_2data = PreferenceSchema()
    summary_schema = PreferenceSchema()
    update_schema = PreferenceSchema(only=('value',), partial=True)

    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org=g.org, dataset='admin/preferences')
        self.org = g.org
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

    def update(self, item, force=False):
        data = Data(org=self.org, dataset='admin/preferences')  
        if item is not None:
            if not force:
                item = {k:v for k,v in item.items() if k in ['value']}
                item = {k:v for k,v in item.items() if v is not None}
            errors = self.update_schema.validate(item)
            if not errors:
                tmp = self.update_schema.load(item)
                tmp['modified'] = dt.datetime.utcnow()
                item = self.update_schema.dump(tmp)
                self.data = self.schema.load(data.update(self.key, item))
                return self.schema.dump(self.data)
            else:
                print("Errors:", errors, flush=True)
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")


class Preferences:
    schema = PreferenceSchema(many=True)
    summary_schema = PreferenceSchema(many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='admin/preferences')
        if query is not None:
            tmp_list = self._data.query(filters=query)
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        return self.summary_schema.dump(self.data)

    def to_frame(self):
        # print(pd.DataFrame(self.data).head(), flush=True)
        return pd.DataFrame(self.data)
    