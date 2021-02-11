from marshmallow import Schema, fields, post_load

class ContactSchema(Schema):
    phone = fields.String(required=True)
    alt_phone = fields.String(default=None, allow_none=True)
    fax = fields.String(default=None, allow_none=True)
    email = fields.Email(default=None, allow_none=True)
    preferred = fields.String(required=True)
    action = fields.Method('map_action', dump_only=True)

    def map_action(self, contact):
        if contact['preferred'] == "phone":
            return "Call"
        elif contact['preferred'] == "email":
            return "E-Mail"
        elif contact['preferred'] == "fax":
            return "Fax"
