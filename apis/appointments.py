from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api

import objects as objs
from objects import Appointment, Appointments
from objects import Procedure, Order, Case
from objects import Doctor, Patient
from flask_jwt_extended import jwt_required, get_jwt_identity

appointment_ns = api.namespace("appointment", description="Appointment Related Apis")
 
@appointment_ns.route("/")
class AppointmentNewAPI(Resource):

    @jwt_required
    def post(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        
        try:
            order = objs.Order(key=args['order']).add_appointment(item=args, who=who['user']['key'])
            return objs.Case(key=order['case']).details(), 200
        except Exception as e:
            print(e, flush=True)
            return e.args, 422

    @jwt_required
    def get(self):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        try:
            appointments = Appointments().details()
            items = []
            for appointment in appointments:
                procedures = []
                for pkey in appointment['procedures']:
                    procedures.append(Procedure(key=pkey).summary())
                order = Order(key=procedures[0]['order']).summary()
                case = Case(key=order['case']).summary()

                case['patient'] = Patient(key=case['patient']).summary()
                order['doctor'] = Doctor(key=order['doctor']).summary()

                item = {
                    'appointment': appointment,
                    'procedure': procedures,
                    'order': order,
                    'case': case
                }
                items.append(item)
            return items, 200
        except KeyError:
            return "Appointment does not exist", 404
        except ValueError as e:
            print(e, flush=True)
            return "Validation error", 422  

@appointment_ns.route("/<string:key>")
class AppointmetAPI(Resource):

    @jwt_required
    def put(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            order = objs.Order(key=key).reschedule_appointment(item=args, who=who['user']['key'])
            return Case(key=order['case']).details(), 200
        except Exception as e:
            print(e, flush=True)
    
    @jwt_required
    def delete(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            order = objs.Order(key=key).cancel_appointment(item=args, who=who['user']['key'])
            return Case(key=order['case']).details(), 200
        except KeyError:
            return "Appointment does not exist", 404
        except ValueError:
            return "Validation error", 422  
    
    @jwt_required
    def patch(self, key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            appointment= objs.Appointment(key=key)
            if args['action'] == 'COMPLETE':
                objs.Appointment(key=key).action('complete',who=who['user']['key'])
            elif args['action'] == 'REMIND':
                objs.Appointment(key=key).action('remind',who=who['user']['key'])
            elif args['action'] == 'ARRIVE':
                objs.Appointment(key=key).action('arrive',who=who['user']['key'])
            elif args['action'] == 'CHECK-IN':
                objs.Appointment(key=key).action('check_in',who=who['user']['key'])
            elif args['action'] == 'START':
                objs.Appointment(key=key).action('start',who=who['user']['key'])
            procedure = Procedure(key=appointment.data['procedures'][0])
            order = Order(key=procedure.data['order'])
            return Case(key=order.data['case']).details(), 200
        except KeyError:
            return "Appointment does not exist", 404
        except ValueError:
            return "Validation error", 422
        except Exception as e:
            print('API Error', e, flush=True) 
            return e.args, 406
