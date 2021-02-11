from flask import request, send_from_directory, g
from flask_restplus import Resource, Api
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import api, app
import objects as objs 
from objects import Case, Order, Procedure, Clinic, Patient, Lawyer, Doctor
from objects import Document, LoP, Appointment, Report
from apis.documents import create_document
import datetime as dt
import pytz

#from data import cases, appointments, orders, procedures, documents
from jinja2 import Template
import pdfkit
import os
import uuid

import sendgrid
from sendgrid.helpers.mail import * 
import base64

email_ns = api.namespace("email", description="Email Related Apis")

app.config['DOCUMENTS'] = '../storage'

EMAIL_TYPES = {
	"LOP_REQUEST": ["ORDER_ID"], 
	"APPOINTMENT": ['PROCEDURE_ID'],
	"REPORT": ["PROCEDURE_ID"],
	"INVOICE": ["ORDER_ID"]
}

#########
def email_body(m_type, m_ref):
	app.config['TEMPLATES'] = f'./orgs/{g.org}/templates/html'
	if (m_type == 'LOP_REQUEST'):
		template_name = "mail_lopr.html"

		order = Order(key=m_ref).details()
		case = Case(key=order['case']).details()
		#lawyer = Lawyer(key=case['lawyer']['key']).details()
		#patient = Patient(key=case['patient']['key']).details()

		document = "7D5B9ECCE2A511E984A4645A0434F7BB"
		token = objs.Document(key=document).get_token()
		document_url = f'{request.url_root}document/doc_token/{token}'
		print('TOKEN_URL:', document_url, flush=True)

		template_path = os.path.join(app.config['TEMPLATES'], template_name)
		template = Template(open(template_path).read())

		return template.render(case=case, order=order)

	elif (m_type == 'LOP_REMINDER'):
		template_name = "mail_lop_reminder.html"
		order = Order(key=m_ref).details()
		case = Case(key=order['case']).details()
		lawyer = Lawyer(key=case['lawyer']['key']).details()
		patient = Patient(key=case['patient']['key']).details()
		lop_timeline = order['lop'].get('timeline')

		request_time = dt.datetime.fromisoformat(lop_timeline['REQUESTED'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))\
						  .strftime("%A, %B %d, %Y")
		order['lop']['timeline']['REQUESTED'] = request_time

		order_date = dt.datetime.fromisoformat(order['date'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))\
						  .strftime("%A, %B %d, %Y")
		order['date'] = order_date

		template_path = os.path.join(app.config['TEMPLATES'], template_name)
		template = Template(open(template_path).read())
		return template.render(case=case, order=order)

	elif (m_type == 'APPOINTMENT'):
			template_name = "mail_appointment.html"

			procedure = Procedure(key=m_ref).details()
			order = Order(key=procedure['order']).details()
			case = Case(key=order['case']).details()
			clinic = Clinic(key=procedure['appointment']['clinic']).details()
			appt_time = dt.datetime.fromisoformat(procedure['appointment']['time'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))
			order_date = dt.datetime.fromisoformat(order['date'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))

			data = {
				'clinic': clinic['name'],
				'date': appt_time.strftime("%A, %B %d, %Y"),
				'time':	appt_time.strftime("%I:%M %p %Z"),
				'order_date': order_date.strftime("%B %d, %Y")
			}

			template_path = os.path.join(app.config['TEMPLATES'], template_name)
			template = Template(open(template_path).read())

			return template.render(case=case, order=order, procedure=procedure, data=data)

	elif (m_type == 'REPORT'):
			template_name = "mail_report.html"

			procedure = Procedure(key=m_ref).data
			appointment = Appointment(key=procedure.get('appointment')).data
			clinic = Clinic(key=appointment.get('clinic')).data

			order = Order(key=procedure['order']).details()
			case = Case(key=order['case']).details()

			report = Report(key=procedure['report']).data
			document = Document(key=report['document']).details()
			print(document['key'], flush=True)
			print(appointment['timeline']['DATE'], flush=True)

#			appt_time = dt.datetime.fromisoformat(appointment['timeline']['DATE'])\
#						  .replace(tzinfo=pytz.UTC)\
#						  .astimezone(pytz.timezone("America/Chicago"))
			appt_time = appointment['timeline']['DATE']\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))
			print('APPT_TIME:', appt_time, flush=True)

			order_date = dt.datetime.fromisoformat(order['date'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))
			print('ORDER_DATE:', order_date, flush=True)

			issue_date = dt.datetime.fromisoformat(document['issue_date'])\
						  .replace(tzinfo=pytz.UTC)\
						  .astimezone(pytz.timezone("America/Chicago"))

			data = {
				'clinic': clinic['name'],
				'date': appt_time.strftime("%A, %B %d, %Y"),
				'time':	appt_time.strftime("%I:%M %p %Z"),
				'order_date': order_date.strftime("%B %d, %Y"),
				'issue_date': issue_date.strftime("%B %d, %Y")
			}

			template_path = os.path.join(app.config['TEMPLATES'], template_name)
			template = Template(open(template_path).read())

			return template.render(case=case, order=order, procedure=procedure, data=data)

	elif (m_type == 'INVOICE'):
			template_name = "mail_invoice.html"

			order = Order(key=m_ref).details()
			case = Case(key=order['case']).details()

			template_path = os.path.join(app.config['TEMPLATES'], template_name)
			template = Template(open(template_path).read())

			return template.render(case=case, order=order)

def email_info(m_type, m_ref):
	if (m_type == 'LOP_REQUEST'):

			order = Order(key=m_ref).details()
			case = Case(key=order['case']).details()
			lawyer = Lawyer(key=case['lawyer']['key']).details()
			patient = Patient(key=case['patient']['key']).details()
			#print(patient, flush=True)

			email = {
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
					},
					{
						'name': 'AMSA Associates',
						'email': 'samin@amsaassociates.com'
					}
				],
				'subject': f"{'L.O.P. Request for'} {patient['name']['salutation']} {patient['name']['display']}",
			}
			return email

	if (m_type == 'LOP_REMINDER'):

			order = Order(key=m_ref).details()
			case = Case(key=order['case']).details()
			lawyer = Lawyer(key=case['lawyer']['key']).details()
			patient = Patient(key=case['patient']['key']).details()

			email = {
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
					},
					{
						'name': 'AMSA Associates',
						'email': 'samin@amsaassociates.com'
					}
				],
				'subject': f"{'L.O.P. Reminder for'} {patient['name']['salutation']} {patient['name']['display']}",
			}
			return email

	elif (m_type == 'APPOINTMENT'):

			procedure = Procedure(key=m_ref).details()
			order = Order(key=procedure['order']).details()
			case = Case(key=order['case']).details()
			if case['is_LoP']:
				lawyer = Lawyer(key=case['lawyer']['key']).details()
			else:
				lawyer = None
			patient = Patient(key=case['patient']['key']).details()
			doctor = Doctor(key=order['doctor']['key']).details()

			email = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': {
					'name': f"{patient['name']['salutation']} {patient['name']['display']}",
					'email': patient['contact']['email']
#					'email': 'rahul.singh@arcvisions.com'
				},
				'cc': [
					{
						'name': 'Breezi MRI',
#						'email': 'orders@breezemri.com'
						'email': 'samrat.sengupta@arcvisoins.com'
					}
				],
				'subject': f"{'Appointment Scheduled for'} {patient['name']['salutation']} {patient['name']['display']}",
			}

			if case['is_LoP']:
				email['cc'].append(					{
						'name': f"{lawyer['name']['salutation']} {lawyer['name']['display']}",
						'email': lawyer['contact']['email']
#						'email': 'kaustav.chakraborty@arcvisions.com'
					})

			#print('EMAIL :', email)
			return email

	elif (m_type == 'REPORT'):
			
			procedure = Procedure(key=m_ref).details()
			order = Order(key=procedure['order']).details()
			case = Case(key=order['case']).details()
			lawyer = Lawyer(key=case['lawyer']['key']).details()
			patient = Patient(key=case['patient']['key']).details()
			doctor = Doctor(key=order['doctor']['key']).details()

			email = {
				'from': {
					'name': 'Breeze MRI',
					'email': 'orders@breezemri.com'
				},
				'to': {
					'name': f"{doctor['name']['salutation']} {doctor['name']['display']}",
					'email': doctor['contact']['email']
				},
				'cc': [
#					{
#						'name': f"{patient['name']['salutation']} {patient['name']['display']}",
#						'email': patient['contact']['email']
#					},
					{
						'name': lawyer['name']['display'],
						'email': lawyer['contact']['email']
					},
					{
						'name': 'Breezi MRI',
						'email': 'samin@amsaassociates.com'
					}
				],
				'subject': f"Clinical Report for {patient['name']['salutation']} {patient['name']['display']}"
			}
			return email

	elif (m_type == 'INVOICE'):
			
			order = Order(key=m_ref).details()
			case = Case(key=order['case']).details()
			lawyer = Lawyer(key=case['lawyer']['key']).details()
			patient = Patient(key=case['patient']['key']).details()

			email = {
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
			}
			return email

def email_doc(m_type, m_ref):
	if (m_type == 'LOP_REQUEST'):		
			order = Order(key=m_ref).details()
			print("ORDER:", order)
			if order['documents']['lopr'] is not None:
				return Document(key=order['documents']['lopr']['key']).summary()
			else:
				return create_document(org=g.org, doc_type=m_type, ref_key=m_ref)

	elif (m_type == 'REPORT'):
			procedure = Procedure(key=m_ref).details()
			document = Document(key=procedure['report']).details()
			return document

	elif (m_type == 'INVOICE'):
			order = Order(key=m_ref).details()
			document = Document(key=order['documents']['invoice']).details()
			if document is not None:
				return document
			else:
				return create_document(org=g.org, doc_type=m_type, ref_key=m_ref)
	else:
		return None



@email_ns.route("/body")
class EmailBody(Resource):
	@jwt_required
	def get(self):
		who = get_jwt_identity()
		g.user = who['user']['key']
		g.org = who['org']['key']
	
		email_type = request.args.get('type')
		email_ref = request.args.get('ref')

		try:
			return email_body(email_type, email_ref)
		except Exception as e:
			print(e, flush=True)


@email_ns.route("/info")
class EmailInfo(Resource):
	@jwt_required
	def get(self):
		who = get_jwt_identity()
		g.user = who['user']['key']
		g.org = who['org']['key']
	
		email_type = request.args.get('type')
		email_ref = request.args.get('ref')

		try:
			print(f'type={email_type} & ref={email_ref}', flush=True)

			if (email_type == 'LOP_REQUEST'):
				lop_key = objs.Order(key=email_ref).data['lop']
				email = objs.LoP(key=lop_key).make_request().email()
			elif (email_type == 'LOP_REMINDER'):
				lop_key = objs.Order(key=email_ref).data['lop']
				email = objs.LoP(key=lop_key).make_reminder().email()
			elif (email_type == 'APPOINTMENT'):
				#change the ref key to appointment key
				# app_key = Procedure(key=).data['appointment']
				email = objs.Appointment(key=email_ref).make_reminder().email()
			elif (email_type == 'REPORT'):
				report_key = Procedure(key=email_ref).data['report']
				email = objs.Report(key=report_key).make_send().email()
			elif (email_type == 'REPORT_REMINDER'):
				report_key = Procedure(key=email_ref).data['report']
				email = objs.Report(key=report_key).make_reminder().email()
			elif (email_type == 'INVOICE_REMINDER'):
				invoice_key = objs.Order(key=email_ref).data['invoice']
				email = objs.Invoice(key=invoice_key).make_reminder().email()
			elif (email_type == 'INVOICE'):
				invoice_key = objs.Order(key=email_ref).data['invoice']
				print("EMAIL INVOICE:", invoice_key)
				email = objs.Invoice(key=invoice_key).make_send().email()
			else:
				email = email_info(email_type, email_ref)
				print('INFO')
				print(email, flush=True)
				email['body'] = email_body(email_type, email_ref)
#			print(email, flush=True)
#			email['attachment'] = email_doc(email_type, email_ref)
#			print(email, flush=True)

			return email, 200
		except Exception as e:
			print(e, flush=True)
			return f"Error: {e.args}" , 422

@email_ns.route("/send")
class SendEmail(Resource):

	sg = sendgrid.SendGridAPIClient(api_key='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')
#	'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')
		
	def send(self, items):

		template = email_body(m_type=items['m_type'], m_ref=items['m_ref'])
		email = email_info(m_type=items['m_type'], m_ref=items['m_ref'])

		mail = Mail()
		mail.from_email= Email(email['from']['email'])
		mail.subject = email['subject']

		content = Content("text/html", template)
#		content = Content("text/plain", 'Hi')

		personalization = Personalization()

		personalization.add_to(Email( email['to']['email'] ))

		for cc in email.get('cc', []):
				personalization.add_cc(Email( cc['email'] ))
		
		mail.add_personalization(personalization)
		mail.add_content(content)

		if items['m_type'] not in ["LOP_REMINDER", "APPOINTMENT"]:
			m_attachment = email_doc(m_type=items['m_type'], m_ref=items['m_ref'])
			file_path = 'storage/' + f'{m_attachment["filename"]}'

			with open(file_path, 'rb') as f:
					data = f.read()

			encoded = base64.b64encode(data).decode()
			attachment = Attachment()
			attachment.content = encoded
			attachment.type = "application/pdf"
			attachment.filename = m_attachment['display']
			attachment.disposition = "attachment"
			attachment.content_id = "PDF Document file"
			
			mail.add_attachment(attachment)

		print(mail.get(), flush=True)
		try:
			response = self.sg.client.mail.send.post(request_body=mail.get())
			print(response.status_code, flush=True)
			print(response.body, flush=True)
			print(response.headers, flush=True)
			return response
		except Exception as e:
			print('ERROR:', str(e), flush=True)
	
	@jwt_required
	def post(self):
		who = get_jwt_identity()
		g.user = who['user']['key']
		g.org = who['org']['key']

		args = request.json
		email_type = args['type']
		email_ref = args['ref']

		items = {
			'm_type' : email_type,
			'm_ref' : email_ref
		}
		try:
			#print(items, flush=True)
#			resp = self.send(items=items)
#			print('RESPONSE:', resp, flush=True)

			if (email_type == "LOP_REQUEST"):
				order = Order(key=email_ref)
				objs.LoP(key=order.data['lop']).action('request')
#				order.update_timeline('lop_requested')
#				order.update_status("REQUESTED")
			elif (email_type == 'LOP_REMINDER'):
				print("Email APIS",flush=True)
				order = Order(key=email_ref)
				objs.LoP(key=order.data['lop']).action('remind')
			elif (email_type == "APPOINTMENT"):
				# procedure = objs.Procedure(key=email_ref)
				# app_key = procedure.data['appointment']
				objs.Appointment(key=email_ref).action('remind')
			elif (email_type == "REPORT"):
				report_key = Procedure(key=email_ref).data['report']
				objs.Report(key=report_key).action('send')
			elif (email_type == 'REPORT_REMINDER'):
				print('IN REPORT_REMINDER 1', flush=True)
				report_key = Procedure(key=email_ref).data['report']
				print('IN REPORT_REMINDER 2', flush=True)
				objs.Report(key=report_key).action('remind')
				print('IN REPORT_REMINDER 3', flush=True)
			elif (email_type == "INVOICE_REMINDER"):
				invoice_key = objs.Order(key=email_ref).data['invoice']
				objs.Invoice(key=invoice_key).action('remind')
			elif (email_type == "INVOICE"):
				invoice_key = objs.Order(key=email_ref).data['invoice']
				objs.Invoice(key=invoice_key).action('send')
				pass

			return "Email Sent", 200
		except Exception as e:
			print(e, flush=True)
			return e.args, 422


