import holoviews as hv
import panel as pn
import param
import pandas as pd
#from models import db
from models import (Security, Transaction, Broker, 
                    Event, CryptoCurrency, CryptoWallet)

#based on example here: http://holoviews.org/user_guide/Dashboards.html
# 
class TransactionExplorer(param.Parameterized):
    def __init__(self,database,app=None):
        self.db = database
        self.app = app
        if self.app is None:
            '''get some app context or something'''
        else:
            pass
        
        self.symbols_dict = self._get_id_symbol_dict()

        #the example shows this next part placed as class variables
        self.symbol_widget = param.ObjectSelector(default='vz', objects=self.symbols)
        
    
    @param.depends('symbol_widget')
    def load_symbol_transactions(self):
        #symbol_id = self.symbols_dict[]
        with self.app.app_context():
            data_df = pd.read_sql(sql=self.db.session.query(Transaction).statement,con=self.db.session.bind)#.filter(Security))
            data_df['invested'] = data_df['num_shares'] * data_df['cost_basis']
        bars = hv.Bars(data_df, hv.Dimension('symbol_id'), 'invested').opts(framewise=True)

    #============================
    #   Helper functions
    def _get_id_symbol_dict(self):
        with self.app.app_context():
            return dict(self.db.session.query(Security.id,Security.symbol).all())

    @property
    def symbols(self):
        return [self.symbols_dict[id] for id in self.symbols_dict]