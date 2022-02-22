"""Collection of tools to use in different situations"""
import math
import decimal
from numpy.lib.arraysetops import isin
import pandas as pd
from datetime import datetime
from types import SimpleNamespace

from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet,
                    Position, Dividend)

from bs4 import BeautifulSoup
import requests
import re
import os
import sys
import yaml
from flask import Flask

yf_flags = SimpleNamespace(
    FLAG_INSTRUMENT_TYPE     = 'quoteType',
    FLAG_SECTOR              = 'sector',
    FLAG_CURRENCY            = 'currency',
    FLAG_NAME                = 'shortName',
    FLAG_SYMBOL              = 'symbol',
    FLAG_EXDIV_DATE          = 'exDividendDate',
    FLAG_LAST_SPLIT_DATE     = 'lastSplitDate',
    FLAG_LAST_SPLIT_FACTOR   = 'lastSplitFactor',
    FLAG_LAST_DIV_AMOUNT     = 'lastDividendValue',
    FLAG_GMT_OFFSET_MILLI    = 'gmtOffSetMilliseconds',
    FLAG_EXCHANGE_TIMEZONE   = 'exchangeTimezoneShortName',
)


def _get_str_dict(dict_object,depth_level):
    '''create a string recursively for dictionaries. I wrote it quickly, 
    so I have not even thought about if it works for more than 2 levels deep'''
    d = dict_object
    str_dict = ''
    open_curly   = '{'
    closed_curly = '}'
    tab_space = "     "
    tab = tab_space*depth_level
    if isinstance(d,dict):
        #str_dict += '\n'
        for idx,key in enumerate(d):
            str_dict += f"{tab}{open_curly}{key}:\n"  #   *(idx+1)}"
            #str_dict += f"{open_curly}{tab}\n{key}: "
            str_dict += f"{get_str_dict(d[key],depth_level+1)},\n"
        str_dict += f"{tab}{closed_curly}\n"
        return str_dict
    else: 
        return f"{tab}{d}"

def pprint_dict(dict_object):
    depth = 0
    str_dict = _get_str_dict(dict_object,depth)
    return str_dict

def unix_to_datetime(unix_timestamp):
    dt = datetime.fromtimestamp(unix_timestamp)
    return dt

def get_split_multiplier(ratio_str):
    '''ratio or factor is assumed in the form of a string as:
                    "4:1"
     which means one share splits into 4
    '''
    factors_split = ratio_str.split(':')
    new_amount = int(factors_split[0])
    old_amount = int(factors_split[1])
    multiplier = new_amount / old_amount
    
    return multiplier

def get_symbol_to_id_dict(db):
    sec_dict = dict(db.session.query(Security.symbol,Security.id).all())
    return sec_dict

def get_id_to_symbol_dict(db):
    sec_dict = dict(db.session.query(Security.id,Security.symbol).all())
    return sec_dict


def get_split_events_df(db):
    '''NOT OPERATIONAL YET'''
    sql_statement = db.session.query(
                        Event.event_date, 
                        Event.symbol_id, 
                        Event.split_factor,
                        ).filter(
                            Event.event_type=='split' or Event.event_type=='reverse_split'
                        ).statement

    df = pd.read_sql(sql=sql_statement,con=db.session.bind)
    return df

def get_last_transaction_datetime(db,symbol_id):
    TRANS_object = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.time_execution.desc()).first()
    if TRANS_object is None:
        return None
    return TRANS_object.time_execution

def get_last_split_datetime(db,symbol_id):
    EVENT_object = db.session.query(Event).filter(Event.symbol_id==symbol_id,Event.event_type=='split').order_by(Event.event_date.desc()).first()
    if EVENT_object is None:
        return None
    return EVENT_object.event_date

def compute_num_shares(db,symbol_id):

    #get transactions for current symbol, ordered by date, ascending
    sql_statement = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.time_execution.asc()).statement
    trans_df = pd.read_sql(sql=sql_statement,con=db.session.bind)
    trans_df = trans_df.set_index('time_execution', drop=True)

    #get split events for current symbol, ordered by date, ascending
    event_type = 'split'
    sql_statement = db.session.query(Event).filter(Event.symbol_id==symbol_id,Event.event_type==event_type).order_by(Event.event_date.asc()).statement
    splits = pd.read_sql(sql=sql_statement,con=db.session.bind)
    splits = splits[['event_date','split_factor']].set_index('event_date', drop=True)

    if len(splits) < 1:
        total_shares = trans_df['num_shares'].sum()
    else:
        total_shares = 0
        prev_split_date = '1800-01-01'
        for row in splits.itertuples():
            split_date   = row.Index
            split_factor = row[1]

            shares_to_split = trans_df[prev_split_date:split_date]
            total_split_factor = splits[split_date:].aggregate(math.prod)[0]   #gets the single factor from multiplying all the splits from this time to the present

            total_shares += (shares_to_split['num_shares']*total_split_factor).sum()

            prev_split_date = split_date

        #Here we add the last portion of shares purchased after last split
        total_shares += trans_df[prev_split_date:]['num_shares'].sum()

    return total_shares

def compute_shares_after_splits(db,symbol_id,trans_df=None):
    '''
    Computes total number of shares for given `symbol_id` by taking into account
    the split events from the `events` table. It will also compute the adjusted 
    cost basis as an average of the share value.

    Parameters
    ----------
    db: Flask-SQLAlchemy handle
        The object that allows us to interact with the database
    symbol_id: int
        Foreign key to the corresponding `symbol` in `securities` table
    trans_df: pandas.DataFrame
        The transactions we are interested in adjusting. Index for this dataframe should
        be the `time_execution` field from the `transactions` table and 
        converted into `DatetimeIndex`. This should be a dataframe obtained from reading the 
        database table `transactions` into a pandas dataframe. For example:

        ```py
        sql_query = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.time_execution.asc()).statement
        trans_df = pd.read_sql(sql=sql_query,con=db.session.bind)
        trans_df = trans_df.set_index('time_execution', drop=True)
        ```
        As such, `trans_df` is expected to have columns `num_shares` and `cost_basis`
    Returns
    -------
    adjusted_values: tuple of decimal.Decimal
        A collection of adjusted values based on the splits applied. i.e.:
        (total_adjusted_shares, adjusted_cost_basis, money_invested)
    '''
    #if trans_df is not provided, use all transactions (this will be the case when the `positions` table is first created)
    if trans_df is None:
        sql_query = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.time_execution.asc()).statement
        trans_df = pd.read_sql(sql=sql_query,con=db.session.bind)
        trans_df = trans_df.set_index('time_execution', drop=True)

    #get split events for current symbol, ordered by date, ascending
    event_type = 'split'
    sql_statement = db.session.query(Event).filter(Event.symbol_id==symbol_id,Event.event_type==event_type).order_by(Event.event_date.asc()).statement
    splits = pd.read_sql(sql=sql_statement,con=db.session.bind)
    splits = splits[['event_date','split_factor']].set_index('event_date', drop=True)

    if len(splits) < 1:
        total_shares = trans_df['num_shares'].sum()
        money_invested = (trans_df['num_shares'] * trans_df['cost_basis']).sum()
        if total_shares == 0:
            adjusted_cost_basis = 0
        else:
            adjusted_cost_basis = money_invested / total_shares
    else:
        total_shares    = 0
        prev_split_date = '1800-01-01'
        for row in splits.itertuples():
            split_date   = row.Index
            split_factor = row[1]

            shares_to_split = trans_df[prev_split_date:split_date]
            total_split_factor = splits[split_date:].aggregate(math.prod)[0]   #gets the single factor from multiplying all the splits from this time to the present
            total_shares += (shares_to_split['num_shares']*total_split_factor).sum()

            prev_split_date = split_date

        #Here we add the last portion of shares purchased after last split
        total_shares += trans_df[prev_split_date:]['num_shares'].sum()
        money_invested = (trans_df['num_shares'] * trans_df['cost_basis']).sum()
        if total_shares == 0:
            adjusted_cost_basis = 0
        else:
            adjusted_cost_basis = money_invested / total_shares

    return (decimal.Decimal(total_shares),
            decimal.Decimal(adjusted_cost_basis),
            decimal.Decimal(money_invested),)


def webscrape_tipranks(ticker):
    base_url    = "https://www.tipranks.com/stocks/"
    url_section = "/dividends"
    url  = f"{base_url}{ticker}{url_section}"
    
    #==================
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html5lib')
    fundamentals = soup.find_all('div', attrs={'data-s':'fundamentals'})
    
    try:
        item = fundamentals[0]
    except IndexError:
        return ticker, None, None, None, None, None
    
    #========Regex Patterns
    float_pattern = r"\$([0-9]+.[0-9]+)"  #for values like $1.64, $0.78, etc
    int_pattern   = r"\$([0-9]+)"         #for values like $2, $10, $1, etc (no decimal point)
    pattern       = f"{float_pattern}|{int_pattern}"
    
    negative_float_pattern = r"(?:\$[0-9]+.[0-9]+)"  #for values like $1.64, $0.78, etc
    negative_int_pattern   = r"(?:\$[0-9]+)"         #for values like $2, $10, $1, etc (no decimal point)
    schedule_type_pattern  = f"(?:{negative_float_pattern}|{negative_int_pattern})([a-z]+)\s*"
    
    months  = r"(jan|feb|mar|apr|may|jun|july|aug|sep|oct|nov|dec)"
    date_pattern = f"({months} ([0-9]+), ([0-9]+))"
    
    ex_div_date_pattern  = f"(?:next ex-dividend date)\s*{date_pattern}"  #the ?: makes sure that the whole group inside the parenthesis is not captured
    payment_date_pattern = f"(?:payment date)\s*{date_pattern}" 
    
    if item is not None:
        str_item = item.text.lower()

        res = re.search(pattern, str_item)
        if res:
            div_str    = res.group()
            div_str    = div_str.replace("$", "")
            div_amount = decimal.Decimal(div_str)
            
            #_str_ex_div_date = re.search(ex_div_date_pattern, str_item).groups()[0]  #first item   #date comes in format: Dec 15, 2021
            
            dates = re.findall(date_pattern, str_item)
            _str_ex_div_date = dates[0][0]
            _str_pay_date    = dates[1][0]
            
            ex_div_date   = datetime.strptime(_str_ex_div_date, "%b %d, %Y")    #datetime.strptime('Jun 1, 2005  1:33PM', '%b %d, %Y %I:%M%p')
            payment_date  = datetime.strptime(_str_pay_date, "%b %d, %Y")
            schedule_type = re.search(schedule_type_pattern, str_item).groups()[0].strip()
            
        return ticker, div_str, div_amount, ex_div_date, payment_date, schedule_type

def write_table_to_csv(db, table='transactions', output_file=''):
    TABLE_MAP = {
        'transactions' : Transaction,
        'positions'    : Position,
        'events'       : Event,
        'securities'   : Security,
        'brokers'      : Broker,
        'dividends'    : Dividend,
    }

    NO_SYMBOL_ID = (Security, CryptoCurrency, CryptoWallet, Broker)

    if len(output_file) < 1:
        folder_output = 'db_files'
        if not os.path.exists(folder_output):
            os.mkdir(folder_output)
        output_file = os.path.join(folder_output, f"{table}.csv")
            
    table_class = TABLE_MAP.get(table.lower(), 'transactions')
    sql_statement = db.session.query(table_class).statement
    df = pd.read_sql(sql=sql_statement,con=db.session.bind)

    #----------Replace Ticker Ids with Actual Tickers
    if not isinstance(table_class, NO_SYMBOL_ID):
        ids_to_tickers_dict = get_id_to_symbol_dict(db)
        df = df.replace({'symbol_id':ids_to_tickers_dict})
    df.to_csv(output_file,)

def get_mysql_uri(config_file='mysql_config.yml', database_name=None):
    with open(config_file) as f_handler:
        config = yaml.safe_load(f_handler)
        
    username  = config.get('username')
    password  = config.get('password')
    host      = config.get('host')
    port      = config.get('port')
    _database = config.get('database') if database_name is None else database_name

    database_URI = f"mysql://{username}:{password}@{host}:{port}/{_database}"
    return database_URI

def exists_in_table(new_entry, db):
    table_class = type(new_entry)
    match = False

    if isinstance(new_entry, Security):
        match = db.session.query(table_class).fitler(table_class.symbol==new_entry.symbol).first()
    elif isinstance(new_entry, Broker):
        pass

    elif isinstance(new_entry, Transaction):
        match = db.session.query(table_class).filter(
            table_class.symbol_id==new_entry.symbol_id,
            table_class.num_shares==new_entry.num_shares,
            table_class.cost_basis==new_entry.cost_basis,
            table_class.is_dividend==new_entry.is_dividend,
            table_class.time_execution==new_entry.time_execution,
            ).first()

    if match:
        return True
    else:
        return False

def generate_unique_id(new_entry):
    pass 

if __name__ == '__main__':
    #test writing database tables to csv
    try:
        table = sys.argv[1]
    except IndexError:
        table = 'transactions'
    
    database_URI = get_mysql_uri('mysql_config.yml')
    print(f'--> MySQL URI:\n\t{database_URI}')
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_URI

    db.init_app(app)
    with app.app_context():
        write_table_to_csv(db, table=table,)