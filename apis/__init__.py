from flask import Flask, flash, request, redirect
from flask_jwt_extended import JWTManager
from flask_restplus import Api
from flask_cors import CORS
# from documents import UPLOAD_FOLDER

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'Racoons & Internationals'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400
jwt = JWTManager(app)
#UPLOAD_FOLDER = '../documents'
#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

api = Api(app)

@jwt.user_claims_loader
def add_claims_to_access_token(response):
    return {'roles': {
        'org': response['org']['category'],
        'user': response['user']['role']
        },
    'org': response['user']['org']
    }


# admin
from .users import user_ns
from .preferences import preference_ns
from .organizations import org_ns
# entities
from .lawyers import lawyer_ns
from .doctors import doctor_ns
from .patients import patient_ns
# master
from .clinics import clinic_ns
#from .procedure_summaries import master_ns
from .master_procedures import master_ns
from .custom_procedures import custom_ns		
# cases 
from .cases import case_ns
from .orders import order_ns
from .procedures import procedure_ns					  
from .appointments import appointment_ns
from .invoice import invoice_ns

from .documents import document_ns
from .emails import email_ns
from .logs import log_ns


from .dashboard import dashboard_ns
