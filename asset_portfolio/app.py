import os
import datetime 
import pandas as pd


#============================================
#     Flask Related Import
from flask import Flask
from flask import render_template
from flask import request, url_for, redirect
from flask_bootstrap import Bootstrap

#============================================
#     Bokeh-Related Imports 
from bokeh.embed import server_document, components
from bokeh.layouts import column, row, widgetbox
from bokeh.models import ColumnDataSource, Slider
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Select
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.themes import Theme
from tornado.ioloop import IOLoop
from bokeh.palettes import inferno
from bokeh.transform import factor_cmap, dodge

from bokeh.core.properties import value

from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature


# from bokeh.embed import components
from bokeh.io import curdoc

from threading import Thread
#============================================
#     Local Files and Modules
from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet)
from models import init_tables
from forms import (CryptoWalletForm, RegisterBrokerForm, 
                   TransactionsForm, CheckEntryForm)
from command_engine import command_engine

#=================================================
python_PID = os.getpid()
#=================================================
#Here we define a database connection
project_dir  = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(project_dir, "asset_portfolio.db")
database_file = f"sqlite:///{database_dir}"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_file

FAKE_SECRET_KEY = 'super_duper_secure_key_1234'    #need secret key for CSRF from WTF-Forms to work
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
CRYPTO_SYMBOL_TO_NAME = {
    'btc':'Bitcoin',
    'eth':'Ethereum',
    'ltc':'Litecoin',
    'xrp':'Ripple',
    'ada':'Cardano',
    'usdc':'USD Coin',
    'neo':'Neo',
    'usdt':'USD Tether',
    'link':'Chainlink',
    'dot':'Polkadot',
    'bnb':'Binance Coin',
    'bch':'Bitcoin Cash',
    'xlm':'Stellar'
}

def get_crypto_name(symbol):
    name = CRYPTO_SYMBOL_TO_NAME.get(symbol,'Unknown')
    return name

def get_Broker_object(broker_name):
    broker_name = broker_name.strip().lower()   #keep everything lowercase and stripped
    broker = Broker.query.filter(Broker.name==broker_name).first()
    if broker is None:
        raise ValueError(f"\n--> Broker of name '{broker_name}' is not registered")
    return broker

def get_cryptocurrency_object(crypto_symbol):
    crypto_symbol = crypto_symbol.strip().lower()
    crypto_object = CryptoCurrency.query.filter(CryptoCurrency.symbol==crypto_symbol).first()
    if crypto_object is None:
        name = get_crypto_name(crypto_symbol)
        crypto_object = CryptoCurrency(symbol=crypto_symbol,name=name)
        db.session.add(crypto_object)
        db.session.commit()
    return crypto_object


@app.route("/",methods=['GET','POST'])
def home():
    plot_fig = histogram_holdings()
    if plot_fig is not None:
        script, div = components(plot_fig)
    else:
        script = ''
        div    = ''
    form = TransactionsForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():

        tickers_dict = command_engine(form.transactions_str.data)
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
        #return redirect(url_for('home'))
        return render_template("home.html", form=form, script=script, div=div)
    else:
        return render_template("home.html", form=form, script=script, div=div)

@app.route('/wallet_registration',methods=['GET','POST'])
def wallet_registration():
    form = CryptoWalletForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        #--Create Wallet address object
        address  = form.address.data
        nickname = form.nickname.data
        symbol   = form.symbol.data.lower()
        CURRENCY_object = get_cryptocurrency_object(symbol)
        WALLET_object = CryptoWallet(address,nickname)

        CURRENCY_object.wallets.append(WALLET_object)
        db.session.add(WALLET_object)
        db.session.commit()
        return redirect(url_for('home'))
    else:
        return render_template('crypto_wallet_registration.html', form=form)

@app.route('/register_broker',methods=['GET','POST'])
def register_broker():
    form = RegisterBrokerForm(request.form)
    if request.method=='POST' and form.validate_on_submit():
        name = form.name.data.lower()
        website = form.website.data
        BROKER_object = Broker(name,website)
        db.session.add(BROKER_object)
        db.session.commit()

        return redirect(url_for('home'))
    else:
        return render_template('register_broker.html',form=form)

@app.route('/check_entries',methods=['GET','POST'])
def check_entries():
    form = CheckEntryForm(request.form)
    tables = []
    titles = []
    if request.method=='POST' and form.validate_on_submit():
        table_to_show = form.table.data 
        #print(f"\n\nTable name chosen: {table_to_show}, type={type(table_to_show)}\n\n")
        if table_to_show == '0': #'securities':
            df = pd.read_sql(sql=db.session.query(Security).statement,con=db.session.bind) 

        elif table_to_show == '1': #'transactions':
            df = pd.read_sql(sql=db.session.query(Transaction).statement,con=db.session.bind)

        elif table_to_show == '2': #'brokers':
            df = pd.read_sql(sql=db.session.query(Broker).statement,con=db.session.bind)

        elif table_to_show == '3': #'crypto':
            df = pd.read_sql(sql=db.session.query(CryptoCurrency).statement,con=db.session.bind)

        elif table_to_show == '4': #'wallets':
            df = pd.read_sql(sql=db.session.query(CryptoWallet).statement,con=db.session.bind)
        
        #-----determine how many rows to show
        rows_to_show = form.rows_to_show.data
        if rows_to_show == 'all':
            num_rows = len(df)
        else:
            try:
                num_rows = int(rows_to_show)
            except ValueError:
                num_rows = len(df)
        #--------

        tables=[df.tail(num_rows).to_html(classes='mystyle')]
        titles=df.columns.values
        return render_template('check_entries.html',form=form,tables=tables,titles=titles)
    else:
        return render_template('check_entries.html',form=form,tables=tables,titles=titles)
#======================================
#  Creating a Bokeh App to embed into Flask

def bkapp(doc):
    df = sea_surface_temperature.copy()
    source = ColumnDataSource(data=df)

    plot = figure(x_axis_type='datetime', y_range=(0, 25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    plot.line('time', 'temperature', source=source)

    def callback(attr, old, new):
        if new == 0:
            data = df
        else:
            data = df.rolling(f"{new}D").mean()
        source.data = ColumnDataSource.from_df(data)

    slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing by N Days")
    slider.on_change('value', callback)

    doc.add_root(column(slider, plot))

    doc.theme = Theme(filename="theme.yaml")

def histogram_holdings():
    '''
    sec_df = pd.read_sql(sql=db.session.query(Security).statement,con=db.session.bind)

    if len(sec_df) < 1:
        return None

    id_to_symbol_mapping = {
        symbol_id:symbol for symbol_id,symbol in zip(sec_df['id'],sec_df['symbol'])
    }
    #sec_df = sec_df[['symbol','id']]
    '''
    #get list of id and symbols and turn them into dict
    sec_list = db.session.query(Security.id,Security.symbol).all()
    id_to_symbol_mapping = dict(sec_list)
    
    trans_df = pd.read_sql(sql=db.session.query(Transaction).statement,con=db.session.bind)
    if len(trans_df) < 1:
        return None
    trans_df['invested'] = trans_df['num_shares'] * trans_df['cost_basis']
    #trans_df = trans_df[['symbol_id','invested']]
    by_symbol = trans_df.groupby('symbol_id').sum().reset_index()
    #print(by_symbol)
    #print(sec_df)
    #by_symbol['symbol'] = sec_df.loc[by_symbol['symbol_id']==sec_df['id']]['symbol']
    by_symbol['symbol'] = by_symbol['symbol_id'].copy()
    by_symbol = by_symbol.replace({'symbol':id_to_symbol_mapping})
    
    by_symbol = by_symbol[['symbol','invested']]
    print(id_to_symbol_mapping)
    print(by_symbol)
    #print(sec_df)
    

    source = ColumnDataSource(data=by_symbol)
    plot_fig = figure(x_range=by_symbol['symbol'], y_range=(0, by_symbol['invested'].max() + 100), 
           plot_height=250, title="Money Invested per Security",
           toolbar_location=None, tools="")

    plot_fig.vbar(x=dodge('symbol', -0.5, range=plot_fig.x_range), top='invested', width=0.4, source=source,
       color="#c9d9d3", legend_label="Dollars Invested")

    plot_fig.x_range.range_padding = 0.1
    plot_fig.xgrid.grid_line_color = None
    plot_fig.legend.location = "top_left"
    plot_fig.legend.orientation = "horizontal"
    return plot_fig

@app.route('/bkapp', methods=['GET'])
def bkapp_page():
    script = server_document('http://localhost:5006/bkapp')
    print(f"Here is the script:\n\n{script}\n\n")
    return render_template("embed.html", script=script, template="Flask")#, relative_urls=False)


def bk_worker():
    # Can't pass num_procs > 1 in this configuration. If you need to run multiple
    # processes, see e.g. flask_gunicorn_embed.py
    #server = Server({'/bkapp': bkapp}, io_loop=IOLoop(), allow_websocket_origin=["0.0.0.0:8000"])
    server = Server({'/bkapp':bkapp}, io_loop=IOLoop(), allow_websocket_origin=["localhost:8000","127.0.0.1:8000"])
    server.start()
    server.io_loop.start()


Thread(target=bk_worker).start()

def write_pid_to_file(pid,filename):
    with open(filename,'w') as f:
        f.write(str(pid))

if __name__ == "__main__":
    #-------
    # Getting PID to kill this process later (not necessary, but it is an annoyance to do it manually)
    python_PID = os.getpid()
    print(f"\n\n--> PID of this Python App:\n\t{python_PID}\n\n")
    write_pid_to_file(python_PID,'_flask_PID')
    #------

    app.run(port=8000, debug=True)
    
