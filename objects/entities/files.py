from flask import send_from_directory, g
from flask import make_response, send_file
import jinja2, pdfkit
import os, glob, uuid
import base64, io

MODE = 'DEVELOPMENT'

if MODE == 'PRODUCTION':
    from weasyprint import HTML
else:
    import pdfkit

class File(object):
    STORE = 'storage'
    TEMPLATES = 'templates/html'
    MIME_TYPES = {
        'txt': 'text/plain', 
        'csv': 'text/csv', 
        'doc': 'applicatio/msword', 
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
        'xls': 'application/vnd.ms-excel', 
        'xlsx': 'application/vnd.ms-excel', 
        'pdf': 'application/pdf'
    }
    ALLOWED_EXTENSIONS = set(MIME_TYPES.keys()) #set(['txt', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'pdf'])
    WKHTMLTOPDF = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
#    WKHTMLTOPDF = '/home/arcvisions/bin/html2pdf'

    PDFKIT_OPTIONS = {
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

    def __init__(self, org, filename=None, item=None):
        self.org =org
        if filename is None and item is None:
            self.filename = None
            self.ext = None
            self.path = None
        elif filename is not None:
            self.filename = filename
            self.ext = self._extension()
            self.path = self._path()
        elif item is not None:
            self.filename = item['filename']
            self.ext = self._extension()
            self.path = self._path()

    def _extension(self):
        return self.filename.rsplit('.', 1)[1].lower()

    def _allowed(self, filename):
        return '.' in filename and \
             self._extension() in self.ALLOWED_EXTENSIONS

    def _path(self):
        return os.path.abspath(os.path.join("./orgs", self.org, self.STORE, self.filename))

    def info(self):
        return {
            'filename': self.filename,
            'ext': self.ext,
        }

    def receive(self, item):
        print("FILE RECIEVE:", item, flush=True)
        self.filename = item.filename
        if item.filename == '':
            raise ValueError(('No file to upload', 204))
        elif not self._allowed(item.filename):
            raise ValueError(('Extension not supported', 409))
        else:
            print('WORKING', flush=True)
            self.filename = item.filename
            self.ext = self._extension()
            key = uuid.uuid1().hex.upper()
            self.filename = f'{key}.{self.ext}'
            self.path = self._path()
            print('PATH:', self.path, flush=True)
            try:
                item.save(self.path)
                return self.info()
            except Exception as e:
                raise ValueError(e)

    def create(self, item):
        print('FILE: CREATE', flush=True)
        template_path = os.path.join("./orgs", self.org, self.TEMPLATES, item['template'])
        print('FILE: TEMPLATE_PATH', template_path, flush=True)
        template = jinja2.Template(open(template_path).read())


        self.ext = 'pdf'
        key = uuid.uuid1().hex.upper()
        self.filename = f'{key}.{self.ext}'
        self.path = self._path()

        print('FILE: FILENAME', self.filename, flush=True)

        try:
            html = template.render(data=item['data'])
        except Exception as e:
            print(e, flush=True)

        print('FILE: RENDERED', html[:100], flush=True)

        try:
            if MODE == 'PRODUCTION':
                HTML(string=html).write_pdf(self.path)
            else:
                config = pdfkit.configuration(wkhtmltopdf=self.WKHTMLTOPDF)
                pdfkit.from_string(html, self.path, 
                                options=self.PDFKIT_OPTIONS, configuration=config)
            return self.info()
        except Exception as e:
            raise ValueError((e, 422))

    def send(self, display):
        file_path = os.path.abspath(f'./orgs/{self.org}/storage/{self.filename}')
        with open(file_path, "rb") as f:
            buffer = base64.encodestring(f.read())
            iobytes = io.BytesIO()
            iobytes.write(buffer)
            iobytes.seek(0)
            mime_type = self.MIME_TYPES[self.ext]
            response = make_response(send_file(iobytes, 
                                               mimetype=mime_type,
                                               attachment_filename=display))
            response.headers['Content-Transfer-Encoding']='base64'
            return response

    def send_file(self, display):
        file_path = os.path.abspath(f'./orgs/{self.org}/storage')
        mime_type = self.MIME_TYPES[self.ext]
        print('SEND:', file_path, self.filename, flush=True)
        return send_from_directory(file_path, self.filename, 
                                    mimetype=mime_type,
                                    attachment_filename=display)

   