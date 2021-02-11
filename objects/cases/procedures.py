# import data
from models import Data
from flask import g
import objects
import json
import pandas as pd
from marshmallow import Schema, fields
import datetime as dt
 
_org = None

class ProcedureSchema(Schema):
    key = fields.Str()

    code = fields.Str(required=True)
    desc = fields.Str(required=True)
    cpt_desc = fields.Str(required=True)
    cpt_code = fields.Str(required=True)
    scan_type= fields.Str(required=True)
    rate = fields.Str(required=True)
#    charge = fields.Str(missing=None)
        
    order = fields.Str(required=True)
    case = fields.Str(required=True)
    
    appointment = fields.Str(missing=None)
    report = fields.Str(missing=None)

    state = fields.Str(required=True)
    intervals = fields.Method('get_intervals', dump_only=True)
    current = fields.Method('get_current', dump_only=True)

    modified = fields.DateTime()
    created = fields.DateTime()

    THRESHOLDS = {
        'APPOINTMENT_ELAPSED': 0,
        'NO_LOP_CRITICAL': 24,
        'NO_LOP_WARNING': 48,
        'SCHEDULE_DELAY_CRITICAL': 96,
        'SCHEDULE_DELAY_WARNING': 48,
    }
    
    _status = {
        'NONE': 'NONE', 
        'SCHEDULED': 'OPEN', 
        'REMINDED': 'OPEN', 
        'COMPLETE': 'COMPLETE'
    }

    def get_status(self, item):
        return self._status[item['state']]
    
    def get_intervals(self,item):
        now = dt.datetime.now(dt.timezone.utc)
        u = {
            'SINCE_CREATED': self._h(now - item['created']),
        } 
        return u

    def get_current(self, item):
        if item['appointment'] is not None:
            appointment = objects.Appointment(key=item['appointment']).details()
            current = appointment['current']
        else:
            lop_key = objects.Order(key=item['order']).data['lop']
            lop_details = objects.LoP(key=lop_key).details()
            lop = lop_details['state'] 
            appt = 'NONE'
            appt_timings = self.get_intervals(item)
            lop_timings = lop_details['intervals']
            if (lop == "NONE"):
                if (appt == "NONE"):
                    return_val = {
                        'appointment': {
                            'actions': [],
                            'criticality': "NORMAL"
                        },
                        'lop': {
                            'criticality': "NORMAL"
                        }
                    }
            elif (lop == "REQUESTED") or (lop == "REMINDED"):              
                if (appt == "NONE"):
                    return_val = {
                        'appointment': {
                            'actions': ["schedule"],
                            'criticality': "NORMAL"
                        },
                        'lop': {
                            'criticality': "NORMAL"
                        }
                    }
            elif lop == "ATTACHED" or lop == "UNREQUIRED":
                if (appt == "NONE"):
                    if (lop == "ATTACHED" ):
                        since_active = lop_timings['SINCE_ATTACHED'] 
                    else: 
                        since_active = appt_timings['SINCE_CREATED']

                    if (since_active > (self.THRESHOLDS['SCHEDULE_DELAY_CRITICAL']*3600)):
                        return_val = {
                            'appointment': {
                                'actions': ["schedule"],
                                'criticality': "CRITICAL"
                            },
                            'lop': {
                                'criticality': "NORMAL"
                            }
                        }
                    elif (since_active > (self.THRESHOLDS['SCHEDULE_DELAY_WARNING']*3600)):
                        return_val = {
                            'appointment': {
                                'actions': ["schedule"],
                                'criticality': "WARNING"
                            },
                            'lop': {
                                'criticality': "NORMAL"
                            }
                        }
                    else:
                        return_val = {
                            'appointment': {
                                'actions': ["schedule"],
                                'criticality': "NORMAL"
                            },
                            'lop': {
                                'criticality': "NORMAL"
                            }
                        }
            c0 = {'NORMAL':0, 'WARNING':0, 'CRITICAL':0}
            c0.update({return_val['appointment']['criticality']: 1})
            c1 = {'NORMAL':0, 'WARNING':0, 'CRITICAL':0}
            c1.update({return_val['lop']['criticality']: 1})
            current = {
                'appointment': {
                    'actions': return_val['appointment']['actions'],
                    'status': {
                        'status': self.get_status(item),
                        'criticality': c0
                    }
                },
                'lop': {
                    'status': {
                        'criticality': c1
                    }
                }
            }

        report = objects.Report(key=item['report']).details()
        current['report'] = report['current']         
        return current
    
    def _h(self, tdelta):
        return 24*3600*tdelta.days + tdelta.seconds

class Procedure(object):
    schema = ProcedureSchema()
    data_schema = ProcedureSchema(exclude=('intervals','current'))
    update_schema = ProcedureSchema(exclude=('intervals','current'), partial=True)
    
    def __init__(self, key=None, item=None, who=None):
        self._data = Data(org=g.org, dataset='cases/procedures')  
        self.org = g.org
        if key is None:
            if item is not None:
                order = objects.Order(key=item['order'])
                item['case'] = objects.Case(key=order.data['case']).key
                item['state'] = 'NONE'
                tmp = self.schema.load(item)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
#                if 'charge' not in tmp:
#                    tmp['charge'] = tmp['rate']
                tmp_json = self.data_schema.dump(tmp)

                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
                
                report = objects.Report(item={'procedure': self.key}).key
                self.update({'report': report})

                self.add_log({
                    'ref_type':'PROCEDURE',
                    'ref_key': self.key,
                    'who': who,
                    'log_type': 'ADDED',
                    'what': None
                })
            else:
                raise ValueError("No order_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
    
    def details(self):
        procedure =  self.schema.dump(self.data)
#        if procedure['appointment'] is not None:
#            procedure['appointment'] = objects.Appointment(key=procedure['appointment']).data
        if procedure['report'] is not None:
            procedure['report'] = objects.Report(key=procedure['report']).details() 
        return procedure
    
    def summary(self):
        return self.schema.dump(self.data)
    
    def update(self, item, force=False):
        data = Data(org=self.org, dataset='cases/procedures')  
        if item is not None:
            if not force:
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

    def update_items(self, item, who):
        updated = self.update(item)
        self.add_log({
            'ref_type':'PROCEDURE',
            'ref_key': self.key,
            'who': who,
            'log_type': 'UPDATED',
            'what': 'procedure update'
        })
        return updated

    def add_appointment(self, item):
        self.update({
            'appointment': item['appointment'],
            'state': 'ADDED'
        })
    
    def remove_appointment(self):
        self.update({
            'appointment': None,
            'state': 'NONE'
        }, force=True)

    def add_document(self, item, file=None, who=None):
        if item['doc_type'] == "REPORT":
            document = objects.Document(item=item, file=file) 
            report = objects.Report(key=self.data['report'])
            print("procedure add doc", flush=True)
            report.action('attach', item=document.key, who=who)
            print("procedure add doc report attached", flush=True)

            
    def add_log(self, item):
        objects.Case(key=self.data['case']).add_log(item=item)

    def update_charge(self, item):
        self.update(item= {'charge': item['charge']})

    def __repr__(self):
        return f'Procedure({self.key})'

class Procedures:
    schema = ProcedureSchema(many=True)

    def __init__(self):
        self._data = Data(org=g.org, dataset='cases/procedures')
        self.data = self.schema.load(self._data.items())

    def details(self):
        return self.schema.dump(self.data)

    def to_frame(self):
        # print(pd.DataFrame(self.data).head(), flush=True)
        return pd.DataFrame(self.data)

    def dashboard_func(self):
        df = objects.Procedures().to_frame().set_index('key',drop=False)
        df.index.name = 'index'
        return df
            
