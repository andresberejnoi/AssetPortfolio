from flask_sqlalchemy import SQLAlchemy
#from flask import Flask

#db = SQLAlchemy
db = SQLAlchemy() 


class Security(db.Model):
    __tablename__ = 'securities'
    
    id           = db.Column(db.Integer,db.Sequence('securities_id_seq'),primary_key=True)
    symbol       = db.Column(db.String(32), nullable=False, unique=True)
    instrument   = db.Column(db.String(64))
    name         = db.Column(db.String(255))
    sector       = db.Column(db.String(255))
    currency     = db.Column(db.String(32))
    date_created = db.Column(db.DateTime, server_default=db.func.now())
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    transactions = db.relationship('Transaction',backref='securities',lazy=True)
    
    def __init__(self,symbol,instrument='',name='',sector='',currency='USD'):
        self.symbol   = symbol
        self.currency = currency

    def __repr__(self):
        return f"Security(ticker={self.symbol}, instrument={self.instrument}, name={self.name}, currency={self.currency})"

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
    

    def __init__(self,symbol,num_shares,cost_basis,is_dividend=False,broker_id=1,time_execution=None):
        self.symbol      = symbol.upper()
        self.num_shares  = num_shares
        self.cost_basis  = cost_basis
        self.is_dividend = is_dividend
        self.broker_id   = broker_id

        if time_execution is not None:
            self.time_execution = time_execution      #if it is None, the server will apply the current time, as indicated above in the setup

    def __repr__(self):
        return f"<Transaction: symbol={self.symbol} num_shares={self.num_shares} cost_basis={self.cost_basis} is_dividend={self.is_dividend}>"

class Broker(db.Model):
    __tablename__ = 'brokers'
    id      = db.Column(db.Integer, db.Sequence('brokers_id_seq'), primary_key=True)
    name    = db.Column(db.String(255), nullable=False, unique=True)
    website = db.Column(db.String(255), nullable=True) 
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(),nullable=False)
    transactions = db.relationship('Transaction',backref='brokers',lazy=True)

    def __init__(self, name, website=''):
        self.name = name 

        if len(website) > 0:
            self.website = website

    def __repr__(self):
        return f"< Broker: name={self.name} website={self.website}"

class Event(db.Model):
    __tablename__ = 'securities_events'
    id           = db.Column(db.Integer,db.Sequence('securities_events_id_seq'),primary_key=True)
    symbol_id    = db.Column(db.Integer, db.ForeignKey('securities.id'),  nullable=False)
    event_type   = db.Column(db.String(64), nullable=False) 
    event_date   = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
 
    def __repr__(self):
        return f"< Event: symbol_id={self.symbol_id} event_type={self.event_type} event_date={self.event_date}"

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