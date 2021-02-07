"""
Collection of functions to perform CRUD operations on a database in the background
"""
import yfinance as yf
import json

#from datetime import datetime
from flask import Flask
import os

from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet)

from types import SimpleNamespace

from tools import unix_to_datetime, yf_flags
#=================================================

def get_symbols_dict(db):
    sec_dict = dict(db.session.query(Security.symbol,Security.id).all())
    return sec_dict

def get_split_event(symbol):
    ticker = yf.Ticker(symbol)
    event = SimpleNamespace(
        symbol       = symbol,
        event_type   = None,
        split_factor = None,
        event_date   = None,
    )
    
    print(f"\nSymbol: {symbol}")
    split_factor = ticker.info.get(yf_flags.FLAG_LAST_SPLIT_FACTOR,None)
    if split_factor is None:
        return event
    
    else:
        factors_split = split_factor.split(':')
        new_amount = int(factors_split[0])
        old_amount = int(factors_split[1])
        if new_amount > old_amount:
            event_type = 'split'
        else:
            event_type = 'reverse_split'
        
        event_date = ticker.info.get(yf_flags.FLAG_LAST_SPLIT_DATE,None)
        event_date = unix_to_datetime(event_date)
        
    event.split_factor = split_factor
    event.event_type   = event_type
    event.event_date   = event_date
    
    #print(event)
    #share_text = 'share' if new_amount 
    #print(f"{old_amount} share turns into {new_amount}")
    return event

def events_table_updater(db):
    sec_dict = get_symbols_dict(db)
    
    for symbol in sec_dict:
        event = get_split_event(symbol)
        if event.event_date is None:
            continue

        #get the security object for that symbol
        SEC_object = db.session.query(Security).filter(Security.symbol==symbol).first()
        symbol_id = SEC_object.id
        #turn simplenamespace event into Database model
        new_event = Event(event.event_type,event.event_date,split_factor=event.split_factor)

        #check if event is already in database (I did this quickly with minimal knowledge of sql. There might be better ways)
        existing_match = db.session.query(Event).filter(Event.event_type == new_event.event_type,
                                                        Event.split_factor == new_event.split_factor,
                                                        Event.symbol_id==symbol_id).first()  # and 
                                                        #Event.event_type == new_event.event_type).first()
        if (existing_match is None) or (existing_match.event_date.date() != new_event.event_date.date()):

            #Check that the event happened after owning the stock
            TRANS_object = Transaction.query.order_by(Transaction.time_execution).filter(Transaction.symbol_id==symbol_id).first()
            if new_event.event_date > TRANS_object.time_execution:
                SEC_object.events.append(new_event)
                db.session.add(new_event)
                print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> ADDED Event \n\t<{new_event}>")
        else:
            print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> Event <{new_event}> already exists in database \n\tor happened before first transaction\n")

    db.session.commit()
    #tickers = yf.Tickers(sec_dict.keys())

if __name__ == '__main__':
    #Here we define a database connection
    project_dir  = os.getcwd()
    database_dir = os.path.join(project_dir, "asset_portfolio.db")
    database_file = f"sqlite:///{database_dir}"

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_file

    db.init_app(app)
    with app.app_context():
        events_table_updater(db)
