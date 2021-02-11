from marshmallow import Schema, fields, post_load

class NameSchema(Schema):
    salutation = fields.String(required=True)
    first = fields.String(required=True)
    middle = fields.String(default=None, allow_none=True)
    last = fields.String(required=True)
    suffix = fields.String(default=None, allow_none=True)
    middle_initial = fields.Method('abbreviate_middle', dump_only=True)
    display = fields.Method('build_display_name', dump_only=True)

    def abbreviate_middle(self, name):
        if name is not None and name['middle'] is not None:
            return name['middle'][0].upper() + '.'
        else:
            return None

    def build_display_name(self, name):
        if name['middle'] is not None:
            display_name = f"{name['first']} {self.abbreviate_middle(name)} {name['last']}"
        else:
            display_name = f"{name['first']} {name['last']}"
        if name['suffix'] is not None:
            display_name = f"{display_name}, {name['suffix']}"
        return display_name
