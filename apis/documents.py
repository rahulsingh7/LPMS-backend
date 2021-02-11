from flask import request, send_file, send_from_directory, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restplus import Resource, Api
from . import api, app
from jinja2 import Template
import pdfkit
import os
import uuid
import datetime as dt
import pytz
from objects import Document, Documents, Order, Case, Procedure, Patient, Image
import objects

document_ns = api.namespace("document", description="Document Related Apis")

#UPLOAD_FOLDER = 'E:/ArcVisions/backend/documents'
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'pdf'])
app.config['DOCUMENTS'] = '/storage'
app.config['IMAGES'] = '/storage'
app.config['TEMPLATES'] = '/templates/html'

@document_ns.route("/")
class DocumentUpload(Resource):
    @jwt_required
    def post(self):
        args = request.form.to_dict()
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        
        if 'file' not in request.files:
            return 'No file to upload', 204
        else:
            file = request.files['file']
            if file.filename == '': 
                return 'No file to upload', 204
            else:
                try:
                    if args['doc_type'] == 'ORDER':
                        objects.Order(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'REGISTRATION':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'ATTORNEY_RELEASE':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'CT_FORM':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'MRI_FORM':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'XRAY_FORM':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'PREGNANCY':
                        objects.Appointment(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    elif args['doc_type'] == 'LOP':
                        if args['ref_type'] == 'BLANKET':
                            objects.Document(item=args, file=file)
                        elif args['ref_type'] in ['CASE','ORDER']:
                            objects.Order(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                        else:
                            return 'Unknown reference type', 422
                    elif args['doc_type'] == 'REPORT':
                        objects.Procedure(key=args['ref_key']).add_document(item=args, file=file, who= who['user']['key'])
                    return 'File Uploaded', 200
                except KeyError as e:
                    return e.args, 404
                except ValueError as e:
                    return e.args, 422
                except Exception as e:
                    return e.args, 406

@document_ns.route("/add")
class DocumentLop(Resource):
    @jwt_required
    def post(self):
        args = request.json
        who =  get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            objects.Order(key=args['order']).add_document(key=args['key'], item=args, who= who['user']['key'])
            return 'Document attached', 201
        except KeyError as e:
            return f'KeyError: {e.args}', 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            return e.args, 406


@document_ns.route("/doc/<string:key>")
class DocumentView(Resource):
    @jwt_required
    def get(self, key):
        try:
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key']
            return Document(key=key).send()
        except KeyError as e:
            return e.args, 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            print(e, flush=True)
            return e.args, 406

@document_ns.route("/doc_token/<string:token>")
class DocumentDownload(Resource):
    def get(self, token):
        try:
            print('TOKEN:', token, flush=True)
            return Document(token=token).send_file() 
        except KeyError as e:
            return e.args, 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            print(e, flush=True)
            return e.args, 406

@document_ns.route("/token/<string:key>")
class DocumentToken(Resource):
    @jwt_required
    def get(self, key):
        try:
            who = get_jwt_identity()
            g.user = who['user']['key']
            g.org = who['org']['key']
            return Document(key=key).get_token(), 200
        except KeyError as e:
            return e.args, 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            print(e, flush=True)
            return e.args, 406

@document_ns.route("/img/<string:filename>")
class ImageView(Resource):
    @jwt_required
    def get(self, filename):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            return Image(filename=filename).send_img()
        except Exception as e:
            print(e, flush=True)

            
@document_ns.route("/img_token/<string:token>")
class ImageToken(Resource):
    def get(self, token):
        try:
            print('TOKEN:', token, flush=True)
            return Image(token=token).send_img() 
        except KeyError as e:
            return e.args, 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            print(e, flush=True)
            return e.args, 406

@document_ns.route("/info/<string:key>")
class DocumentInfo(Resource):
    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        return Document(key=key).details(), 200

@document_ns.route("/summary/<string:key>")
class DocumentSummary(Resource):
    @jwt_required
    def get(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        return Document(key=key).summary(), 200

@document_ns.route("/summary")
class DocumentSummaries(Resource):
    @jwt_required
    def get(self):
        args = request.args.to_dict()
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']

        if args is not None:
            return Documents(query=args).details(), 200
        else:
            return Documents().details(), 200


def create_document(doc_type, ref_key, org):
        item = {}
        item['doc_type'] = doc_type
        item['ref_type'] = "ORDER"
        item['ref_key'] = ref_key
        

        order = Order(key=item['ref_key']).details()
        case = Case(key=order['case']).details()

        #print("CASE: ", case, flush=True)
        #print("ORDER: ", order, flush=True)

        if (doc_type == 'LOP_REQUEST'):
            template_name = "lopr.html"
            data = {'case': case, 'order': order, 'procedure': ''}
        elif (doc_type == 'INVOICE'):
            template_name = "invoice.html"

            invoice_date = dt.datetime.utcnow()\
                            .replace(tzinfo=pytz.UTC)\
                            .astimezone(pytz.timezone("America/Chicago"))
            #print('DATE:', invoice_date.strftime("%B %d, %Y"))

            total_charge = 0
            for procedure in order['procedures']:
                if 'charge' in procedure and procedure['charge'] is not None:
                    total_charge += float(procedure['charge'])
                else:
                    procedure['charge'] = procedure['rate']
                procedure['adj'] = float(procedure['charge']) - float(procedure['rate'])

            patient = Patient(key=case['patient']['key']).details()

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

            data = {
                'case': case, 
                'order': order, 
                'date': invoice_date.strftime("%B %d, %Y"),
                'total': total_charge,
                'patient': patient,
                'chart': chart
            }
        else:
            raise ValueError("Invalid document type")
            

        template_path = os.path.join("./orgs", org, app.config['TEMPLATES'], template_name)
        template = Template(open(template_path).read())

        config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
        file_id = uuid.uuid1().hex.upper()
        file_name = f'{file_id}.pdf'
        file_path = os.path.abspath(os.path.join("./orgs", org, app.config['DOCUMENTS'], file_name))

        item['key'] = file_id
        item['filename'] = file_name
        item['ext'] = 'pdf'

        info = Document(item=item).summary()

        file_path = f"org/{org}/storage/{item['filename']}"
        #print(data, flush=True)

        options = {
         'dpi': 300,
         'page-size': 'Letter',
         'margin-top': '0.25in',
         'margin-right': '0.25in',
         'margin-bottom': '0.25in',
         'margin-left': '0.25in',
         'encoding': "UTF-8",
         'custom-header' : [
            ('Accept-Encoding', 'gzip')
         ],
         'no-outline': None,
         'viewport-size': '1280x1024',
         'orientation': 'Portrait'
        }

        if (doc_type == 'LOP_REQUEST'):
            pdfkit.from_string(template.render(case=data['case'], order=data['order']), file_path, 
                            options=options, configuration=config)
        elif (doc_type == 'INVOICE'):
            extra = {
                'date': data['date'],
                'total': data['total'],
                'chart': data['chart'],
                'patient': data['patient']
            }
            pdfkit.from_string(template.render(case=data['case'], order=data['order'], 
                                               data=extra), 
                            file_path, options=options, configuration=config)
        Order(key=item['ref_key']).add_document(info)

        #print(Order(key=item['ref_key']).details(), flush=True)
        return info


@document_ns.route("/create")
class DocumentCreate(Resource):
    @jwt_required
    def post(self):
        args = request.json
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            if args['doc_type'] in ['LOP_REQUEST','INVOICE']:
                    document = Order(key=args['ref_key']).add_document(item=args)
                    return document.send()
            else:
                return f'Document type {args["doc_type"]} not recognized', 422
        except KeyError as e:
            return e.args, 404
        except ValueError as e:
            return e.args, 422
        except Exception as e:
            return e.args, 406


# @document_ns.route("/create")
# class DocumentCreate(Resource):
#     @jwt_required
#     def post(self):
#         who = get_jwt_identity()
#         args = request.json
#         file_path = f'org/{who['org']['key']}/storage/'
#         info = create_document(args['doc_type'], args['ref_key'], who['org']['key'])
#         return send_from_directory(file_path,
#                         info['filename'], attachment_filename=info['display'], 
#                         as_attachment=False)




