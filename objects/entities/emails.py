from flask import request, g
import objects as objs
import sendgrid
import sendgrid.helpers.mail as sgmail
import base64, os
from jinja2 import Template

class Email(object):
    STORE = 'storage'
    TEMPLATES = 'templates/html'
    unsafe_endpoint = 'http://'
    sg = sendgrid.SendGridAPIClient(api_key='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')

    def __init__(self):
        self.org = g.org
        self.info = {
            'from': {},
            'to': {},
            'cc': [],
            'subject': None,
        }
        self.body = None
        self.attachment = None

    def set_info(self, info):
        for key in info:
            if key in self.info and info[key] is not None:
                self.info[key] = info[key]

    def set_body(self, template, data, document=None):
        if document is not None:
            token = objs.Document(key=document).get_token()
            document_url = f'{request.url_root}document/doc_token/{token}'
            data['document_url'] = document_url
        token = objs.Image(filename='image001.png').get_token()
        data['logo_url'] = f'{request.url_root}document/img_token/{token}'
        t_root = f'orgs/{self.org}/{self.TEMPLATES}'
        template_path = os.path.join(t_root, template)
        template = Template(open(template_path).read())

        self.body = template.render(data=data)

#    def set_attachment(self, document):
#        self.attachment = document

    def email(self):
        email = self.info
        email['body'] = self.body
        return email

    def send(self):
        mail = sgmail.Mail()
        mail.from_email= sgmail.Email(self.info['from']['email'])
        mail.subject = self.info['subject']

        personalization = sgmail.Personalization()
        personalization.add_to(sgmail.Email(self.info['to']['email'] ))

        for cc in self.info.get('cc', []):
            personalization.add_cc(sgmail.Email(cc['email']))

        mail.add_personalization(personalization)

        content = sgmail.Content("text/html", self.body)
        mail.add_content(content)
        try:
            response = self.sg.client.mail.send.post(request_body=mail.get())
            print(response.status_code, flush=True)
            return response
        except Exception as e:
            print('ERROR:', str(e), flush=True)

#        if self.attachment is not None:
#            filename = objs.Document(key=self.attchment).details().get('filename')
#            file = File(filename=filename)