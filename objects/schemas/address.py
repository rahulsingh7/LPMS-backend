from marshmallow import Schema, fields, post_load

class AddressSchema(Schema):
    line1 = fields.String(default=None, allow_none=True)
    line2 = fields.String(default=None, allow_none=True)
    city = fields.String(default='', allow_none=True)
    state = fields.String(default='', allow_none=True)
    zipcode = fields.String(default='', allow_none=True)
    summary = fields.Method('summarize_address', dump_only=True)

    def summarize_address(self, address):
        components = {k: address[k] if address[k] is not None else '' for k in ['state', 'zipcode']}
        components['city'] = f"{address['city']}," \
                                if address['city'] is not None else ''\
                                if len(components) > 0 else f"{address['city']}"
        return f"{components['city']} {components['state']} {components['zipcode']}".strip()
