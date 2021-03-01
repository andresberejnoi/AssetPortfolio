'''Functions to be called from the main sites. It is to make the app code cleaner'''
import datetime
import pandas as pd
import yfinance as yf

from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet,
                    Position,)

from tools import (compute_shares_after_splits, yf_flags,
                   get_id_to_symbol_dict, 
                   get_symbol_to_id_dict,
                   compute_num_shares, 
                   get_last_transaction_datetime,
                   get_last_split_datetime)


CRYPTO_SYMBOL_TO_NAME = {
    'btc' :'Bitcoin',
    'eth' :'Ethereum',
    'ltc' :'Litecoin',
    'xrp' :'Ripple',
    'ada' :'Cardano',
    'usdc':'USD Coin',
    'neo' :'Neo',
    'usdt':'USD Tether',
    'link':'Chainlink',
    'dot' :'Polkadot',
    'bnb' :'Binance Coin',
    'bch' :'Bitcoin Cash',
    'xlm' :'Stellar',
    'nav' :'NavCoin',
    'vtc' :'Vertcoin',
    'doge':'DogeCoin',
}

BROKER_ALIASES_DICT = {
    'robinhood'    :['robinhood','robin','hood','robinhood.com','rb'],
    'shareowner'   :['shareowner','shareowneronline','shareowner_online','shareowner online','shareowneronline.com','soo','so',],
    'schwab'       :['schwab','charles','charles schwab','schwab.com','cs','shb'],
    'td Ameritrade':['td','ameritrade','thinkorswim','tdameritrade','td_ameritrade','tdameritrade.com','td ameritrade'],
}

def get_crypto_name(symbol):
    name = CRYPTO_SYMBOL_TO_NAME.get(symbol,'Unknown')
    return name

def get_broker_name(broker_name):
    broker_name = broker_name.lower()

    for key in BROKER_ALIASES_DICT:
        aliases = BROKER_ALIASES_DICT[key]
        if broker_name in aliases:
            return key
    
    return broker_name    #we only get to this point if the broker name is not recognized as a valid alias.

def get_Broker_object(db,broker_name):
    broker_name = broker_name.strip().lower()   #keep everything lowercase and stripped
    broker_name = get_broker_name(broker_name)  #matches user-provided broker value with what exists in the database

    broker = Broker.query.filter(Broker.name==broker_name).first()
    if broker is None:
        #creates broker and registers it in the database
        broker = create_new_broker_object(broker_name)
        db.session.add(broker)
        db.session.commit()
    return broker

def get_cryptocurrency_object(db,crypto_symbol):
    crypto_symbol = crypto_symbol.strip().lower()
    crypto_object = CryptoCurrency.query.filter(CryptoCurrency.symbol==crypto_symbol).first()
    if crypto_object is None:
        name = get_crypto_name(crypto_symbol)
        crypto_object = CryptoCurrency(symbol=crypto_symbol,name=name)
        db.session.add(crypto_object)
        db.session.commit()
    return crypto_object

def create_new_security_object(symbol):
    ticker = yf.Ticker(symbol)
    instrument_type = ticker.info.get(yf_flags.FLAG_INSTRUMENT_TYPE,None)
    company_name    = ticker.info.get(yf_flags.FLAG_NAME,None)
    sector          = ticker.info.get(yf_flags.FLAG_SECTOR,None)
    currency        = ticker.info.get(yf_flags.FLAG_CURRENCY,'USD')

    new_sec = Security(symbol,
                       instrument_type=instrument_type,
                       name=company_name,
                       sector=sector,
                       currency=currency)
    return new_sec

def create_new_broker_object(broker_name,website=''):
    '''Creates broker object based on broker_name'''
    broker = Broker(broker_name,website)
    return broker

def update_transactions_table(db,tickers_dict):
    '''Use this function with TransactionsForm
    Parameters
    ----------
    db: database
    tickers_dict: dict
        Dictionary returned by method `command_engine`
    '''
    for symbol in tickers_dict:
        SYMBOL_object = Security.query.filter(Security.symbol==symbol).first()     #without .first() the return is a query object
        if SYMBOL_object is None:
            SYMBOL_object = create_new_security_object(symbol)
            db.session.add(SYMBOL_object)
            db.session.commit()
        print(f"\n\n--> {SYMBOL_object}\n\n")
        
        trans_events = tickers_dict[symbol]   #gets list of TransactionEvent objects
        for trans in trans_events:
            BROKER_object = get_Broker_object(db, trans.broker)
            TRANS_object = Transaction(
                #trans.ticker, 
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
def update_positions_table(db,symbols_list):
    sec_dict = get_symbol_to_id_dict(db)

    for symbol in symbols_list:
        symbol_id = sec_dict[symbol]
        SEC_object        = db.session.query(Security).filter(Security.symbol==symbol).first()
        POSITION_object   = db.session.query(Position).filter(Position.symbol_id==symbol_id).first()

        adjusted_vals = compute_shares_after_splits(db,symbol_id)
        _total_shares = adjusted_vals[0]
        _cost_basis   = adjusted_vals[1]
        _invested     = adjusted_vals[2]

        last_transaction_update = db.session.query(Transaction.last_updated).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.last_updated.desc()).first()[0]
        print(f"\n\n--->LAST_TRANSACTION_UPDATE:\n\t{last_transaction_update}\n\n")
        if POSITION_object is None:
            POSITION_object = Position(total_shares=_total_shares,cost_basis=_cost_basis,invested=_invested,last_transaction_update=last_transaction_update)
            SEC_object.positions.append(POSITION_object)
            db.session.add(POSITION_object)
        else:
            update_dict = {
                'total_shares'    :_total_shares,
                'cost_basis'      :_cost_basis,
                'invested'        :_invested,
                'last_transaction_update':last_transaction_update,
            }
            #POSITION_object.update(update_dict)
            db.session.query(Position).filter_by(symbol_id=symbol_id).update(update_dict)

        db.session.commit()

def PROBLEM_update_positions_table(db,symbols_list):
    sec_dict = get_symbol_to_id_dict(db)

    for symbol in symbols_list:
        symbol_id = sec_dict[symbol]
        SEC_object        = db.session.query(Security).filter(Security.symbol==symbol).first()
        POSITION_object   = db.session.query(Position).filter(Position.symbol_id==symbol_id).first()
        last_transaction  = get_last_transaction_datetime(db,symbol_id)
        #last_event       = get_last_split_datetime(db,symbol_id)
        last_event_update = db.session.query(Event).filter(Event.symbol_id==symbol_id,Event.event_type=='split').order_by(Event.last_updated.desc()).first()[0]
        if last_event_update is None:
            last_event_update = datetime.datetime.fromisoformat('1800-01-01')  #just a very old date. It is the best I can do right now

        if (POSITION_object is None) or (POSITION_object.last_updated < last_event_update):
            #when there is no record of this object for the first time or when a new split is applied, we need to calculate with the entire history
            adjusted_vals = compute_shares_after_splits(db,symbol_id)
            total_shares  = adjusted_vals[0]
            cost_basis    = adjusted_vals[1]
            invested      = adjusted_vals[2]
            
            last_transaction_update = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.last_updated.desc()).first()[0]
            POSITION_object = Position(total_shares=total_shares,cost_basis=cost_basis,invested=invested,last_transaction_update=last_transaction_update)
            SEC_object.positions.append(POSITION_object)
            db.session.add(POSITION_object)
        
        else:
            sql_query = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id,Transaction.last_updated>POSITION_object.last_transaction_update).order_by(Transaction.time_execution.asc()).statement
            trans_df = pd.read_sql(sql=sql_query,con=db.session.bind)
            if len(trans_df) < 1:
                continue

            trans_df = trans_df.set_index('time_execution',drop=True)

            old_total_shares = POSITION_object.total_shares
            old_invested     = POSITION_object.invested

            adjusted_vals = compute_shares_after_splits(db,symbol_id,trans_df)
            _total_shares = adjusted_vals[0] + old_total_shares
            _invested     = adjusted_vals[2] + old_invested
            _cost_basis   = _invested / _total_shares
            update_dict = {
                'total_shares'    :_total_shares,
                'cost_basis'      :_cost_basis,
                'invested'        :_invested,
                'last_transaction':last_transaction,
            }
            POSITION_object.update(update_dict) 

        """    
        else:
            #find all new transactions created since after the last update
            last_transaction_update = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id).order_by(Transaction.last_updated.desc()).first()
            if POSITION_object.last_transaction < last_transaction:
                old_total_shares = POSITION_object.total_shares
                old_cost_basis   = POSITION_object.cost_basis
                old_invested     = POSITION_object.invested

                sql_query = db.session.query(Transaction).filter(Transaction.symbol_id==symbol_id,Transaction.last_updated>POSITION_object.last_transaction_update).order_by(Transaction.time_execution.asc()).statement
                trans_df = pd.read_sql(sql=sql_query,con=db.session.bind)
                trans_df = trans_df.set_index('time_execution',drop=True)
                adjusted_vals = compute_shares_after_splits(db,symbol_id,trans_df)
                _total_shares = adjusted_vals[0] + old_total_shares
                _invested     = adjusted_vals[2] + old_invested
                _cost_basis   = _invested / _total_shares
                update_dict = {
                    'total_shares'    :_total_shares,
                    'cost_basis'      :_cost_basis,
                    'invested'        :_invested,
                    'last_transaction':last_transaction,
                }
                POSITION_object.update(update_dict)
        """
        db.session.commit()  #maybe it needs to go after the for loop; test this