from wtforms import (SubmitField, BooleanField, StringField, 
                    PasswordField, validators)
from flask_wtf import FlaskForm

class TransactionsForm(FlaskForm):
    transactions_str = StringField('Enter string here: (i.e. aapl 0.4 200 -t 10:48, msft 0.5 228 -dt 2020-05-30 13:55)',[validators.DataRequired()]) 
    submit = SubmitField('Submit')

class CryptoWalletForm(FlaskForm):
    symbol = StringField('Crypto Currency (i.e. BTC, ETH, XRP, LTC, etc)',[validators.DataRequired()])
    nickname = StringField('Wallet Nickname')
    address = StringField('Public Address',[validators.DataRequired()])
    submit = SubmitField('Submit')

class RegisterBrokerForm(FlaskForm):
    name = StringField('Enter Broker database name (type something short)',[validators.DataRequired()])
    website = StringField("Broker's Website")
    submit = SubmitField('Submit')