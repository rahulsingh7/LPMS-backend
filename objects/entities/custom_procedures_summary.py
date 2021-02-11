from models import Data
from flask import g
from marshmallow import Schema, fields, post_load

import uuid
import datetime as dt
import time

class CustomProcedureSummarySchema(Schema):
    key = fields.Str()
    code = fields.Str(required=True)
    desc = fields.Str(required=True)
    cpt_desc = fields.Str(required=True)
    cpt_code = fields.Str(required=True)
    body_part = fields.Str(required=True)
    bpt_code = fields.Str(required=True)
    area = fields.Str(required=True)
    apt_code = fields.Str(required=True)
    rate = fields.Str(required=True)
    scan_type = fields.Str(required=True)


class CustomProcedure(object):
    schema = CustomProcedureSummarySchema()
    summary_schema = CustomProcedureSummarySchema(only=
        ('key','code','desc','cpt_desc','cpt_code','rate','scan_type'))
    update_schema = CustomProcedureSummarySchema(only=
        ('code','desc','cpt_desc','cpt_code', 'body_part','bpt_code', 
         'area','apt_code','rate','scan_type'), partial=True)
    # update_schema = CustomProcedureSchema(only=('name','body_part','area','procedure_code','base_procedure','scan_type','modified'),partial=True)
    def __init__(self, key=None, item=None):
        self._data = Data(org=g.org, dataset='entites/custom_procedure_summary')
        self.org = g.org
        if key is None:
            if item is not None:
                tmp = self.schema.load(item,partial=True)
                """ tmp['created'] = dt.datetime.utcnow()
                tmp['modified'] = tmp['created'] """
                
                tmp_json = self.schema.dump(tmp)

                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
            else:
                raise ValueError("No code provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))

    
    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)

    def update(self, item):
        # data = Data(org=self.org, dataset='entites/custom_procedures_summary')
        if item is not None:
            item = {k:v for k,v in item.items() if v is not None}
            errors = self.update_schema.validate(item)
            if not errors:
                print('HERE!')
                self.data = self.schema.load(self._data.update(self.key, item))
                print('AFTER!')
                return self.schema.dump(self.data)
            else:
                print('ERRORS: ', errors, flush=True)
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")


class CustomProcedureSummary:
    schema = CustomProcedureSummarySchema(many=True)
    summary_schema = CustomProcedureSummarySchema(only=('key','code','desc','cpt_desc','cpt_code','rate','scan_type'), many=True)

    def __init__(self):
        self._data = Data(org=g.org, dataset='entities/custom_procedure_summary')
        self.data = self.schema.load(self._data.items())

    def summary(self):
        return self.summary_schema.dump(self.data)