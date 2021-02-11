import json
from models import Data
from flask import g
import objects
from marshmallow import Schema, fields
import datetime as dt
import pandas as pd
import pytz

_org = None

class DocumentSchema(Schema):
    request = fields.Str(missing=None)
    letter = fields.Str(missing=None)

class TimelineSchema(Schema):
    CREATED = fields.DateTime(missing=None)
    REQUESTED = fields.DateTime(missing=None)
    REMINDED = fields.DateTime(missing=None)
    ATTACHED = fields.DateTime(missing=None)


class LOP_Schema(Schema):
    key = fields.Str()
    order = fields.Str()
    timeline = fields.Nested(TimelineSchema)
    state = fields.Str(required=True)
    documents = fields.Nested(DocumentSchema)
    modified = fields.DateTime()
    created = fields.DateTime()
    status = fields.Method('get_status', dump_only=True)
    intervals = fields.Method('get_intervals', dump_only=True)
    current = fields.Method('get_current', dump_only=True)


    _status = {
        'NONE': 'OPEN', 
        'REQUESTED': 'OPEN', 
        'REMINDED': 'OPEN', 
        'ATTACHED': 'COMPLETE',
        'UNREQUIRED': 'UNREQUIRED'
    }

    def get_intervals(self, item):
        now = dt.datetime.now(dt.timezone.utc)
        
        return {
            'SINCE_CREATED': self._h(now - item['timeline']['CREATED']) if item['timeline']['CREATED'] is not None else None,
            'SINCE_REQUESTED': self._h(now - item['timeline']['REQUESTED']) if item['timeline']['REQUESTED'] is not None else None,
            'SINCE_REMINDED': self._h(now - item['timeline']['REMINDED']) if item['timeline']['REMINDED'] is not None else None,
            'SINCE_ATTACHED': self._h(now - item['timeline']['ATTACHED']) if item['timeline']['ATTACHED'] is not None else None
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

        df = pd.read_csv('./rules/lop.csv').set_index('priority')
        df1 = objects.Preferences().to_frame()
        tx = df1.set_index(['component','name']).loc[('LOP',),:].value*3600
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

class LoP(object):
    schema = LOP_Schema()
    data_schema = LOP_Schema(exclude=('intervals','current','status'))
    summary_schema = LOP_Schema(only=('key','timeline', 'state','documents'))
    update_schema= LOP_Schema(only=('documents','timeline','state','modified'), partial=True)
    
    def __init__(self, key=None, item=None, who=None):
        self._data= Data(org=g.org, dataset='cases/lops')
        self.org = g.org
        if key is None:
            if item is not None:
                datum = {
                    'state': 'NONE' if item['is_LoP'] else 'UNREQUIRED',
                    'order': item['order'],
                    'timeline': {
                        'CREATED' : dt.datetime.now(dt.timezone.utc).isoformat(),
                        'REQUESTED' : None,
                        'REMINDED' : None,
                        'ATTACHED' : None
                    },
                    'documents': {
                        'request': None,
                        'letter': None
                    }
                }
                tmp = self.schema.load(datum)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
                tmp_json = self.data_schema.dump(tmp)
                self.data = self.schema.load(self._data.create(tmp_json))
                self.key = self.data['key']
            else:
                raise ValueError("No lop_id provided")
        else:
            self.key = key 
            self.data = self.schema.load(self._data.get(self.key))

    def update(self, item):
        # data= Data(org=self.org, dataset='cases/lops')
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

    def update_request(self, key):
        documents = self.schema.dump(self.data).get('documents')
        documents['request'] = key
        self.update({'documents': documents})
            
    def action(self, name, item=None, who=None):
        print("ACTIONS",name,flush=True)
        action_map = {
            'request': self._request,
            'remind': self._remind,
            'attach': self._attach
        }
        current = self.schema.dump(self.data).get('current')
        if name in current['actions']:
            return action_map[name](item, who)
        else:
            raise ValueError(f'Action {name} not allowed')

    def make_request(self):
        email = objects.Email()
        order = objects.Order(key=self.data['order']).details()
        case = objects.Case(key=order['case']).details()
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
                    'name': 'Breezi MRI',
                    'email': 'samrat.sengupta@arcvisions.com'
                }
            ],
            'subject': f"{'L.O.P. Request for'} {patient['name']['salutation']} {patient['name']['display']}",
        })

        email_data = {
            'case': case,
            'order': order
        }

        if 'documents' in self.data \
            and 'request' in self.data['documents'] \
            and self.data['documents']['request'] is not None:
            request_document = self.data['documents']['request']
        else:
            print('LOP: MAKE_REQUEST[DOC]')
            document = objects.Document(item = {
                'doc_type': 'LOP_REQUEST',
                'ref_type': 'ORDER',
                'ref_key': self.data['order']
            })

            doc_data = {
                'order': objects.Order(key=self.data['order']).details(),
                'case': objects.Case(key=order['case']).details()
            }

            document = document.create(item={'template': 'lopr.html', 'data': doc_data})
            lop_documents = self.data.get('documents')
            lop_documents['request'] = document.key
            self.update({
                'documents': lop_documents
            })
            request_document = document.key
            print('LOP: MAKE_REQUEST[DOC]')

        email.set_body(template='mail_lopr.html', data=email_data, 
                       document=request_document)
        return email

    def make_reminder(self):
        email = objects.Email()
        order = objects.Order(key=self.data['order']).details()
        case = objects.Case(key=order['case']).details()
        lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
        patient = objects.Patient(key=case['patient']['key']).details()
        lop_timeline = self.data['timeline']
        request_time = lop_timeline['REQUESTED']\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))\
						  .strftime("%A, %B %d, %Y")
        order['lop']['timeline']['REQUESTED'] = request_time

        order_date = dt.datetime.fromisoformat(order['date'])\
                            .replace(tzinfo=pytz.UTC)\
                            .astimezone(pytz.timezone("America/Chicago"))\
                            .strftime("%A, %B %d, %Y")

        order['date'] = order_date
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
						'name': 'Breezi MRI',
						'email': 'samrat.sengupta@arcvisions.com'
					}
				],
				'subject': f"{'L.O.P. Reminder for'} {patient['name']['salutation']} {patient['name']['display']}",
			})

        email_data = {
            'case': case,
            'order': order
        }

        email.set_body(template='mail_lop_reminder.html', data=email_data, 
                       document=self.data['documents']['request'])
        return email

            
    def _request(self, item=None, who=None):
        if self.data['state'] == 'NONE':
            try:
                self.make_request().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['REQUESTED'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'REQUESTED',
                    'timeline': timeline
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']
        
    def _attach(self, item, who=None):
        if self.data['state'] in ['NONE','REQUESTED','REMINDED']:
            datum = self.schema.dump(self.data)
            timeline = datum.get('timeline')
            timeline['ATTACHED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            documents = datum.get('documents')
            documents['letter'] = item
            self.update({
                'documents': documents,
                'state': 'ATTACHED',
                'timeline': timeline
            })
        return self.data['state']

    def _remind(self, item=None, who=None):
        print("REMINDER",flush = True)
        if self.data['state'] in ['REQUESTED','REMINDED']:
            try:
                print("SENDING......",flush = True)
                self.make_reminder().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['REMINDED'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'REMINDED',
                    'timeline': timeline
                })
            except Exception as e:
                print('Email Error:', e, flush=True)   
        return self.data['state']
    
    def details(self):
        return self.schema.dump(self.data)
