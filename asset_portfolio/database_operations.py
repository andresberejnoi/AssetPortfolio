"""
Collection of functions to perform CRUD operations on a database in the background
"""
import yfinance as yf
import pandas as pd

from flask import Flask
import os

from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet)

from tools import get_symbol_to_id_dict
#=================================================

def events_table_updater(db):
    '''Uses yfinance library to collect split events and stores them in the database'''
    sec_dict = get_symbol_to_id_dict(db)
    
    for symbol in sec_dict:
        events_df = pd.DataFrame(yf.Ticker(symbol).splits)

        if len(events_df) < 1:
            continue
        
        #Retrive security from database to link to event
        SEC_object = db.session.query(Security).filter(Security.symbol==symbol).first()

        for row in events_df.itertuples():
            date         = row.Index   #should be a datetime object
            split_factor = row[1]
            event_type   = 'split'

            #Check that the event is not already in the database
            existing_match = db.session.query(Event).filter(Event.event_type == event_type,
                                                            Event.symbol_id  == sec_dict[symbol],
                                                            Event.event_date == date).first()
            if existing_match is None:
                EVENT_obj = Event(event_type   = event_type,
                                  event_date   = date,
                                  split_factor = split_factor,)
                #link event to security
                SEC_object.events.append(EVENT_obj)
                db.session.add(EVENT_obj)
            
            else:
                print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> Event <{existing_match}> already exists in database \n\tor happened before first transaction\n")

        print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> ADDED Events \n\t<{events_df}>")
    db.session.commit()


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
