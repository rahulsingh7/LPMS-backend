# import data 
from models import Data
#from . import Order
from flask import g
from marshmallow import Schema, fields, post_load

import uuid
import datetime as dt
import time

class MasterProcedureSummarySchema(Schema):
    key = fields.Str(required=True)
    code = fields.Str(required=True)
    desc = fields.Str(required=True)
    cpt_desc = fields.Str(required=True)
    cpt_code = fields.Str(required=True)
    rate = fields.Str(required=True)
    scan_type= fields.Str(required=True)
    body_part = fields.Str(required=True)
    bpt_code = fields.Str(required=True)
    area = fields.Str(required=True)
    apt_code = fields.Str(required=True)
    
class MasterProcedure(object):
    schema = MasterProcedureSummarySchema()
    summary_schema = MasterProcedureSummarySchema(only=
        ('key','code','desc','cpt_desc','cpt_code','rate','scan_type'))

    def __init__(self, key):
        self._data = Data(org='master', dataset='master/master_procedure_summary')
        if key is not None:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
        else:
            raise KeyError("No Procedure key")

    def details(self):
        return self.schema.dump(self.data)
    
    def summary(self):
        return self.summary_schema.dump(self.data)
    

class MasterProcedureSummary:
    schema = MasterProcedureSummarySchema(many=True)
    summary_schema = MasterProcedureSummarySchema(only=
        ('key','code','desc','cpt_desc','cpt_code','rate','scan_type'), many=True)
        
    def __init__(self, key=None):
        self._data = Data(org='master', dataset='master/master_procedure_summary')
        if key is None:
            # print(data.master_procedures_summary, flush=True)
            self.data = self.schema.load(self._data.items())
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
            # print("DATA_TO_OBJ", self.data, flush=True)

    def summary(self):
        return self.summary_schema.dump(self.data)