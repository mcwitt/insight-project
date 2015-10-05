from wtforms import Form, StringField, IntegerField, RadioField
from wtforms.validators import Required

class InputForm(Form):
    address1 = StringField('address1', [Required()], default='')
    address2 = StringField('address2', [Required()], default='')
    alpha = StringField('alpha', [Required()], default='5')

