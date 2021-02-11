# import data
from models import Data
import objects as objs
from flask import g
#from .. import Procedure, Doctor
#from .. import Log, Doctor

from marshmallow import Schema, fields
import uuid
import datetime as dt
    
_org = None

class OrderSchema(Schema):
    key = fields.Str()
    date = fields.Date(required=True)
    doctor = fields.Str(required=True)
    document = fields.Str(missing=None, allow_none=True)

    # DOWNSTREAM COMPONENTS
    procedures = fields.List(fields.Str(), missing=[], allow_none=True, many=True)
    appointments = fields.List(fields.Str(), missing=[], allow_none=True, many=True)
    unscheduled = fields.Method('get_unscheduled', dump_only=True)
    
    # ASSOCIATED ELEMENTS
    lop = fields.Str(missing=None, allow_none=True)
    invoice = fields.Str(missing=None, allow_none=True)
    
    # UPSTREAM REFERENCE
    case = fields.Str(required=True)
    
    # BOOK-KEEPING
    current = fields.Method('get_status', dump_only=True)
    modified = fields.DateTime()
    created = fields.DateTime()
    
    def get_unscheduled(self, item):
        unscheduled = []
        for procedure in item['procedures']:
            appointment = objs.Procedure(key=procedure).data['appointment']
            if appointment is None:
                unscheduled.append(procedure)
        return unscheduled
    
    def get_status(self, item):
        status = {}

        mandatory = item['date'] is not None and item['doctor'] is not None
        secondary = len(item['procedures']) > 0 and item['document'] is not None
        if mandatory:
            if secondary:
                status['order'] = {
                    'status': 'COMPLETE', 
                    'criticality': {'NORMAL': 1, 'WARNING': 0, 'CRITICAL': 0}
                }
            else:
                status['order'] = {
                    'status': 'OPEN', 
                    'criticality': {'NORMAL': 1, 'WARNING': 0, 'CRITICAL': 0}
                }
        else:
            status['order'] = {
                'status': 'NONE', 
                'criticality': {'NORMAL': 1, 'WARNING': 0, 'CRITICAL': 0}
            }
            
        lop = objs.LoP(key=item['lop']).details()

        current_appointment = []
        current_report = []
        current_lop = []
        for procedure in item['procedures']:
            current = objs.Procedure(key=procedure).details().get('current')
            current_appointment.append(current['appointment']['status'])
            current_report.append(current['report']['status'])
            current_lop.append(current['lop']['status'])
        
        criticality_lop = lop['current']['status']['criticality']
        for s in current_lop:
            for k,v in s['criticality'].items():
                criticality_lop[k] += v
        status['lop'] = {
            'status': lop['current']['status']['status'],
            'criticality': criticality_lop
        }
        
        criticality_appointment = {'NORMAL': 0, 'WARNING': 0, 'CRITICAL': 0}
        for s in current_appointment:
            for k,v in s['criticality'].items():
                criticality_appointment[k] += v
        u = all([s['status'] == 'NONE' for s in current_appointment])
        v = all([s['status'] == 'COMPLETE' for s in current_appointment])
        status_appointment = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
        status['appointment'] = {
            'status': status_appointment,
            'criticality': criticality_appointment
        }

        criticality_report = {'NORMAL': 0, 'WARNING': 0, 'CRITICAL': 0}
        for s in current_report:
            for k,v in s['criticality'].items():
                criticality_report[k] += v
        u = all([s['status'] == 'NONE' for s in current_report])
        v = all([s['status'] == 'COMPLETE' for s in current_report])
        status_report = 'NONE' if u else 'COMPLETE' if v else 'OPEN'
        status['report'] = {
            'status': status_report,
            'criticality': criticality_report
        }
        if item['invoice'] is not None:
            status['invoice'] = objs.Invoice(key=item['invoice']).details().get('current').get('status')
            
        return status


class Order(object):
    schema = OrderSchema()
    data_schema = OrderSchema(exclude=('unscheduled','current'))
    summary_schema = OrderSchema(only=('key', 'case', 'date','doctor','procedures','document'))
#    update_schema= OrderSchema(only=('documents','timeline', 'lop_status','log','procedures','doctor','modified'), partial=True)
    update_schema= OrderSchema(only=('document','lop','invoice','procedures','appointments','modified'), partial=True)
    
    def __init__(self, key=None, item=None, is_LoP=True, who=None):
        self._data = Data(org=g.org, dataset='cases/orders')
        self.org = g.org 
        if key is None:
            if item is not None:
                tmp = self.schema.load(item)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
                
                tmp_json = self.data_schema.dump(tmp)

                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
                
                self.case = objs.Case(key=self.data['case'])
                self.add_LoP_obj(who=who)
                self.add_invoice_obj(who=who)
                
                self.add_log({							   
                    'ref_type':'ORDER',
                    'ref_key': self.key,
                    'log_type': 'CREATED',
                    'what': None
                })

            else:
                raise ValueError("No order_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
            self.case = objs.Case(key=self.data['case'])
            
#    def _updatable(self, key):
#        if key in ['date', 'doctor', 'document']:
#            # If LoP Request has been sent
#            if self.data['lop']:
                
            
    def update(self, item):
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
#        case = objs.Case(key=self.data['case'])
#        log_entry = {
#            'ref_type':'ORDER',
#            'ref_key': self.key,
#            'who': who,
#            'log_type': 'UPDATED',
#            'what': 'order update'
#        }
#        self.add_log(order_update_log,case=case.key)
        return updated
    
    def details(self):
        order = self.schema.dump(self.data)
        if order['doctor'] is not None:
            order['doctor'] = objs.Doctor(key=order['doctor']).summary()

        if order['document'] is not None:
            order['document'] = objs.Document(key=order['document']).summary()

        lop = objs.LoP(key=order['lop']).details()
        order['lop'] = lop

        procedures = []
        for procedure in order['procedures']:
            procedures.append(objs.Procedure(key=procedure).details())
        order['procedures'] = procedures

        appointments = []
        for appointment in order['appointments']:
            appointments.append(objs.Appointment(key=appointment).details())
        order['appointments'] = appointments

        invoice = objs.Invoice(key = order['invoice']).details()
        order['invoice'] = invoice 

        return order
    
    def add_procedure(self, item, who):
        item['order'] = self.key
        procedure = objs.Procedure(item=item, who=who)
        procedures = self.schema.dump(self.data).get('procedures')
        procedures.append(procedure.key)
        self.update(item={'procedures': procedures})
        objs.Invoice(key=self.data['invoice']).add_item(key=procedure.key)
        return self.case.key
    
    def add_appointment(self, item, who):
        datum = self.schema.dump(self.data)
        appointments = datum.get('appointments')
        unscheduled = datum.get('unscheduled')
        
        valid = all([procedure in unscheduled for procedure in item['procedures']])
        if valid:
            app = objs.Appointment(item=item, who=who)
            appointments.append(app.key)
            self.update(item={'appointments': appointments})
        else:
            raise ValueError("Invalid Procedures")
        return self.data

    def reschedule_appointment(self,item, who):
        datum = self.schema.dump(self.data)
        appointments = datum.get('appointments')
        if item['appointment'] in appointments:
            objs.Appointment(key=item['appointment'], who=who).action('reschedule',item=item, who=who)
        else:
            raise KeyError("Appointment not found")
        return self.data

    def cancel_appointment(self,item, who):
        datum = self.schema.dump(self.data)
        appointments = datum.get('appointments')
        if item['appointment'] in appointments:
            objs.Appointment(key=item['appointment'], who=who).action('cancel', item=item, who=who)
        else:
            raise KeyError("Appointment not found")
        return self.data


    def remove_appointment(self, key):
        appointments = self.schema.dump(self.data).get('appointments')
        if key in appointments:
            appointments.remove(key)
            self.update(item={'appointments': appointments})
        else:
            raise ValueError("Invalid Appointment")
        return self.data
    
    def add_LoP_obj(self, who):
        item = {
            'order': self.key,
            'is_LoP': self.case.data['is_LoP']
        }
        lop = objs.LoP(item=item, who=who)
        self.update({'lop': lop.key})

    def add_invoice_obj(self, who):
        item = {
            'order': self.key
        }
        invoice = objs.Invoice(item=item, who=who)
        self.update({'invoice': invoice.key}) 

    def add_log(self, item):
        objs.Case(key=self.data['case']).add_log(item=item)

    def add_document(self, key=None, item=None, file=None, who=None):
        if item is not None:
            if item['doc_type'] == 'ORDER':
                document = objs.Document(item=item, file=file)
                self.update({'document': document.key})
                print("REPORT ADD DOC",flush=True)
                self.add_log({							   
                    'ref_type':'ORDER',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': None
                })
            elif item['doc_type'] == 'LOP':
                if key is None:
                    if item['ref_type'] == 'CASE':
                        item['ref_key'] = self.case.key
                    document = objs.Document(item=item, file=file)
                else:
                    document = objs.Document(key=key)
                objs.LoP(key=self.data['lop']).action('attach', item=document.key)
                self.add_log({							   
                    'ref_type':'LOP',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': None
                })
            elif item['doc_type'] == 'LOP_REQUEST':
                item['ref_type'] = 'ORDER'
                datum = {'case': self.case.details(), 'order': self.details(), 'procedure': ''}
                document = objs.Document(item=item)\
                    .create(item={'template': "lopr.html", 'data': datum})
                objs.LoP(key=self.data['lop']).update_request(key=document.key)
                return document
            elif item['doc_type'] == 'INVOICE':
                #document = "7D5B9ECCE2A511E984A4645A0434F7BB"
                # hard coded 
                document = objs.Invoice(key=self.data['invoice']).action('generate')
                return document

        else:
            document = objs.Document(key=key)
            objs.LoP(key=self.data['lop']).action('attach', item=document.key)
            self.add_log({							   
                'ref_type':'LOP',
                'ref_key': self.key,
                'log_type': 'ATTACHED',
                'what': None
            })


    def summary(self):
        return self.summary_schema.dump(self.data)

class Orders:
    schema = OrderSchema(many=True)
    summary_schema = OrderSchema(only=('key', 'date', 'doctor', 'procedures'), many=True)

    def __init__(self):
        self._data = Data(org=g.org, dataset='cases/orders')
        self.data = self.schema.load(self._data.items())


    def details(self):
        return self.summary_schema.dump(self.data)
