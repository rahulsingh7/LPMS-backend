from models import Data
from flask import g
import json
import objects

from marshmallow import Schema, fields, post_load
import pandas as pd 
import uuid
import datetime as dt
import time
    
class LogSchema(Schema):
    key = fields.Str()
    when = fields.DateTime()
    who = fields.Str(required=True)
    what = fields.Str(allow_none=True) 
    ref_type = fields.Str(required=True)
    log_type = fields.Str(required=True)
    ref_key = fields.Str(required=True)
    summary = fields.Method('summarize', dump_only=True)

    def summarize(self, item):    
        if item['ref_type'] == 'CASE':
            if item['log_type'] == 'CREATED':
                return "created a new case"
            elif item['log_type'] == 'UPDATED':
                return "updated the case"
        elif item['ref_type'] == 'ORDER':
            if item['log_type'] == 'CREATED':
                return "created a new order"
            elif item['log_type'] == 'UPDATED':
                return "updated the order"
            elif item['log_type'] == "ATTACHED":
                return "uploaded the order document"
        elif item['ref_type'] == 'APPOINTMENT':
            if item['log_type'] == 'SCHEDULED':
                return "scheduled an appointment"
            elif item['log_type'] == 'RESCHEDULED':
                return "rescheduled the appointment"
            elif item['log_type'] == 'CANCELLED':
                return f"cancelled the appointent due to {item['what']}"
            elif item['log_type'] == 'CHECKED_IN':
                return f"Checked in for appointment"
            elif item['log_type'] == 'ARRIVED':
                return f"arrived for appointment"
            elif item['log_type'] == 'IN_PROGRESS':
                return f"appointment in progress"
            elif item['log_type'] == 'COMPLETED':
                return "marked an appointment Complete"
            elif item['log_type'] == 'REMINDED':
                return "sent an appointment reminder"
            elif item['log_type'] == 'ATTACHED':
                return f"attached {item['what']}"
        elif item['ref_type']== 'PROCEDURE':
            if item['log_type'] == 	'ADDED':
                return "added a procedure"
            elif item['log_type'] == 'UPDATED':
                return "updated the procedure"
        elif item['ref_type']== 'REPORT':
            if item['log_type'] == "UPLOADED":
                return "uploaded a report"
            elif item['log_type'] == "SENT":
                return "sent the report"
            elif item['log_type']  == "REMINDED":
                return "reminded a report"
        elif item['ref_type']== 'INVOICE':
            if item['log_type'] == "GENERATED":
                return "generted an invoice"
            elif item['log_type'] == "SENT":
                return "sent the invoice"
            elif item['log_type'] == "REMINDED":
                return "sent a reminder"
            elif item['log_type'] == "COMPLETE":
                return "marked the invoice paid"
        elif item['ref_type'] == 'LOP':
            if item['log_type'] == 'REQUESTED':
                return "requested an LOP"
            elif item['log_type'] == 'REMINDED':
                return "sent an LOP reminder"
            elif item['log_type'] == 'ATTACHED':
                return "attached an LOP"




class Log(object):
    schema = LogSchema()
    data_schema = LogSchema(exclude=('summary',))
    
    def __init__(self, key=None, item=None, query=None):
        self._data = Data(org=g.org, dataset='entities/logs')
        self.org = g.org
        if key is None:
            if item is not None:
                item['who'] = g.user
                tmp = self.schema.load(item)
                tmp['when'] = dt.datetime.utcnow()
                tmp_json = self.data_schema.dump(tmp)

                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key'] 

                objects.User(key=self.data['who']).add_log(key=self.key)

                #....Considering the Lawyer and Patient mentioned exists in the System.....
            else:
                raise ValueError("No Log_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
    
    def details(self):
        log = self.schema.dump(self.data)
        log['who'] = objects.User(key=log['who']).summary()
        return log
		
class Logs(object):
    schema = LogSchema(many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='entities/logs')
        self.org = g.org
        if query is not None:
            tmp_list = self._data.query(filters=query)[0]
        else:
            tmp_list = self._data.items()
        self.data = self.schema.load(tmp_list)

    def details(self):
        logs = self.schema.dump(self.data)
        for log in logs:
            log['who'] = objects.User(key=log['who']).summary()
        return logs

    def to_frame(self):
        # print(pd.DataFrame(self.data).head(), flush=True)
        return pd.DataFrame(self.data)

    def dashboard_func(self):
        df = objects.Logs().to_frame().set_index('key',drop=False)
        df.index.name = 'index'
        return df
            
