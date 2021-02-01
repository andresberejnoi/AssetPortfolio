import os
import datetime 

from flask import Flask
from flask import render_template
from flask import request, url_for, redirect
from flask_bootstrap import Bootstrap

#from flask_sqlalchemy import SQLAlchemy
from models import db
from models import Security, Transaction, Broker, Event
from models import init_tables

from forms import CryptoWalletForm, RegisterBrokerForm
#my own modules here
from command_engine import command_engine

#Here we define a database connection
project_dir  = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(project_dir, "asset_portfolio.db")
database_file = f"sqlite:///{database_dir}"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_file

FAKE_SECRET_KEY = os.urandom(32)    #need secret key for CSRF from WTF-Forms to work
app.config['SECRET_KEY'] = FAKE_SECRET_KEY

Bootstrap(app)
#db = SQLAlchemy(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    #init_tables(db)
    #db.session.commit()

    
#init_tables(db)
#class Symbols(db.Model):

def get_Broker_object(broker_name):
    broker_name = broker_name.strip().lower()   #keep everything lowercase and stripped
    broker = Broker.query.filter(Broker.name==broker_name).first()
    return broker



@app.route("/",methods=['GET','POST'])
def home():
    if request.form:
        #try:
        print(request.form)
        tickers_dict = command_engine(request.form.get('transactions'))  #transactions is how the text input field is called in the html page for this endpoint
        #except:
        #    return "Something went horribly wrong, but I don't know what"
        
        for symbol in tickers_dict:
            SYMBOL_object = Security.query.filter(Security.symbol==symbol).first()     #without .first() the return is a query object
            if SYMBOL_object is None:
                SYMBOL_object = Security(symbol)
                db.session.add(SYMBOL_object)
                db.session.commit()
            print(f"------> {SYMBOL_object}")
            
            trans_events = tickers_dict[symbol]   #gets list of TransactionEvent objects
            for trans in trans_events:
                BROKER_object = get_Broker_object(trans.broker)
                TRANS_object = Transaction(
                    trans.ticker, 
                    trans.amount, 
                    trans.cost_basis, 
                    trans.is_dividend(),
                    #get_broker_id(trans.broker),
                    time_execution=trans.datetime,
                )

                SYMBOL_object.transactions.append(TRANS_object)
                BROKER_object.transactions.append(TRANS_object)
                db.session.add(TRANS_object)

        db.session.commit()
    return render_template("home.html")


@app.route('/wallet_registration',methods=['GET','POST'])
def wallet_registration():
    form = CryptoWalletForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        return redirect(url_for('home'))
    else:
        return render_template('crypto_wallet_registration.html', form=form)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)