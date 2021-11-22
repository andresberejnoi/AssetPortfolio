"""
Collection of functions to perform CRUD operations on a database in the background
"""
import yfinance as yf
import pandas as pd

from flask import Flask
import os
import sys

from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet, Dividend)

from tools import get_symbol_to_id_dict, webscrape_tipranks

import yaml
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

                print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> Added:\n{EVENT_obj}")
            else:
                print(f"\nSymbol: {SEC_object.symbol.upper()}\n--> <{existing_match}> already exists in database")

    db.session.commit()

def dividends_table_updater(db):
    sec_dict = get_symbol_to_id_dict(db)

    for symbol in sec_dict:
        symbol_id = sec_dict[symbol]
        #events_df = pd.DataFrame(yf.Ticker(symbol).splits)

        #Retrive security from database to link to dividend
        SEC_object = db.session.query(Security).filter(Security.symbol==symbol).first()

        _, _, div_amount, ex_div_date, div_pay_date, schedule_type, *extras = webscrape_tipranks(symbol)
        if schedule_type=='monthly':
            pay_schedule = 0
        elif schedule_type=='quarterly':
            pay_schedule = (div_pay_date.month % 3) + 1 #this will make the value between [1-3]
        elif schedule_type is None:
            pay_schedule = -1
        else:
            pay_schedule = -1

        DIVIDEND_OBJ = db.session.query(Dividend).filter(Dividend.symbol_id==symbol_id).first()
        
        if DIVIDEND_OBJ is None:
            DIVIDEND_OBJ = Dividend(dividend_amount  =div_amount,
                                    exdividend_date  =ex_div_date,
                                    payment_date     =div_pay_date,
                                    payment_schedule =pay_schedule,) 
            SEC_object.dividends.append(DIVIDEND_OBJ)
            db.session.add(DIVIDEND_OBJ)
        else:
            update_dict = {
                'dividend_amount'  : div_amount,
                'payment_schedule' : pay_schedule,
                'exdividend_date'  : ex_div_date,
                'payment_date'     : div_pay_date,
            }
            DIVIDEND_OBJ.dividend_amount = div_amount
            db.session.query(Dividend).filter_by(symbol_id=symbol_id).update(update_dict)

        db.session.commit()

if __name__ == '__main__':
    #Here we define a database connection
    try:
        DB_TYPE = sys.argv[1]
    except IndexError:
        DB_TYPE = 'mysql'
    
    supported_dbs = ['mysql','sqlite']
    #DB_TYPE = 'mysql'
    if DB_TYPE == 'mysql':
        with open('mysql_config.yml') as f_handler:
            config = yaml.safe_load(f_handler)
        
        username  = config.get('username')
        password  = config.get('password')
        host      = config.get('host')
        port      = config.get('port')
        _database = config.get('database')

        database_URI = f"mysql://{username}:{password}@{host}:{port}/{_database}"

    elif DB_TYPE == 'sqlite':

        project_dir  = os.path.dirname(os.path.abspath(__file__))
        database_dir = os.path.join(project_dir, "asset_portfolio.db")
        database_URI = f"sqlite:///{database_dir}"

    else:
        print(f'--> Database {DB_TYPE} not supported.\n\tDatabase options supported: {supported_dbs}')
        sys.exit()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_URI

    func_to_run = sys.argv[2]

    db.init_app(app)
    with app.app_context():
        if func_to_run=='splits':
            events_table_updater(db)
        elif func_to_run=='dividends':
            dividends_table_updater(db)