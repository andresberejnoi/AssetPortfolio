"""Collection of tools to use in different situations"""
from datetime import datetime
from types import SimpleNamespace
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet)

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