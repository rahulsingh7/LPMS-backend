from models import Data
from flask import g
# from .. import Patient, Lawyer
# from .. import Order, Log
import objects
from marshmallow import Schema, fields, post_load

import sys
import uuid
import datetime as dt
import time

_org = None

class CaseSchema(Schema):
    key = fields.Str()
    patient = fields.Str(required=True)
    injury_date = fields.Date(required=True)
    lawyer = fields.Str(missing=None)
    is_LoP= fields.Boolean(required=True)
    orders = fields.List(fields.Str(), missing=None, many=True)
    log = fields.List(fields.Str(), missing=None, many=True)
    status = fields.Method('case_status', dump_only=True)

    modified = fields.DateTime()
    created = fields.DateTime()

    def case_status(self, item):
        status = {
            'order': {
                'status':'NONE',
                'criticality':{'NORMAL':0,'WARNING':0,'CRITICAL':0}
                },
            'lop': {
                'status':'NONE',
                'criticality':{'NORMAL':0,'WARNING':0,'CRITICAL':0}
                },
            'appointment': {
                'status':'NONE',
                'criticality':{'NORMAL':0,'WARNING':0,'CRITICAL':0}
                },
            'report': {
                'status':'NONE',
                'criticality':{'NORMAL':0,'WARNING':0,'CRITICAL':0}
                },
            'invoice': {
                'status':'NONE',
                'criticality':{'NORMAL':0,'WARNING':0,'CRITICAL':0}
                }
        }

        if len(item['orders']) > 0:
            order_q = []
            appointment_q=[]
            lop_q=[]
            report_q=[]
            invoice_q=[]
            for order_key in item['orders']:
                order = objects.Order(key=order_key).details()
                order_q.append(order['current']['order'])
                appointment_q.append(order['current']['appointment'])
                lop_q.append(order['current']['lop'])
                report_q.append(order['current']['report'])
                invoice_q.append(order['current']['invoice'])
                
            criticality_order = status['order']['criticality']
            for s in order_q:
                for k,v in s['criticality'].items():
                    criticality_order[k] += v
            u = all([s['status'] == 'NONE' for s in order_q])
            v = all([s['status'] == 'COMPLETE' for s in order_q])
            status_order = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
            status['order'] = {
                'status': status_order,
                'criticality': criticality_order
            }
            
            criticality_lop = status['lop']['criticality']
            for s in lop_q:
                for k,v in s['criticality'].items():
                    criticality_lop[k] += v
            u = all([s['status'] == 'NONE' for s in lop_q])
            v = all([s['status'] == 'COMPLETE' for s in lop_q])
            w = all([s['status'] == 'UNREQUIRED' for s in lop_q])
            status_lop = 'UNREQUIRED' if w \
                    else 'NONE' if u \
                    else 'COMPLETE' if v \
                    else 'OPEN'
            status['lop'] = {
                'status': status_lop,
                'criticality': criticality_lop
            }

            criticality_appointment = status['appointment']['criticality']
            for s in appointment_q:
                for k,v in s['criticality'].items():
                    criticality_appointment[k] += v
            u = all([s['status'] == 'NONE' for s in appointment_q])
            v = all([s['status'] == 'COMPLETE' for s in appointment_q])
            status_appointment = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
            status['appointment'] = {
                'status': status_appointment,
                'criticality': criticality_appointment
            }
            
            criticality_report = status['report']['criticality']
            for s in report_q:
                for k,v in s['criticality'].items():
                    criticality_report[k] += v
            u = all([s['status'] == 'NONE' for s in report_q])
            v = all([s['status'] == 'COMPLETE' for s in report_q])
            status_report = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
            status['report'] = {
                'status': status_report,
                'criticality': criticality_report
            }

            criticality_invoice = status['invoice']['criticality']
            for s in invoice_q:
                for k,v in s['criticality'].items():
                    criticality_invoice[k] += v
            u = all([s['status'] == 'NONE' for s in invoice_q])
            v = all([s['status'] == 'COMPLETE' for s in invoice_q])
            status_invoice = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
            status['invoice'] = {
                'status': status_invoice,
                'criticality': criticality_invoice
            }

        return status


class Case(object):
    schema = CaseSchema()
    storage_schema=CaseSchema(exclude=('status',))
    summary_schema = CaseSchema(only=('key','is_LoP','orders','patient','lawyer','status','modified'))
    update_schema = CaseSchema(only=('orders','patient','lawyer','is_LoP', 'log','modified'), partial=True)

    def __init__(self, key=None, item=None, who=None):
        self._data = Data(org=g.org, dataset='cases/cases') 
        self.org = g.org
        if key is None:
            if item is not None and who is not None:
                # TOFIX
                items = {
                    'patient': item['patient'],
                    'injury_date': item['injury_date'],
                    'is_LoP' : item['is_LoP'],
                    'lawyer' : item['lawyer'],
                    'orders': [],
                    'log': []
                }
                tmp = self.schema.load(items,partial=True)

                tmp['created'] = dt.datetime.utcnow()
                tmp['modified'] = tmp['created']

                tmp_json = self.storage_schema.dump(tmp)
                tmp_data = self._data.create(tmp_json)
                self.data = self.schema.load(tmp_data)
                self.key = self.data['key']
                
                # ADD_LOG:
                self.add_log({
                    'ref_type':'CASE',
                    'ref_key': self.key,
                    'who': who,
                    'log_type': 'CREATED',
                    'what': None
                })

                #....Considering the Lawyer and Patient mentioned exists in the System.....
            else:
                raise ValueError("No order_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
    
   
    def details(self):
        case_details = self.schema.dump(self.data)
        case_details['patient'] = objects.Patient(key=case_details['patient']).summary()
        if case_details['is_LoP']:
            case_details['lawyer'] = objects.Lawyer(key=case_details['lawyer']).summary()

        orders = []
        for order in case_details['orders']:
            orders.append(objects.Order(key=order).details())
        case_details['orders'] = orders

        logs = []
        for log in case_details['log']:
            logs.append(objects.Log(key=log).details())
        case_details['log'] = logs

        return case_details
    
    def summary(self):
        return self.summary_schema.dump(self.data)

    # def update(self, item):
    #     #TOFIX_TODAY
    #     if item is not None:
    #         item = {k:v for k,v in item.items() if v is not None}
    #         errors = self.update_schema.validate(item)
    #         if not errors:
    #             tmp = self.update_schema.load(item)
    #             tmp['modified'] = dt.datetime.utcnow()
    #             tmp_json = self.update_schema.dump(tmp)
    #             updated_dict = data.update(self.key, tmp_json)
    #             self.data = self.schema.load(updated_dict)
    #             return self.summary_schema.dump(self.data)
    #         else:
    #             print(errors, flush=True)
    #             raise ValueError(errors)
    #     else:
    #         raise ValueError("No item to update")

    def update(self, item):
        self._data = Data(org=self.org, dataset='cases/cases')
        if item is not None:
            item = {k:v for k,v in item.items() if v is not None}
            try:
                tmp = self.update_schema.load(item)
                tmp['modified'] = dt.datetime.now(dt.timezone.utc)
                tmp_json = self.update_schema.dump(tmp)
            except Exception as errors:
                print('Dump Errors:', errors, flush=True)
                raise ValueError(errors)

            try:
                updated_dict = self._data.update(self.key, tmp_json)
                self.data = self.schema.load(updated_dict)
                return self.schema.dump(self.data)
            except Exception as errors:
                print('Load Errors:', errors, flush=True)
                raise ValueError(errors)
        else:
            raise ValueError("No item to update")

    
    def update_items(self, item, who):
        updated = self.update(item)
        self.add_log({
            'ref_type':'CASE',
            'ref_key': self.key,
            'who': who,
            'log_type': 'UPDATED',
            'what': 'case update'
        })
        return updated

    def add_order(self, item, who):
        item['case'] = self.key 
        order_id = objects.Order(item=item, is_LoP = self.data['is_LoP'], who=who).key
        orders = self.data['orders']
        orders.append(order_id)
        self.update(item={'orders': orders})
        return self.schema.dump(self.data)

    def add_log(self, item):
        log = objects.Log(item=item).details()
        if 'log' in self.data and self.data['log'] is not None:
            self.data['log'].append(log['key'])
        else:
            self.data['log'] = [log['key']]
        self.update(item={'log': self.data['log']}) 


class Cases:
    schema = CaseSchema(many=True)
    data_schema = CaseSchema(many=True)

    def __init__(self):
        self._data = Data(org=g.org, dataset='cases/cases')
        self.org = g.org
        self.data = self.schema.load(self._data.items())

    def details(self):
        return self.data_schema.dump(self.data)

    def summaries(self):
        try:
            case_summaries = self.data_schema.dump(self.data)
            for case in case_summaries:
                case['patient'] = objects.Patient(key=case['patient']).summary()
                if (case['is_LoP']):
                    case['lawyer'] = objects.Lawyer(key=case['lawyer']).summary()
            return case_summaries
        except Exception as e:
            print('CASE ERROR:', e, flush=True)
            raise ValueError(e)
