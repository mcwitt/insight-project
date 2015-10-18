from wtforms import Form, StringField
from wtforms.validators import Required

class InputForm(Form):
    address1 = StringField('address1', [Required()], default='Exploratorium, San Francisco')
    address2 = StringField('address2', [Required()], default='Presidio, San Francisco')
    alpha = StringField('alpha', [Required()], default='5')

