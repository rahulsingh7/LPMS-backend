import json
from models import Data
from flask import g
import objects
import pandas as pd
from marshmallow import Schema, fields
import datetime as dt

_org = None

class TimelineSchema(Schema):
    CREATED = fields.DateTime(missing=None, allow_none=True)
    WAITING = fields.DateTime(missing=None, allow_none=True)
    REMINDED = fields.DateTime(missing=None, allow_none=True)
    ATTACHED = fields.DateTime(missing=None, allow_none=True)
    SENT = fields.DateTime(missing=None, allow_none=True)

class Report_Schema(Schema):
    key = fields.Str()
    procedure = fields.Str()
    timeline = fields.Nested(TimelineSchema)
    state = fields.Str(required=True)
    document = fields.Str(allow_none=True)
    pro_doc = fields.Str(missing=None, allow_none=True)
    modified = fields.DateTime()
    created = fields.DateTime()
    status = fields.Method('get_status', dump_only=True)
    intervals = fields.Method('get_intervals', dump_only=True)
    current = fields.Method('get_current', dump_only=True)

    # tx = pd.read_csv('orgs/arcvisions.com/preferences/thresholds.csv').set_index(['component','name'])\
    #        .loc[('REPORTS',),:].threshold*3600
    # THRESHOLDS = tx.to_dict()
    
    # preferences = json.load(open(f'orgs/arcvisions.com/data/admin/preferences.json'))
    # df1 = pd.DataFrame(preferences).transpose()
    # tx = df1.set_index(['component','name']).loc[('REPORTS',),:].value*3600
    # THRESHOLDS = tx.to_dict()
    
    _status = {
        'NONE': 'NONE', 
        'WAITING': 'OPEN', 
        'REMINDED': 'OPEN', 
        'ATTACHED': 'OPEN',
        'SENT': 'COMPLETE'
    }

    def get_intervals(self, item):
        now = dt.datetime.now(dt.timezone.utc)
        
        return {
            'SINCE_CREATED': self._h(now - item['timeline']['CREATED']) if item['timeline']['CREATED'] is not None else None,
            'SINCE_WAITING': self._h(now - item['timeline']['WAITING']) if item['timeline']['WAITING'] is not None else None,
            'SINCE_REMINDED': self._h(now - item['timeline']['REMINDED']) if item['timeline']['REMINDED'] is not None else None,
            'SINCE_ATTACHED': self._h(now - item['timeline']['ATTACHED']) if item['timeline']['ATTACHED'] is not None else None,
            'SINCE_SENT': self._h(now - item['timeline']['SENT']) if item['timeline']['SENT'] is not None else None
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

        df = pd.read_csv('./rules/reports.csv').set_index('priority')
        df1 = objects.Preferences().to_frame()
        tx = df1.set_index(['component','name']).loc[('REPORTS',),:].value*3600
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

class Report(object):
    schema = Report_Schema()
    data_schema = Report_Schema(exclude=('intervals','current','status'))
    summary_schema = Report_Schema(only=('key','timeline', 'state','document'))
    update_schema= Report_Schema(only=('document','timeline','state','pro_doc','modified'), partial=True)
    
    def __init__(self, key=None, item=None, who=None):
        self._data = Data(org=g.org, dataset='cases/reports')
        self.org = g.org
        if key is None:
            if item is not None:
                datum = {
                    'state': 'NONE',
                    'procedure': item['procedure'],
                    'timeline': {
                        'CREATED' : dt.datetime.now(dt.timezone.utc).isoformat(),
                        'WAITING' : None,
                        'REMINDED' : None,
                        'ATTACHED' : None,
                        'SENT': None
                    }
                }
                tmp = self.schema.load(datum)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
                tmp_json = self.data_schema.dump(tmp)
                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
            else:
                raise ValueError("No report_id provided")
        else:
            self.key = key 
            self.data = self.schema.load(self._data.get(self.key))

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
            
    def action(self, name, item=None, who=None):
        action_map = {
            'waiting': self._waiting,
            'remind': self._remind,
            'attach': self._attach,
            'send' : self._send
        }
        current = self.schema.dump(self.data).get('current')
        if name in current['actions']:
            result = action_map[name](item, who)
            procedure = objects.Procedure(key=self.data['procedure'])
            order = objects.Order(key=procedure.data['order'])
            invoice = objects.Invoice(key=order.data['invoice'])
            invoice.update_state()
            return result
        else:
            raise ValueError(f'Action {name} not allowed')

    def make_send(self):
        email = objects.Email()
        procedure = objects.Procedure(key=self.data['procedure']).details()
        appointment = objects.Appointment(key=procedure['appointment']).details()
        clinic  = objects.Clinic(key=appointment['clinic']).details()
        order = objects.Order(key=procedure['order']).details()
        case = objects.Case(key=order['case']).details()
        # lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
        patient = objects.Patient(key=case['patient']['key']).details()
        doctor = objects.Doctor(key=order['doctor']['key']).details()

        email_info = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': {
					'name': f"{doctor['name']['salutation']} {doctor['name']['display']}",
					'email': doctor['contact']['email']
				},
                'cc':[],
				'subject': f"Clinical Report for {patient['name']['salutation']} {patient['name']['display']}"
			}

        if case['is_LoP']:
            lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
            email_info['cc'].append({
                'name': f"{lawyer['name']['salutation']} {lawyer['name']['display']}",
				'email': lawyer['contact']['email']
            })

        email.set_info(info = email_info)


        email_data = {
            'case': case,
            'order': order,
            'clinic': clinic
        }

        email.set_body(template='mail_report.html', data=email_data, 
                       document=self.data['document'])

        return email

    def make_reminder(self):
        email = objects.Email()
        procedure = objects.Procedure(key=self.data['procedure']).details()
        appointment = objects.Appointment(key=procedure['appointment']).details()
        clinic  = objects.Clinic(key=appointment['clinic']).details()
        order = objects.Order(key=procedure['order']).details()
        case = objects.Case(key=order['case']).details()
        
        patient = objects.Patient(key=case['patient']['key']).details()
        #doctor = objects.Doctor(key=order['doctor']['key']).details()
        email_info = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': {
					'name': f"{clinic['name']}",
					'email': clinic['contact']['email']
				},
				'cc': [
				],
				'subject': f" Report Reminder for {patient['name']['salutation']} {patient['name']['display']}"
			}
        if case['is_LoP']:
            lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
            email_info['cc'].append(					{
                    'name': lawyer['name']['display'],
					'email': lawyer['contact']['email']
                })

        email.set_info(info = email_info)
        email_data = {
            'case': case,
            'order': order,
            'clinic': clinic
        }
        if 'pro_doc' in self.data \
            and self.data['pro_doc'] is not None:
            request_document = self.data['pro_doc']
        else:
            document = objects.Document(item = {
                'doc_type': 'PROCEDURE',
                'ref_type': 'PROCEDURE',
                'ref_key': self.data['procedure']
            })

            doc_data = {
                'procedure': objects.Procedure(key=self.data['procedure']).details(),
                'order': order,
                'case': case,
                'clinic': clinic,
                'org': objects.Organization(key=self.org).details()
            }

            document = document.create(item={'template': 'procedure.html', 'data': doc_data})
            pro_document = document.key
            self.update({
                'pro_doc': pro_document
            })
            request_document = document.key

        email.set_body(template='mail_report_reminder.html', data=email_data, 
                       document=request_document)
        return email

        
            
    def _waiting(self, item=None, who=None):
        if self.data['state'] == 'NONE':
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['WAITING'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'WAITING',
                'timeline': timeline
            })            
        return self.data['state']
        
    def _remind(self, item=None, who=None):
        if self.data['state'] in ['WAITING','REMINDED']:
            try:
                self.make_reminder().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['REMINDED'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'REMINDED',
                    'timeline': timeline
                })
                self.add_log({
                    'ref_type':'REPORT',
                    'ref_key': self.key,
                    'log_type': 'REMINDED',
                    'what': None
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']
    
    def _attach(self, item=None, who=None):
        if self.data['state'] in ['WAITING','REMINDED']:
            print("REPORT ATTACH",flush=True)
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['ATTACHED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'document': item,
                'state': 'ATTACHED',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'REPORT',
                'ref_key': self.key,
                'log_type': 'UPLOADED',
                'what': None
            })
        return self.data['state']

    def _send(self, item=None, who=None):
        if self.data['state'] in ['ATTACHED']:
            try:
                self.make_send().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['SENT'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'SENT',
                    'timeline': timeline
                })
                self.add_log({
                    'ref_type':'REPORT',
                    'ref_key': self.key,
                    'log_type': 'SENT',
                    'what': None
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']
        
    def details(self):
        return self.schema.dump(self.data)

    def add_log(self, item):
        procedure = objects.Procedure(key=self.data['procedure']).details()
        order = objects.Order(key=procedure['order']).details()
        objects.Case(key=order['case']).add_log(item=item)