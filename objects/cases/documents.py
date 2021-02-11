# import data
from models import Data
from flask import g
from marshmallow import Schema, fields, post_load
from itsdangerous import JSONWebSignatureSerializer
import uuid
import datetime as dt
import time

import objects

#from objects import Case, Order, Procedure
#from objects import Lawyer

DOCUMENT_TYPES = {
    "ORDER": ["ORDER"], 
    "LOP_REQUEST": ["ORDER"], 
    "LOP": ['BLANKET', 'CASE', 'ORDER'],
    "PATIENT_FORM": ["CASE"],
    "REPORT": ["PROCEDURE"],
    "INVOICE": ["ORDER"]
}

_org = None

class DocumentSchema(Schema):
    key = fields.Str(required=True)
    doc_type = fields.Str(required=True)
    issue_date = fields.Date()
    ref_type = fields.Str(required=True)
    ref_key = fields.Str(required=True)
    filename = fields.Str(missing=None)
    ext = fields.Str(missing=None)
    comment = fields.Str()
    modified = fields.DateTime()
    created = fields.DateTime()
    display = fields.Method('display_name', dump_only=True)
    reference = fields.Method('get_reference', dump_only=True)

    def display_name(self, document):
        return f'{document["doc_type"]}_{document["key"]}.{document["ext"]}'

    def get_reference(self, document):
        if document['doc_type'] == 'ORDER':
            if document['ref_type'] == 'ORDER':
                return {'order': objects.Order(key=document['ref_key']).summary()}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == 'LOP_REQUEST':
            if document['ref_type'] == 'ORDER':
                return {'order': objects.Order(key=document['ref_key']).summary()}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == 'LOP':
            if document['ref_type'] == 'BLANKET':
                return {
                    'lawyer': objects.Lawyer(key=document['ref_key']).summary()
                    }
            elif document['ref_type'] == 'CASE':
                case = objects.Case(key=document['ref_key']).details()
                lawyer = objects.Lawyer(key=case['lawyer']['key']).summary()
                return {
                    'case': case,
                    'lawyer': lawyer
                    }
            elif document['ref_type'] == 'ORDER':
                order = objects.Order(key=document['ref_key']).details()
                case = objects.Case(key=order['case']).details()
                lawyer = objects.Lawyer(key=case['lawyer']['key']).summary()
                return {
                    'case': case, 
                    'order': order,
                    'lawyer': lawyer
                    }
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == 'PATIENT_FORM':
            if document['ref_type'] == 'CASE':
                return {'case': objects.Case(key=document['ref_key']).summary()}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == "REPORT":
            if document['ref_type'] == 'PROCEDURE':
                procedure = objects.Procedure(key=document['ref_key']).summary() 
                order = objects.Order(key=procedure['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order, 'procedure': procedure}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == "INVOICE":
            if document['ref_type'] == 'ORDER':
                order = objects.Order(key=document['ref_key']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order}
        elif document['doc_type'] == "REGISTRATION":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
        elif document['doc_type'] == "ATTORNEY_RELEASE":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
        elif document['doc_type'] == "CT_FORM":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
        elif document['doc_type'] == "MRI_FORM":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
        elif document['doc_type'] == "XRAY_FORM":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
        elif document['doc_type'] == "PREGNANCY":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                order = objects.Order(key=appointment['order']).summary()
                case = objects.Case(key=order['case']).summary()
                return {'case': case, 'order': order,'appointment':appointment}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == "APPOINTMENT":
            if document['ref_type'] == "APPOINTMENT":
                appointment = objects.Appointment(key=document['ref_key']).details()
                return {'appointment':appointment}
            else:
                raise ValueError('Reference Type not recognized')
        elif document['doc_type'] == "PROCEDURE":
            if document['ref_type'] == "PROCEDURE":
                procedure = objects.Procedure(key=document['ref_key']).details()
                return {'procrdure':procedure}
            else:
                raise ValueError('Reference Type not recognized')            
        else:
            raise ValueError("Document Type not recognized")


class Document(object):
    schema = DocumentSchema()
    storage_schema = DocumentSchema(exclude=('reference','display'))
    summary_schema = DocumentSchema(only=('key', 'doc_type', 'issue_date', 'ref_type', 
                                          'ref_key','filename', 'display'))
    update_schema = DocumentSchema(only=('filename','ext','modified'), partial=True)
    
    def __init__(self, key=None, item=None, file=None, token=None):
        if token is None:
            self._data = Data(org=g.org, dataset='cases/documents')
            self.org = g.org
            if key is None:
                if item is not None:
                    if file is not None:
                        file_details = objects.File(org=self.org).receive(file)
                        item['filename'] = file_details['filename']
                        item['ext'] = file_details['ext']
                        print("DOCUMENT INIT",flush=True)
                        self.file = objects.File(org=self.org, filename=item['filename'])
                    else:
                        self.file = objects.File(org=self.org)

                    tmp = self.schema.load(item, partial=True)
                    tmp['created'] = dt.datetime.utcnow()
                    tmp['modified'] = tmp['created']
                    
                    tmp_json = self.storage_schema.dump(tmp)

                    self.data = self.schema.load(self._data.create(tmp_json))
                    self.key = self.data['key']
                    print("DOCUMENT INIT DONE",flush=True)
                else:
                    raise ValueError("No document provided")
            else:
                self.key = key
                self.data = self.schema.load(self._data.get(self.key))
                if self.data['filename'] is not None:
                    self.file = objects.File(org=self.org, filename=self.data['filename'])
                else:
                    self.file = objects.File(org=self.org)
        else:
            s = JSONWebSignatureSerializer('secret-key')
            _token = bytes(token, 'utf-8')
            _item = s.loads(_token)
            self.org = _item['org']
            self.key = _item['key']
            self._data = Data(org=self.org, dataset='cases/documents')
            self.data = self.schema.load(self._data.get(self.key))
            print('FILE:', self.org, self.key, self.data['filename'])
            if self.data['filename'] is not None:
                self.file = objects.File(org=self.org, filename=self.data['filename'])
            else:
                self.file = objects.File(org=self.org)


    def update(self, item):
        # data = Data(org=self.org, dataset='cases/documents')
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


    def details(self):
        return self.schema.dump(self.data)

    def summary(self):
        return self.summary_schema.dump(self.data)

    def send(self):
        return self.file.send(display=self.summary().get('display'))

    def send_file(self):
        return self.file.send_file(display=self.summary().get('display'))

    def get_token(self):
        s = JSONWebSignatureSerializer('secret-key')
        url = s.dumps({'org': self.org, 'key': self.key})
        return url.decode('utf-8')

    def create(self, item):
        print('DOC CREATE:', item.keys(), flush=True)
        info = self.file.create(item=item)
        self.update({
            'filename': info['filename'],
            'ext': info['ext']            
        })
        return self

class Documents:
    schema = DocumentSchema(many=True)
    summary_schema = DocumentSchema(only=('key', 'doc_type', 'issue_date', 'ref_type', 
                                          'reference', 'filename', 'display'), many=True)

    def __init__(self, query=None):
        self._data = Data(org=g.org, dataset='cases/documents')
        if query is not None:
            self.data = self.schema.load(self._data.query(filters=query)[0])
        else:
            self.data = self.schema.load(self._data.items())

    def details(self):
        return self.summary_schema.dump(self.data)
