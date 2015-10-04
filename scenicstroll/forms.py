from wtforms import Form, StringField, FloatField, RadioField
from wtforms.validators import Required

class InputForm(Form):
    address1 = StringField('address1', [Required()], default='')
    address2 = StringField('address2', [Required()], default='')

