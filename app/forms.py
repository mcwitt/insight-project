from wtforms import Form, StringField, FloatField, RadioField, validators

class InputForm(Form):
    address1 = StringField('address1', [validators.DataRequired()], default='')
    address2 = StringField('address2', [validators.DataRequired()], default='')
#    units = RadioField('units',
#        [validators.DataRequired()],
#        choices=[('mi', 'miles'), ('km', 'km')], default='mi')
