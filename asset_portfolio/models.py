from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
#from flask import Flask

#db = SQLAlchemy
db = SQLAlchemy() 


class Security(db.Model):
    __tablename__ = 'securities'
    
    id           = db.Column(db.Integer,db.Sequence('securities_id_seq'),primary_key=True)
    symbol       = db.Column(db.String(32), nullable=False, unique=True)
    instrument_type   = db.Column(db.String(64))
    name         = db.Column(db.String(255))
    sector       = db.Column(db.String(255))
    currency     = db.Column(db.String(32))
    #date_created = db.Column(db.DateTime, server_default=db.func.now())
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    transactions = db.relationship('Transaction', backref='securities', lazy=True)
    events       = db.relationship('Event'      , backref='securities', lazy=True)
    positions    = db.relationship('Position'   , backref='securities', lazy=True)
    dividends    = db.relationship('Dividend'   , backref='securities', lazy=True)
    
    def __init__(self,symbol,instrument_type=None,name=None,sector=None,currency=None):
        self.symbol   = symbol

        if instrument_type is not None:
            self.instrument_type = instrument_type
        if name is not None:
            self.name = name 
        if sector is not None:
            self.sector = sector
        if currency is not None:
            self.currency = currency

    def __repr__(self):
        return f"< Security: ticker={self.symbol}, instrument={self.instrument_type}, name={self.name}, currency={self.currency} >"

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id             = db.Column(db.Integer, db.Sequence('transactions_id_seq'), primary_key=True)
    #symbol_id     = db.Column(db.Integer,       nullable=False)
    symbol_id      = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    #symbol        = db.relationship('Symbol')
    num_shares     = db.Column(db.Numeric(19,9, asdecimal=True),         nullable=False)
    cost_basis     = db.Column(db.Numeric(19,5, asdecimal=True),         nullable=False)
    is_dividend    = db.Column(db.Boolean,                               nullable=True)
    broker_id      = db.Column(db.Integer, db.ForeignKey('brokers.id'),  nullable=False)
    time_execution = db.Column(db.DateTime,server_default=db.func.now(), nullable=False)    #it is important to have the time of the actual execution, because the events table will use that time to determine accurate share counts
    last_updated   = db.Column(db.DateTime,server_default=db.func.now(), onupdate=db.func.now(),       nullable=True)
    

    def __init__(self,num_shares,cost_basis,is_dividend=False,broker_id=1,time_execution=None):
        #self.symbol      = symbol.upper()
        self.num_shares  = num_shares
        self.cost_basis  = cost_basis
        self.is_dividend = is_dividend
        self.broker_id   = broker_id

        if time_execution is not None:
            self.time_execution = time_execution      #if it is None, the server will apply the current time, as indicated above in the setup

    def __repr__(self):
        return f"<Transaction: symbol_id={self.symbol_id} num_shares={self.num_shares} cost_basis={self.cost_basis} is_dividend={self.is_dividend} time_execution={self.time_execution}>"

class Broker(db.Model):
    __tablename__ = 'brokers'
    id      = db.Column(db.Integer, db.Sequence('brokers_id_seq'), primary_key=True)
    name    = db.Column(db.String(255), nullable=False, unique=True)
    website = db.Column(db.String(255), nullable=True) 
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(),nullable=False)
    transactions = db.relationship('Transaction', backref='brokers',lazy=True)

    def __init__(self, name, website=''):
        self.name = name 

        if len(website) > 0:
            self.website = website

    def __repr__(self):
        return f"< Broker: name={self.name} website={self.website} >"

class Event(db.Model):
    __tablename__ = 'securities_events'
    id              = db.Column(db.Integer,db.Sequence('securities_events_id_seq'),primary_key=True)
    symbol_id       = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    event_type      = db.Column(db.String(64), nullable=False) 
    split_factor    = db.Column(db.Numeric(19,10),nullable=True)  #only required for split events. I think this table will contain dividend cuts and raises as well
    dividend_change = db.Column(db.Numeric(19,5, asdecimal=True),nullable=True)
    event_date      = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    last_updated    = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
 
    def __init__(self,event_type,event_date,**kwargs):
        self.event_type = event_type
        self.event_date = event_date
        split_factor = kwargs.get('split_factor',None)
        dividend_change = kwargs.get('dividend_change',None)

        if split_factor is not None:
            self.split_factor = split_factor 
        if dividend_change is not None:
            self.dividend_change = dividend_change

    def __repr__(self):
        return f"< Event: symbol_id={self.symbol_id} event_type={self.event_type} event_date={self.event_date} split_factor={self.split_factor} dividend_change={self.dividend_change} >"

class Position(db.Model):
    __tablename__ = 'security_positions'
    id               = db.Column(db.Integer,db.Sequence('securities_positions_id_seq'),primary_key=True)
    symbol_id        = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    total_shares     = db.Column(db.Numeric(19,9, asdecimal=True),         nullable=False)
    cost_basis       = db.Column(db.Numeric(19,5, asdecimal=True),         nullable=False)
    invested         = db.Column(db.Numeric(19,5, asdecimal=True),         nullable=False)
    last_transaction_update = db.Column(db.DateTime,                              nullable=False)
    last_updated     = db.Column(db.DateTime,server_default=db.func.now(), onupdate=db.func.now(),       nullable=True)

    def __init__(self,**kwargs):
        '''
        Parameters
        ----------
        symbol_id: int
            Foreign key from securities table
        total_shares: Decimal (19,9)
            Total amount of shares combining all transactions and accounting for splits
        cost_basis: Decimal(19,5)
            Average cost per share based on total money invested and `total_shares`
        invested: Decimal(19,5)
            Total amount invested. It should be `total_shares` * `cost_basis`
        last_transaction_update: datetime object
            Time of the last transaction update for this symbol id according to the transactions table
        last_updated: datetime object
            Last time this record was modified
        '''
        self.total_shares     = kwargs.get('total_shares', 0)
        self.cost_basis       = kwargs.get('cost_basis', 0)
        self.last_transaction_update = kwargs.get('last_transaction_update', None)
        self.invested         = kwargs.get('invested', None)
        if self.invested is None:
            self.invested = self.total_shares * self.cost_basis

    def __repr__(self):
        return f"< Position: symbol_id={self.symbol_id} total_shares={self.total_shares} cost_basis={self.cost_basis} invested={self.invested} >"

class Dividend(db.Model):
    __tablename__    = "current_dividends"
    id               = db.Column(db.Integer, db.Sequence('current_dividends_id_seq'), primary_key=True)
    symbol_id        = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    dividend_amount  = db.Column(db.Numeric(19, 5, asdecimal=True),           nullable=True)
    payment_schedule = db.Column(db.Integer,  nullable=True)
    exdividend_date  = db.Column(db.DateTime, nullable=True)
    payment_date     = db.Column(db.DateTime, nullable=True)
    last_updated     = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=True)

    #For printing purposes
    SCHEDULE_DICT = {
        -1 : 'N/A',
        0  : 'montly',
        1  : 'Jan,Apr,July,Oct',
        2  : 'Feb,May,Aug,Nov',
        3  : 'Mar,June,Sep,Dec',
        4  : 'bi-annual',
        5  : 'irregular'
    }

    def __init__(self, dividend_amount, payment_schedule, exdividend_date, payment_date):
        self.dividend_amount  = dividend_amount
        self.payment_schedule = payment_schedule
        self.exdividend_date  = exdividend_date
        self.payment_date     = payment_date

    def __repr__(self):
        return f"<Dividend: symbol_id={self.symbol_id} | Amount=${self.dividend_amount} | Schedule={self.SCHEDULE_DICT[self.payment_schedule]} | last updated on: {self.last_updated}"

class CryptoCurrency(db.Model):
    __tablename__ = 'cryptocurrencies'
    id = db.Column(db.Integer, db.Sequence('cryptocurrencies_id_seq'), primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    symbol = db.Column(db.String(32), nullable=False, unique=True)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    wallets = db.relationship('CryptoWallet',backref='cryptocurrencies',lazy=True)

    def __init__(self,symbol,name=None):
        self.symbol = symbol
        if name is not None:
            self.name = name

class CryptoWallet(db.Model):
    __tablename__ = 'cryptowallets'
    id = db.Column(db.Integer, db.Sequence('cryptowallets_id_seq'), primary_key=True)
    cryptocurrency_id = db.Column(db.Integer, db.ForeignKey('cryptocurrencies.id'), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(64), nullable=True)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __init__(self,address,nickname='wallet'):
        self.address  = address 
        self.nickname = nickname



def init_tables(db):
    #db.create_all()

    #register brokers here
    brokers_list = [('robinhood','https://robinhood.com/us/en/'),('shareowner','https://www.shareowneronline.com/')]
    #brokers_list = [('robinhood','fake_website'),('shareowner','fake_website')]

    #for broker_item in brokers:
    #    broker,website = broker_item
    #    b = Broker(broker,website)
    #    db.session.add(b)
    broker_objects = [Broker(broker_name,website) for broker_name,website in brokers_list]
    db.session.add_all(broker_objects)

    str_list = "\n".join([str(b) for b in broker_objects])
    print(f'\n\nAdding broker Objects:\n{str_list}')
    db.session.commit()

def create_app():
    app = Flask(__name__)
    #db.init_app(app)
    return app

if __name__ == '__main__':
    '''
    app = create_app()
    
    with app.app_context():
        db.create_all()
        init_tables(db)
    '''