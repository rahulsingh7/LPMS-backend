from flask import send_from_directory, g
from flask import make_response, send_file
from itsdangerous import JSONWebSignatureSerializer
import jinja2, pdfkit
import os, glob, uuid
import base64, io

class Image(object):
    STORE = 'storage'
    MIME_TYPES = {
        'png': 'image/png', 
        'jpg': 'image/jpg', 
        'jpeg': 'image/jpeg'
    }
    ALLOWED_EXTENSIONS = set(MIME_TYPES.keys())
    def __init__(self, filename=None, item=None, token=None):
        if token is None:
            self.org = g.org
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
        else:
            s = JSONWebSignatureSerializer('secret-key')
            _token = bytes(token, 'utf-8')
            _item = s.loads(_token)
            self.org = _item['org']
            self.filename = _item['filename']
            self.ext = self._extension()
            self.path = self._path()

    def _path(self):
        return os.path.abspath(os.path.join("./orgs", self.org, self.STORE, self.filename))

    def _extension(self):
        return self.filename.rsplit('.', 1)[1].lower()

    def _allowed(self, filename):
        return '.' in filename and \
             self._extension() in self.ALLOWED_EXTENSIONS

    def get_token(self):
        s = JSONWebSignatureSerializer('secret-key')
        url = s.dumps({'org': self.org, 'filename': self.filename})
        return url.decode('utf-8')

   
    def send_file(self, display):
        file_path = os.path.abspath(f'./orgs/{self.org}/storage')
        mime_type = self.MIME_TYPES[self.ext]
        print('SEND:', file_path, self.filename, flush=True)
        return send_from_directory(file_path, self.filename, 
                                    mimetype=mime_type,
                                    attachment_filename=display)


    def send_img(self):
        return self.send_file(display=self.filename)
