import json
from models import Data
from flask import g
import objects
import pandas as pd
from marshmallow import Schema, fields
import datetime as dt
import pytz

_org = None

class DocumentSchema(Schema):
    invoice = fields.Str(allow_none=True)

#STATES: 'NONE', 'SCHEDULED', 'COMPLETED', 'READY', 'COMPLETE'
class LineitemsSchema(Schema):     
    procedure = fields.Str()
    charge = fields.Str()
    state = fields.Str()

# STATES: 'OPEN', 'ACTIVE', 'GENERATED', 'SENT', 'REMINDED', 'PAID' 
class TimelineSchema(Schema):
    CREATED = fields.DateTime(missing=None)
    ACTIVATED = fields.DateTime(missing=None)
    GENERATED = fields.DateTime(missing=None)
    SENT = fields.DateTime(missing=None)
    REMINDED = fields.DateTime(missing=None)
    PAID = fields.DateTime(missing=None)
    
class Invoice_Schema(Schema):
    key = fields.Str()
    line_items = fields.Nested(LineitemsSchema, missing=[], many=True)
    document = fields.Nested(DocumentSchema, missing=None)
    state = fields.Str(required=True)
    timeline = fields.Nested(TimelineSchema)
    order = fields.Str(required=True)
    modified = fields.DateTime()
    created = fields.DateTime()
    status = fields.Method('get_status', dump_only=True)
    intervals = fields.Method('get_intervals', dump_only=True)
    current = fields.Method('get_current', dump_only=True)

    

    _status = {
        'OPEN': 'OPEN', 
        'ACTIVE': 'OPEN', 
        'GENERATED': 'OPEN', 
        'SENT': 'OPEN',
        'REMINDED' : 'OPEN',
        'PAID': 'COMPLETE'
    }

    def get_intervals(self, item):
        now = dt.datetime.now(dt.timezone.utc)
        
        return {
            'SINCE_OPEN': self._h(now - item['timeline']['CREATED']) if item['timeline']['CREATED'] is not None else None,
            'SINCE_ACTIVE': self._h(now - item['timeline']['ACTIVATED']) if item['timeline']['ACTIVATED'] is not None else None,
            'SINCE_GENERATED': self._h(now - item['timeline']['GENERATED']) if item['timeline']['GENERATED'] is not None else None,
            'SINCE_INVOICED': self._h(now - item['timeline']['SENT']) if item['timeline']['SENT'] is not None else None,
            'SINCE_REMINDED': self._h(now - item['timeline']['REMINDED']) if item['timeline']['REMINDED'] is not None else None
        }

    def get_status(self, item):
        return self._status[item['state']]


    def compare(self, row, intervals):
        if row.comparison == 'NULL':
            return True
        else:
            a = intervals[row.interval]
            op = row.comparison
            b = self.THRESHOLDS[row.threshold]
            if op == '>':
                return a > b
            elif op == '<':
                return a < b
            elif op == '>=':
                return a >= b
            elif op == '<=':
                return a <= b
            elif op == '==':
                return a == b
            else:
                raise ValueError('Invalid Operator')

    def get_current(self, item):
        state = item['state']
        intervals = self.get_intervals(item)
        criticality = {'NORMAL':0, 'WARNING':0, 'CRITICAL':0}

        df = pd.read_csv('./rules/invoice.csv').set_index('priority')
        df1 = objects.Preferences().to_frame()
        tx = df1.set_index(['component','name']).loc[('INVOICES',),:].value*3600
        self.THRESHOLDS = tx.to_dict()
        df['comparison'] = df.comparison.fillna('NULL')
        df['actions'] = df.actions.fillna('')    
        df1 = df[df.state == state]
        df2 = df1.apply(lambda row: self.compare(row, intervals), axis=1)
        df3 = df2[df2].sort_index()
        idx = df3.index[0]
        result = df.loc[idx]
        actions = result.actions.split('||') if len(result.actions) > 0 else []
        criticality[result.criticality] += 1

        current = {
            'actions': actions,
            'status': {
                'status': result.status,
                'criticality': criticality
            }
        }

        return current
    
    
    
    def _h(self, tdelta):
        return 24*3600*tdelta.days + tdelta.seconds

class Invoice(object):
    schema = Invoice_Schema()
    data_schema = Invoice_Schema(exclude=('intervals','current','status'))
    summary_schema = Invoice_Schema(only=('key','timeline','line_items','state','document'))
    update_schema= Invoice_Schema(only=('document','timeline','line_items','state','modified'), partial=True)
    
    def __init__(self, key=None, item=None, who=None):
        self._data = Data(org=g.org, dataset='cases/invoices')
        self.org = g.org
        if key is None:
            if item is not None:
                datum = {
                    'state': 'OPEN',
                    'order': item['order'],
                    'timeline': {
                        'CREATED' : dt.datetime.now(dt.timezone.utc).isoformat(),
                        'ACTIVATED' : None,
                        'GENERATED' : None,
                        'SENT' : None,
                        'REMINDED': None,
                        'PAID': None
                    }
                }
                
                tmp = self.schema.load(datum)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
                tmp_json = self.data_schema.dump(tmp)
                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
            else:
                raise ValueError("No invoice_id provided")
        else:
            self.key = key 
            self.data = self.schema.load(self._data.get(self.key))

    def update(self, item):
        # data = Data(org=self.org, dataset='cases/invoices')
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
            
    def add_item(self, key):
        procedure = objects.Procedure(key=key).data
        item = {}
        item['procedure'] = procedure['key']
        item['charge'] = procedure['rate']
        item['state'] = self._item_state(key)
        line_items = self.schema.dump(self.data).get('line_items')
        line_items.append(item)
        self.update({'line_items': line_items})
        self.update_state()

    def make_send(self):
        email = objects.Email()
        #procedure = objects.Procedure(key=self.data['procedure']).details()
        order = objects.Order(key=self.data['order']).details()
        case = objects.Case(key=order['case']).details()
        patient = objects.Patient(key=case['patient']['key']).details()
        email_info = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': [],
				'cc': [
					{
						'name': 'Samrat Sengupta',
						'email': 'samrat.sengupta@arcvisions.com'
					}
				],
				'subject': f"{'Invoice for'} {patient['name']['salutation']} {patient['name']['display']}"
		}
        if case['is_LoP']:
            lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
            email_info['to'] = {
                    'name': f"{lawyer['name']['salutation']} {lawyer['name']['display']}",
                    'email': lawyer['contact']['email']
                }
        else:
            email_info['to'] = {
                    'name': f"{patient['name']['salutation']} {patient['name']['display']}",
                    'email': patient['contact']['email']
                }
        
        email.set_info(info = email_info)

        charges = [float(item['charge']) for item in self.data['line_items']]
        print(charges, flush=True)
        total = sum(charges)

        email_data = {
            'to': email_info['to'],
            'case': case,
            'order': order,
            'total': total
        }

        email.set_body(template='mail_invoice.html', data=email_data, 
                       document=self.data['document']['invoice'])
        return email


    def make_reminder(self):
        email = objects.Email()
        procedure = objects.Procedure(key=self.data['procedure']).details()
        order = objects.Order(key=procedure['order']).details()
        case =objects.Case(key=order['case']).details()
        lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
        patient = objects.Patient(key=case['patient']['key']).details()

        email.set_info(info = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': {
					'name': lawyer['name']['display'],
					'email': lawyer['contact']['email']
				},
				'cc': [
					{
						'name': f"{patient['name']['salutation']} {patient['name']['display']}",
						'email': patient['contact']['email']
					},
					{
						'name': 'Breezi MRI',
						'email': 'samin@amsaassociates.com'
					}
				],
				'subject': f"{'Invoice for'} {patient['name']['salutation']} {patient['name']['display']}",
				'filename': 'filename.txt'
			})

        email_data = {
            'case': case,
            'order': order
        }

        email.set_body(template='mail_invoice_reminder.html', data=email_data, 
                       document=self.data['document']['invoice'])
        return email



    def _item_state(self, key):
        if self.data['state'] != 'PAID':
            procedure = objects.Procedure(key=key).data
            appt_key = procedure['appointment']

            if appt_key is None:
                state = 'NONE'
            else:
                appointment = objects.Appointment(key=appt_key).data
                if appointment['state'] == 'NONE':
                    state = 'NONE'
                elif appointment['state'] in ['SCHEDULED','REMINDED','ARRIVED','CHECKED_IN','IN_PROGRESS']:
                    state = 'SCHEDULED'
                elif appointment['state'] == 'COMPLETE':
                    report = objects.Report(key=procedure['report']).data
                    if report['state'] in ['NONE','WAITING','REMINDED']:
                        state = 'WAITING'
                    elif report['state'] in ['ATTACHED','SENT']:
                        state = 'READY'
        else:
            state = 'CLOSED'
        return state
        # NONE, SCHEDULED, WAITING, READY, CLOSED

    def update_charge(self, line_items):
        self.update({'line_items': line_items})
        self.update_state()
        return self.data

    def update_state(self):
        invoice = self.schema.dump(self.data)
        line_items = invoice.get('line_items')
        timeline = invoice.get('timeline')
        states = []
        for item in line_items:
            item['state'] = self._item_state(key=item['procedure'])
            states.append(item['state'])
        self.update({'line_items': line_items})
        if invoice['state'] == 'OPEN' and all([state == 'READY' for state in states]):
            timeline['ACTIVATED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({'timeline': timeline, 'state': 'ACTIVE'})

        
        
    def action(self, name):
        print('INVOICE_ACTION:', name, flush=True)
        action_map = {
            'attach': self._attach,
            'generate': self._generate,
            'send' : self._send,
            'remind': self._remind,
            'complete': self._complete
        }
        return action_map[name]()
            
    def _generate(self):
        print('_generate:', self.data['state'], flush=True)
        if self.data['state'] == 'ACTIVE':
#            print(self.data, flush=True)
#            self.data['document']['invoice']= "7D5B9ECCE2A511E984A4645A0434F7BB"
            item = {
                'doc_type': 'INVOICE',
                'ref_type': 'ORDER',
                'ref_key': self.data['order']
            }

            document = objects.Document(item=item)

            print('IN INVOICE GENERATE:', document.summary(), flush=True)

            order = objects.Order(key=item['ref_key']).details()
            case = objects.Case(key=order['case']).details()

            invoice_date = dt.datetime.utcnow()\
                            .replace(tzinfo=pytz.UTC)\
                            .astimezone(pytz.timezone("America/Chicago"))

            total_charge = 0
            for procedure in order['procedures']:
                if 'charge' in procedure and procedure['charge'] is not None:
                    total_charge += float(procedure['charge'])
                else:
                    procedure['charge'] = procedure['rate']
                procedure['adj'] = float(procedure['charge']) - float(procedure['rate'])

            patient = objects.Patient(key=case['patient']['key']).details()

            for i, o in enumerate(case['orders']):
                if o['key'] == order['key']:
                    break
            order_key = i + 1

            doi = dt.datetime.fromisoformat(case['injury_date'])\
                    .replace(tzinfo=pytz.UTC)\
                    .astimezone(pytz.timezone("America/Chicago"))\
                    .strftime("%Y%m%d")

            dob = dt.datetime.fromisoformat(patient['dob'])\
                    .replace(tzinfo=pytz.UTC)\
                    .astimezone(pytz.timezone("America/Chicago"))\
                    .strftime("%Y%m%d")

            chart = f'BRZ{doi}-{dob}-{order_key}' 

            invoice_data = {
                'case': case, 
                'order': order, 
                'date': invoice_date.strftime("%B %d, %Y"),
                'total': total_charge,
                'patient': patient,
                'chart': chart
            }

            document = document.create(item={
                'template':'invoice.html',
                'data': invoice_data
                })

            print('INVOICE GENERATED:', document.summary(), flush=True)

            timeline = self.schema.dump(self.data).get('timeline')
            timeline['GENERATED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'GENERATED',
                'document': {
                    'invoice': document.key
                },
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'INVOICE',
                'ref_key': self.key,
                'log_type': 'GENERATED',
                'what': None
            })
        return objects.Document(key=self.data['document']['invoice'])
        
    def _attach(self):
        if self.data['state'] in ['OPEN']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['ATTACHED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'ACTIVE',
                'timeline': timeline
            })
        return self.data['state']

    def _remind(self):
        if self.data['state'] in ['SENT','REMINDED']:
            try:
                self.make_reminder().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['REMINDED'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'REMINDED',
                    'timeline': timeline
                })
                self.add_log({
                    'ref_type':'INVOICE',
                    'ref_key': self.key,
                    'log_type': 'REMINDED',
                    'what': None
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']
    
    def _send(self):
        if self.data['state'] in ['GENERATED']:
            try:
                self.make_send().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['SENT'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'SENT',
                    'timeline': timeline
                })
                self.add_log({
                    'ref_type':'INVOICE',
                    'ref_key': self.key,
                    'log_type': 'SENT',
                    'what': None
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']
    
    def _complete(self):
        if self.data['state'] in ['SENT','REMINDED']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['PAID'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'PAID',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'INVOICE',
                'ref_key': self.key,
                'log_type': 'COMPLETE',
                'what': None
            })
        return self.data
    
    
    def details(self):
        return self.schema.dump(self.data)

    def document_data(self):
        invoice_date = dt.datetime.utcnow()\
                        .replace(tzinfo=pytz.UTC)\
                        .astimezone(pytz.timezone("America/Chicago"))\
                        .strftime("%B %d, %Y")

        order = objects.Order(key=self.data['order']).details()
        case = objects.Case(key=order['case']).details()
        order_index = case['orders'].index(order['key'])
        patient = objects.Patient(key=case['patient']['key']).details()

        total_charge = 0.0
        for line_item in self.data['line_items']:
            procedure = objects.Procedure(key=line_item['procedure']).details()
            total_charge += float(line_item['charge'])
            line_item['procedure'] = procedure
            line_item['adj'] = float(line_item['charge']) - float(procedure['rate']) 

        doi = dt.datetime.fromisoformat(case['injury_date'])\
                .replace(tzinfo=pytz.UTC)\
                .astimezone(pytz.timezone("America/Chicago"))\
                .strftime("%Y%m%d")

        dob = dt.datetime.fromisoformat(patient['dob'])\
                .replace(tzinfo=pytz.UTC)\
                .astimezone(pytz.timezone("America/Chicago"))\
                .strftime("%Y%m%d")

        chart = f'BRZ{doi}-{dob}-{order_index}' 

        return {
            'case': case, 
            'order': order, 
            'date': invoice_date,
            'total': total_charge,
            'patient': patient,
            'chart': chart
        }

    def add_log(self, item):
        order = objects.Order(key=self.data['order']).details()
        objects.Case(key=order['case']).add_log(item=item)