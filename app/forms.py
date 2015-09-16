from wtforms import Form, StringField, FloatField, RadioField, validators

class InputForm(Form):
    address = StringField('address', [validators.DataRequired()], default='')
    distance = FloatField('distance', [validators.DataRequired()], default='')
    units = RadioField('units',
        [validators.DataRequired()],
        choices=[('mi', 'miles'), ('km', 'km')], default='mi')
