from wtforms import (SubmitField, BooleanField, StringField, 
                    PasswordField, validators)
from flask_wtf import Form

class TransactionsForm(Form):
    pass 

class CryptoWalletForm(Form):
    crypto = StringField('Crypto Currency (i.e. BTC, ETH, XRP, LTC, etc)',[validators.DataRequired()])
    nickname = StringField('Wallet Nickname')
    address = StringField('Public Address',[validators.DataRequired()])
    submit = SubmitField('Submit')

class RegisterBrokerForm(Form):
    name = StringField('Enter Broker database name (type something short)',[validators.DataRequired()])
    website = StringField("Broker's Website")
    submit = SubmitField('Submit')