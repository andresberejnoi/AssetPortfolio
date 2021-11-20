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
from bokeh.models import ColumnDataSource, Slider, CustomJS, Div
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Select
from bokeh.resources import INLINE
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
                    Event, CryptoCurrency, CryptoWallet,
                    Position,)
from models import init_tables
from forms import (CryptoWalletForm, RegisterBrokerForm, 
                   TransactionsForm, CheckEntryForm)
from command_engine import command_engine

from tools import get_id_to_symbol_dict, get_symbol_to_id_dict

from table_updaters import (update_transactions_table,
                            update_positions_table,)

import yaml
#=================================================
#Here we define a database connection
DB_TYPE = 'mysql'
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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_URI

#engine = sqlalchemy.create_engine(database_URI)

FAKE_SECRET_KEY = 'super_duper_secure_key_1234'    #need secret key for CSRF from WTF-Forms to work
app.config['SECRET_KEY'] = FAKE_SECRET_KEY

Bootstrap(app)
db.init_app(app)

with app.app_context():
    db.create_all()

#==============================================================
#                           ROUTES
#==============================================================
@app.route("/",methods=['GET','POST'])
def home():
    sym_dic = get_symbol_to_id_dict(db)
    #update_positions_table(db,sym_dic.keys())
    form = TransactionsForm(request.form)
    form_was_submitted = False

    if request.method == 'POST' and form.validate_on_submit():
        form_was_submitted = True
        trans_str = form.transactions_str.data

        #process the str command into dict of TransactionEvent objects
        tickers_dict = command_engine(trans_str)  

        #update relevant tables
        update_transactions_table(db,tickers_dict)
        update_positions_table(db,tickers_dict.keys())  #I could technically just send tickers_dict and it should work

    # This is the display portion
    plot_fig = histogram_holdings()
    if plot_fig is not None:
        script, div = components(plot_fig)
    else:
        script = ''
        div    = ''
    js_resources = ''  #INLINE.render_js()
    css_resources = '' #INLINE.render_css()

    if form_was_submitted:
        return redirect(url_for("home",
                                js_resources=js_resources,
                                css_resources=css_resources,
                                form=form,
                                script=script,
                                div=div,))
    else:
        # render template
        html = render_template(
            'home.html',
            js_resources=js_resources,
            css_resources=css_resources,
            form=form,
            script=script,
            div=div,
        )
        return html

@app.route("/holdings")
def holdings():
    sql_statement = db.session.query(Transaction).statement 
    df = pd.read_sql(sql=sql_statement,con=db.session.bind)

    long_term_start = datetime.datetime.utcnow() - datetime.timedelta(days=366)
    long_term_df  = df[df['time_execution']<=long_term_start]
    short_term_df = df[df['time_execution']>long_term_start]
    
    #sum up all the shares; cost basis and others are not needed right now, but I think they should be added eventually
    long_term_df  = long_term_df[['symbol_id','num_shares']].groupby('symbol_id').sum().reset_index()
    short_term_df = short_term_df[['symbol_id','num_shares']].groupby('symbol_id').sum().reset_index()

    #replacing symbol IDs with the corresponding symbol
    id_symbols_dict = get_id_to_symbol_dict(db)
    long_term_df  = long_term_df.replace({'symbol_id':id_symbols_dict})
    short_term_df = short_term_df.replace({'symbol_id':id_symbols_dict})
    
    #setting up the values to send back
    tables_long_term = [long_term_df.to_html(classes='mystyle',index=False),]
    tables_short_term = [short_term_df.to_html(classes='mystyle',index=False),]
    
    titles_long_term  = long_term_df.columns.values
    titles_short_term = short_term_df.columns.values

    return render_template('holdings.html',
                           tables_long_term=tables_long_term,
                           titles_long_term=titles_long_term,
                           tables_short_term=tables_short_term,
                           titles_short_term=titles_short_term,)

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

    #    return redirect(url_for('home'))
    #else:
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
            sql_statement = db.session.query(Security).statement

        elif table_to_show == '1': #'transactions':
            sql_statement =db.session.query(Transaction).statement

        elif table_to_show == '2': #'brokers':
            sql_statement = db.session.query(Broker).statement

        elif table_to_show == '3': #'crypto':
            sql_statement = db.session.query(CryptoCurrency).statement

        elif table_to_show == '4': #'wallets':
            sql_statement = db.session.query(CryptoWallet).statement
        
        elif table_to_show == '5': #'events':  
            sql_statement = db.session.query(Event).statement
        
        elif table_to_show == '6': #'positions'
            sql_statement = db.session.query(Position).statement

        #=====GET DATAFRAME FROM DATABASE
        df = pd.read_sql(sql=sql_statement,con=db.session.bind)

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

        tables=[df.tail(num_rows).to_html(classes='mystyle',index=False)]
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
    id_to_symbol_mapping = get_id_to_symbol_dict(db)
    
    trans_df = pd.read_sql(sql=db.session.query(Transaction).statement,con=db.session.bind)
    if len(trans_df) < 1:
        return None
    trans_df['invested'] = trans_df['num_shares'] * trans_df['cost_basis']
    #trans_df = trans_df[['symbol_id','invested']]
    by_symbol = trans_df.groupby('symbol_id')
    by_symbol = by_symbol[['num_shares','invested']].sum().reset_index()
    by_symbol['avg_price'] = by_symbol['invested'] / by_symbol['num_shares']

    #by_symbol['symbol'] = sec_df.loc[by_symbol['symbol_id']==sec_df['id']]['symbol']
    by_symbol['symbol'] = by_symbol['symbol_id'].copy()
    by_symbol = by_symbol.replace({'symbol':id_to_symbol_mapping})

    #=====================================================================
    #=====================================================================
    #Designing the Plot
    curdoc().theme = 'dark_minimal'
    source = ColumnDataSource(data=by_symbol)

    plot_fig = figure(x_range=by_symbol['symbol'], y_range=(0, by_symbol['invested'].max() + 200), 
            plot_height=250, title="Money Invested per Security",
            toolbar_location=None, 
            tools=['tap'], 
    )
    hover_tools = HoverTool(
        tooltips=[
                ('symbol','@symbol'),
                ('invested','@invested{($ 0.00 a)}'),
                ('shares','@num_shares{(0.0000)}'),
                ('avg. price','@avg_price{($ 0.00 a)}')
            ],
        formatters={
            '@symbol':'printf'
        }
    )

    plot_fig.add_tools(hover_tools)
    #plot_fig.vbar(x=dodge('symbol', -0.5, range=plot_fig.x_range), top='invested', width=0.4, source=source,
    #   color="#c9d9d3", legend_label="Dollars Invested")

    plot_fig.vbar(x=dodge('symbol',0, range=plot_fig.x_range), top='invested', width=0.8, source=source,
       color="#c9d9d3", legend_label=f"Money Invested (Total: $ {by_symbol['invested'].sum():.2f})")

    plot_fig.x_range.range_padding = 0.1
    plot_fig.xgrid.grid_line_color = None
    plot_fig.legend.location = "top_left"
    plot_fig.legend.orientation = "horizontal"
    plot_fig.xaxis.major_label_orientation = "vertical"

    div_container = Div()
    callback1 = CustomJS(
        args=dict(source=source, div_container=div_container), 
        #use_strict=False,  #deprecated, do not use anymore
        code="""
            var ind = source.selected.indices;
            console.log(ind);
            if (String(ind) != '') {
                var symbol     = source.data['symbol'][ind].toUpperCase();
                var invested   = source.data['invested'][ind].toFixed(2);
                var num_shares = source.data['num_shares'][ind].toFixed(7);
                var avg_price  = source.data['avg_price'][ind].toFixed(2);
                
                var message = '<b>Symbol:  ' + String(symbol)  + '</b><br>Invested: $ ' + String(invested) + '</b><br>Shares: ' + String(num_shares) + '</b><br>Avg. Price: $ ' + String(avg_price);
                div_container.text = message;
            }
            else {
                div_container.text = '';
            }
        """)

    plot_fig.js_on_event('tap', callback1)

    #return plot_fig
    return row(plot_fig,div_container)
    #return plot_fig,div_container

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
    
