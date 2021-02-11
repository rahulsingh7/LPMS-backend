from flask_restplus import Resource, Api, reqparse
from flask import request, g
from . import api

import objects as objs
from flask_jwt_extended import jwt_required, get_jwt_identity

invoice_ns = api.namespace("invoice", description="Appointment Related Apis")
 
@invoice_ns.route("/<string:key>/update_charge")
class InvoiceAPI(Resource):
    @jwt_required
    def put(self,key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            invoice = objs.Invoice(key=key).update_charge(line_items=args)
            order = objs.Order(key=invoice['order']).details()
            return objs.Case(key=order['case']).details(), 200
        except Exception as e:
            print(e, flush=True)
            return e.args, 422

@invoice_ns.route("/<string:key>/action")
class InvoicePaid(Resource):
    @jwt_required
    def patch(self,key):
        who = get_jwt_identity()
        g.user = who['user']['key']
        g.org = who['org']['key']
        args = request.json
        try:
            if args['action'] == 'COMPLETE':
                invoice = objs.Invoice(key=key).action('complete')
                order = objs.Order(key=invoice['order']).details()
                return objs.Case(key=order['case']).details(), 200
        except Exception as e:
            print(e, flush=True)
            return e.args, 422
