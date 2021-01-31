import os
import datetime 

from flask import Flask
from flask import render_template
from flask import request

#from flask_sqlalchemy import SQLAlchemy
from models import db
from models import Security, Transaction, Broker, Event
from models import init_tables
#my own modules here
from command_engine import command_engine

#Here we define a database connection
project_dir  = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(project_dir, "asset_portfolio.db")
database_file = f"sqlite:///{database_dir}"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_file

#db = SQLAlchemy(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    #init_tables(db)
    #db.session.commit()

    
#init_tables(db)
#class Symbols(db.Model):

"""
class Security(db.Model):
    __tablename__ = 'securities'
    
    id           = db.Column(db.Integer,db.Sequence('securities_id_seq'),primary_key=True)
    symbol       = db.Column(db.String(32), nullable=False, unique=True)
    instrument   = db.Column(db.String(64))
    name         = db.Column(db.String(255))
    sector       = db.Column(db.String(255))
    currency     = db.Column(db.String(32))
    transactions = db.relationship('Transaction',backref='securities',lazy=True)
    
    def __init__(self,symbol,instrument='',name='',sector='',currency='USD'):
        self.symbol = symbol

    def __repr__(self):
        return f"Security(ticker={self.symbol}, instrument={self.instrument}, name={self.name}, currency={self.currency})"

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id           = db.Column(db.Integer, db.Sequence('transactions_id_seq'), primary_key=True)
    #symbol_id   = db.Column(db.Integer,       nullable=False)
    symbol_id    = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    #symbol       = db.relationship('Symbol')
    num_shares   = db.Column(db.Numeric(19,9, asdecimal=True),         nullable=False)
    cost_basis   = db.Column(db.Numeric(19,5, asdecimal=True),         nullable=False)
    is_dividend  = db.Column(db.Boolean,                               nullable=True)
    time_created = db.Column(db.DateTime,server_default=db.func.now(), nullable=False)
    time_updated = db.Column(db.DateTime,onupdate=db.func.now(),       nullable=True)
    

    def __init__(self,symbol,num_shares,cost_basis,is_dividend=False):
        self.symbol      = symbol.upper()
        self.num_shares  = num_shares
        self.cost_basis  = cost_basis
        self.is_dividend = is_dividend

    def __repr__(self):
        return f"<Transaction: symbol={self.symbol} num_shares={self.num_shares} cost_basis={self.cost_basis} is_dividend={self.is_dividend}>"
"""

@app.route("/",methods=['GET','POST'])
def home():
    if request.form:
        try:
            print(request.form)
            tickers_dict = command_engine(request.form.get('transactions'))  #transactions is how the text input field is called in the html page for this endpoint
        except:
            return "Something went horribly wrong, but I don't know what"
        
        for symbol in tickers_dict:
            SYMBOL_object = Security.query.filter(Security.symbol==symbol).first()     #without .first() the return is a query object
            if SYMBOL_object is None:
                SYMBOL_object = Security(symbol)
                db.session.add(SYMBOL_object)
                db.session.commit()
            print(f"------> {SYMBOL_object}")
            
            trans_events = tickers_dict[symbol]   #gets list of TransactionEvent objects
            for trans in trans_events:
                TRANS_object = Transaction(
                    trans.ticker, 
                    trans.amount, 
                    trans.cost_basis, 
                    trans.is_dividend()
                )

                SYMBOL_object.transactions.append(TRANS_object)
                db.session.add(TRANS_object)

        db.session.commit()
    return render_template("home.html")

@app.route("/",methods=["GET", "POST"])
def OLD_home():
    if request.form:
        try:
            print(request.form)
            tuples = command_engine(request.form.get("transactions"))   #transactions is how the text input field is called in the html page for this endpoint
        except:
            return "Something went horribly wrong, but I don't know what"
        
        for inst,master_trans_dict in tuples:
            if inst.lower() == 'add':
                for symbol in master_trans_dict:
                    SYMBOL_object = Security.query.filter(Security.symbol==symbol).first()     #without .first() the return is a query object
                    if SYMBOL_object is None:
                        SYMBOL_object = Security(symbol)
                        db.session.add(SYMBOL_object)
                        db.session.commit()
                    print(f"------> {SYMBOL_object}")
                    trans_dict = master_trans_dict[symbol]

                    transactions = trans_dict.get('transactions',None)
                    flags        = trans_dict['flags']
                    for idx,trans in enumerate(transactions):
                        num_shares = trans[0]
                        cost_basis = trans[1]

                        flags_list = flags[idx][1]   #the second element is always a list of flags, such as ['-d','-robinhood', etc]

                        if '-d' in flags_list:
                            is_dividend = True
                        else:
                            is_dividend = False
                        
                        #Create the Transaction Object to insert into the database
                        TRANS_object = Transaction(symbol, num_shares, cost_basis, is_dividend)
                        SYMBOL_object.transactions.append(TRANS_object)
                        db.session.add(TRANS_object)
        
        db.session.commit()



    return render_template("home.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)