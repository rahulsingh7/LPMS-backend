from ../data/local_data import LocalDictModel 

# admin
users = LocalDictModel('breezemri.com','admin/users.json')
user_cred = LocalDictModel('breezemri.com','admin/user_credentials.json')
organizations = LocalDictModel('breezemri.com','admin/organizations.json')

# entities
patients = LocalDictModel('breezemri.com','entities/patients.json')
lawyers = LocalDictModel('breezemri.com','entities/lawyers.json')
doctors = LocalDictModel('breezemri.com','entities/doctors.json')
custom_procedures_summary = LocalDictModel('breezemri.com','entities/custom_procedure_summary.json')
logs = LocalDictModel('breezemri.com','entities/logs.json')

# master
clinics = LocalDictModel('breezemri.com','master/clinics.json')
procedure_summaries = LocalDictModel('breezemri.com','master/procedure_summaries.json')
procedure_details = LocalDictModel('breezemri.com','master/procedure_details.json')
master_procedures_summary = LocalDictModel('breezemri.com','master/master_procedure_summary.json')
areas = LocalDictModel('breezemri.com','master/master_areas.json')
body_part = LocalDictModel('breezemri.com','master/master_body_parts.json')
base = LocalDictModel('breezemri.com','master/master_base.json')

# cases
cases = LocalDictModel('breezemri.com','cases/cases.json')
orders = LocalDictModel('breezemri.com','cases/orders.json')
procedures = LocalDictModel('breezemri.com','cases/procedures.json')
appointments = LocalDictModel('breezemri.com','cases/appointments.json')
lops = LocalDictModel('breezemri.com','cases/lops.json')
reports = LocalDictModel('breezemri.com','cases/reports.json')
invoices = LocalDictModel('breezemri.com','cases/invoices.json')
## reports
## invoices
documents = LocalDictModel('breezemri.com','cases/documents.json')

