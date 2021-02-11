from models import Data
from flask import g
import objects
import pandas as pd
import json
from marshmallow import Schema, fields
import datetime as dt


class TimelineSchema(Schema):
    PROCEDURE_CREATED = fields.DateTime(missing=None, allow_none=True)
    SCHEDULED = fields.DateTime(missing=None, allow_none=True)
    REMINDED = fields.DateTime(missing=None, allow_none=True)
    ARRIVED = fields.DateTime(missing=None, allow_none=True)
    CHECKED_IN = fields.DateTime(missing=None, allow_none=True)
    IN_PROGRESS = fields.DateTime(missing=None, allow_none=True)
    DATE = fields.DateTime(required=True)
    COMPLETED = fields.DateTime(missing=None, allow_none=True)

class AppointmentSchema(Schema):
    key = fields.Str()

    clinic = fields.Str(required=True)
    date = fields.Date(required=True)
    time = fields.DateTime(required=True)
    duration = fields.Int(required=True)
    scan_types = fields.Method('generate_scan_types', dump_only=True)

    order = fields.Str(required=True)
    procedures = fields.List(fields.Str(), missing=[], many=True)
    documents = fields.List(fields.Str(),missing=[], many=True, allow_none=True)
    app_doc = fields.Str(missing=None ,allow_none=True)

    state = fields.Str(required=True)
    timeline = fields.Nested(TimelineSchema)

    status = fields.Method('get_status', dump_only=True)
    current = fields.Method('get_current',dump_only=True)
    intervals = fields.Method('get_intervals',dump_only= True)
    created = fields.DateTime()
    modified = fields.DateTime()

  
    _status = {
        'NONE': 'NONE', 
        'SCHEDULED': 'OPEN', 
        'REMINDED': 'OPEN',
        'ARRIVED': 'OPEN',
        'CHECKED_IN': 'OPEN',
        'IN_PROGRESS': 'OPEN', 
        'COMPLETE': 'COMPLETE'
    }

    def generate_scan_types(self, item):
        scan_list = []
        for pkey in item['procedures']:
            procedure = objects.Procedure(key=pkey).data
            scan_list.append(procedure['scan_type'])
        
        scan_freq = {}
        for scan_type in set(scan_list):
            scan_freq[scan_type] = scan_list.count(scan_type)

        return scan_freq
    
    def get_intervals(self,item):
        now = dt.datetime.now(dt.timezone.utc)
        u = {
            'TO_APPOINTMENT': self._h(item['timeline']['DATE'] - now) if item['timeline']['DATE'] is not None else None,
            'SINCE_CREATED': self._h(now - item['timeline']['PROCEDURE_CREATED']) if item['timeline']['PROCEDURE_CREATED'] is not None else None,
            'SINCE_REMINDER': self._h(now - item['timeline']['REMINDED']) if item['timeline']['REMINDED'] is not None else None,
            'SINCE_SCHEDULED': self._h(now - item['timeline']['SCHEDULED']) if item['timeline']['SCHEDULED'] is not None else None
            # 'SINCE_CHECKED_IN': self._h(now - item['timeline']['CHECKED_IN']) if item['timeline']['CHECKED_IN'] is not None else None
            # 'SINCE_IN_PROGRESS': self._h(now - item['timeline']['IN_PROGRESS']) if item['timeline']['IN_PROGRESS'] is not None else None
        }
        return u
    
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
        df = pd.read_csv('./rules/appointments.csv').set_index('priority')
        df1 = objects.Preferences().to_frame()
        tx = df1.set_index(['component','name']).loc[('APPOINTMENTS',),:].value*3600
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
        current_appointment = {
            'actions': actions,
            'status': {
                'status': result.status,
                'criticality': criticality
            }
        }

        lop_key = objects.Order(key=item['order']).data['lop']
        lop_details = objects.LoP(key=lop_key).details()
        lop_state = lop_details['state'] 
        criticality1 = {'NORMAL':0, 'WARNING':0, 'CRITICAL':0}
        df4 = pd.read_csv('./rules/appointments_lop.csv').set_index('priority')
        df4['comparison'] = df4.comparison.fillna('NULL')  
        df5 = df4[df4.state == lop_state]
        df6 = df5.apply(lambda row: self.compare(row, intervals), axis=1)
        df7 = df6[df6].sort_index()
        # print(item, df7, flush=True)
        idx1 = df7.index[0]
        result1 = df4.loc[idx1]
        criticality1[result1.criticality] += 1
        current_lop = {
            'status':{
                'criticality': criticality1
            }
        }

        current = {
            'appointment': current_appointment,
            'lop': current_lop
        }

        return current
    
    
    
    def _h(self, tdelta):
        return 24*3600*tdelta.days + tdelta.seconds


class Appointment(object):
    schema = AppointmentSchema()
    dict_schema = AppointmentSchema(exclude=('scan_types','status','intervals','current'))
#    dict_schema = AppointmentSchema()
    update_schema = AppointmentSchema(only=('state', 'timeline','clinic', 'date', 'time', 'duration','documents', 'app_doc','modified'),
        partial=True)

    def __init__(self, key=None, item=None, who=None):
        self._data = Data(org=g.org, dataset='cases/appointments')
        self.org = g.org
        if key is None:
            if item is not None:
                datum = {
                    'state': 'SCHEDULED',
                    'timeline': {
                        'PROCEDURE_CREATED' : dt.datetime.now(dt.timezone.utc).isoformat(),
                        'SCHEDULED' : dt.datetime.now(dt.timezone.utc).isoformat(),
                        'REMINDED' : None,
                        'DATE' : item['time'],
                        'CHECKED_IN': None,
                        'IN_PROGRESS': None,
                        'COMPLETED' : None
                    },
                }
                item.update(datum)
                tmp = self.schema.load(item)
                tmp['created'] = dt.datetime.now(dt.timezone.utc)
                tmp['modified'] = tmp['created']
                
                tmp_json = self.dict_schema.dump(tmp)
                
                self.data = self.schema.load(self._data.create(tmp_json))

                order = objects.Order(key=self.data['order'])
                invoice = objects.Invoice(order.data['invoice'])
                invoice.update_state()


                self.case = order.data['case']
                self.key = self.data['key']

                for procedure in self.data['procedures']:
                    objects.Procedure(key=procedure).add_appointment(item={'appointment': self.key})

                self.add_log({
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'SCHEDULED',
                    'what': 'appointment sheduled'
                })
                    
            else:
                raise ValueError("No appointment_id provided")
        else:
            self.key = key
            self.data = self.schema.load(self._data.get(self.key))
            self.case = objects.Order(key=self.data['order']).data['case']
            
            
    def update(self, item):
        # data = Data(org=self.org, dataset='cases/appointments')
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


    def add_document(self, key=None, item=None, file=None, who=None):
        if item is not None:
            if item['doc_type'] == 'REGISTRATION':
                document = objects.Document(item=item, file=file) 
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'Registration Form'
                })
            elif item['doc_type'] == 'ATTORNEY_RELEASE':
                document = objects.Document(item=item, file=file)
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'Attorny Release Document'
                })
            elif item['doc_type'] == "CT_FORM":
                document = objects.Document(item=item, file=file)
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'CT Form'
                })
            elif item['doc_type'] == 'MRI_FORM':
                document = objects.Document(item=item, file=file)
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'MRI Form'
                })
            elif item['doc_type'] == 'XRAY_FORM':
                document = objects.Document(item=item, file=file)
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'X-RAY Form'
                })
            elif item['doc_type'] == 'PREGNANCY':
                document = objects.Document(item=item, file=file)
                documents = self.schema.dump(self.data).get('documents')
                documents.append(document.key)
                self.update(item={'documents': documents})
                self.add_log({							   
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'ATTACHED',
                    'what': 'Pregnancy Form'
                })
            
            
            
    def action(self, name, item=None, who=None):
        action_map = {
            'remind': self._remind,
            'reschedule': self._reschedule,
            'start': self._start,
            'arrive': self._arrive,
            'check_in': self._check_in,
            'cancel': self._cancel,
            'complete': self._complete
        }
        current = self.schema.dump(self.data).get('current')
        if name in current['appointment']['actions']:
            order = objects.Order(self.data['order'])
            invoice = objects.Invoice(order.data['invoice'])
            result = action_map[name](item,who)
            invoice.update_state()
            return result
        else:
            raise ValueError(f'Action {name} not allowed')

    def _start(self,item, who):
        if self.data['state'] in ['CHECKED_IN']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['IN_PROGRESS'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'IN_PROGRESS',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'IN_PROGRESS',
                'what': 'appointment in progress'
            })
        return self.data['state']

    def _arrive(self, item, who):
        if self.data['state'] in ['SCHEDULED','REMINDED']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['ARRIVED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'ARRIVED',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'ARRIVED',
                'what': 'patient arrived'
            })
        return self.data['state']

        
    def _check_in(self,item ,who):
        if self.data['state'] in ['ARRIVED']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['CHECKED_IN'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'CHECKED_IN',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'CHECKED_IN',
                'what': 'checked in'
            })
        return self.data['state']
        
    def _reschedule(self, item, who):
        if self.data['state'] in ['SCHEDULED','REMINDED']:
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['SCHEDULED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            timeline['DATE'] = item['time']
            self.update({
                'clinic': item['clinic'],
                'date': item['date'],
                'time': item['time'],
                'duration': item['duration'],
                'state': 'SCHEDULED',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'RESHEDULED',
                'what': 'appointment resheduled'
            })
        return self.data['state']

    def _remind(self, item=None, who=None):
        if self.data['state'] in ['SCHEDULED','REMINDED']:
            try:
                self.make_reminder().send()
                timeline = self.schema.dump(self.data).get('timeline')
                timeline['REMINDED'] = dt.datetime.now(dt.timezone.utc).isoformat()
                self.update({
                    'state': 'REMINDED',
                    'timeline': timeline
                })
                self.add_log({
                    'ref_type':'APPOINTMENT',
                    'ref_key': self.key,
                    'log_type': 'REMINDED',
                    'what': 'appointment reminded'
                })
            except Exception as e:
                print('Email Error:', e, flush=True)
        return self.data['state']

    def _cancel(self, item, who=None):
        if self.data['state'] in ['SCHEDULED','REMINDED','ARRIVED','CHECKED_IN','IN_PROGRESS']:
            for procedure in self.data['procedures']:
                objects.Procedure(key=procedure).remove_appointment()            
            objects.Order(key=self.data['order']).remove_appointment(key=self.key)
            self._data.delete(key=self.key)
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'CANCELLED',
                'what': item['what']
            })


    def _complete(self, item=None, who=None):
        if self.data['state'] in ['SCHEDULED','REMINDED','IN_PROGRESS']:
            if item is not None:
                for procedure in item['incomplete']:
                    if procedure in self.data['procedures']:
                        objects.Procedure(key=procedure).remove_appointment()

            
            for procedure in self.data['procedures']:
                report_key = objects.Procedure(key=procedure).data['report']
                objects.Report(key=report_key).action('waiting')
            timeline = self.schema.dump(self.data).get('timeline')
            timeline['COMPLETED'] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.update({
                'state': 'COMPLETE',
                'timeline': timeline
            })
            self.add_log({
                'ref_type':'APPOINTMENT',
                'ref_key': self.key,
                'log_type': 'COMPLETED',
                'what': 'appointment done'
            })
        return self.data['state']

    # def _complete(self, item=None, who=None):
    #     if self.data['state'] in ['SCHEDULED','REMINDED']:
    #         timeline = self.schema.dump(self.data).get('timeline')
    #         timeline['COMPLETED'] = dt.datetime.now(dt.timezone.utc).isoformat()
    #         self.update({
    #             'state': 'COMPLETED',
    #             'timeline': timeline
    #         })
    #         self.add_log({
    #             'ref_type':'APPOINTMENT',
    #             'ref_key': self.key,
    #             'who': who,
    #             'log_type': 'COMPLETED',
    #             'what': 'appointment done'
    #         })
    #     return self.data['state']
    
    def make_reminder(self):
        email = objects.Email()
        procedure = objects.Procedure(key=self.data['procedures'][0]).details()
        order = objects.Order(key=procedure['order']).details()
        case = objects.Case(key=order['case']).details()
        if case['is_LoP']:
            lawyer = objects.Lawyer(key=case['lawyer']['key']).details()
        else:
            lawyer = None
        patient = objects.Patient(key=case['patient']['key']).details()
        # doctor = objects.Doctor(key=order['doctor']['key']).details()

        email_info = {
            'from': {
                'name': 'Breeze MRI',
                'email': 'orders@breezemri.com'
            },
            'to': {
                'name': f"{patient['name']['salutation']} {patient['name']['display']}",
                'email': patient['contact']['email']
            },
            'cc': [
                {
                    'name': 'Breezi MRI',
                    'email': 'samrat.sengupta@arcvisoins.com'
                }
            ],
            'subject': f"{'Appointment Scheduled for'} {patient['name']['salutation']} {patient['name']['display']}",
        }

        if case['is_LoP']:
            email_info['cc'].append(					{
                    'name': f"{lawyer['name']['salutation']} {lawyer['name']['display']}",
                    'email': lawyer['contact']['email']
                })

        email.set_info(info = email_info)

        email_data = {
            'case': case,
            'order': order,
        }

        
        if 'app_doc' in self.data \
            and self.data['app_doc'] is not None:
            app_document = self.data['app_doc']
        else:
            document = objects.Document(item = {
                'doc_type': 'APPOINTMENT',
                'ref_type': 'APPOINTMENT',
                'ref_key': self.key
            })

            doc_data = {
            'case': case,
            'order': order,
            'org': objects.Organization(key=self.org).data,
            'appointment': self.details(),
            'clinic': objects.Clinic(key=self.data['clinic']).details()
            }

            # print(doc_data, flush=True)

            document = document.create(item={'template': 'appointment.html', 'data': doc_data})
            self.update({
                'app_doc': document.key
            })
            app_document = document.key


        email.set_body(template='mail_appointment.html', data=email_data, 
                       document=app_document)
        return email



    def details(self):
        # print('DUMPING DETAILS', flush=True)
        return self.schema.dump(self.data)

    def add_log(self, item):
        objects.Case(key=self.case).add_log(item=item)
    
    def __repr__(self):
        return f'Appointment({self.key})'

class Appointments:
    schema = AppointmentSchema(many=True)

    def __init__(self):
        self._data = Data(org=g.org, dataset='cases/appointments')
        self.org = g.org
        self.data = self.schema.load(self._data.items())
        
    def details(self):
        # print('PRE-DUMP', flush=True)
        datum = self.schema.dump(self.data)
        # print('POST-DUMP', flush=True)
        for appt in datum:
            documents = []
            for doc in appt['documents']:
                documents.append(objects.Document(key=doc).summary())
            appt['documents'] = documents
        return datum
    
    def to_frame(self):
        # print(pd.DataFrame(self.data).head(), flush=True)
        return pd.DataFrame(self.data)

    def dashboard_func(self):
        df = objects.Appointments().to_frame().set_index('key',drop=False)
        df.index.name = 'index'
        return df
