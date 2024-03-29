import datetime
import re


class TransactionEvent(object):
    '''Storage object for transaction Events. It seems more organized than keeping
    a bunch of lists of tuples of lists and dicts. There are some useful external methods
    such as is_dividend() to return a boolean if the transaction is a dividend payment.'''
    DIVIDEND_FLAG = 'div'
    BROKER_FLAG   = 'b'
    DT_FLAG       = 'dt'
    TIME_FLAG     = 't'
    DATE_FLAG     = 'date'

    DEFAULT_BROKER = 'robinhood'
    def __init__(self, ticker,amount,cost_basis,flags=[]):
        self._ticker = ticker
        self._amount = amount
        self._cost_basis = cost_basis
        self.flag_list = flags  #list of tuples
        
        #set datetime value
        self._datetime = None 
        self._set_datetime()
        
    
    def _set_datetime(self):
        """sets datetime value from flags and also deletes those flags from self.flag_list after it's done"""
        if len(self.flag_list) > 0:
            flags,vals = zip(*self.flag_list) #split list of tuples into two lists
        else:
            self._datetime = datetime.datetime.utcnow()
            return 

        #----
        indexes_to_delete = []
        if (self.DATE_FLAG in flags) and (self.TIME_FLAG not in flags):
            idx = flags.index(self.DATE_FLAG)
            val = vals[idx]
            date = datetime.datetime.fromisoformat(val)
            time = datetime.time(hour=8,minute=0)
            self._datetime = datetime.datetime.combine(date,time)
            indexes_to_delete.append(idx)

        elif (self.TIME_FLAG in flags) and (self.DATE_FLAG not in flags):
            idx = flags.index(self.TIME_FLAG)
            val = vals[idx]
            date = datetime.datetime.utcnow().date()
            time = datetime.time.fromisoformat(val)
            self._datetime = datetime.datetime.combine(date,time)
            indexes_to_delete.append(idx)

        elif (self.DATE_FLAG in flags) and (self.TIME_FLAG in flags):
            idx_date = flags.index(self.DATE_FLAG)
            idx_time = flags.index(self.self.TIME_FLAG)
            
            date_str = vals[idx_date]
            time_str = vals[idx_time]
            dt_str   = f"{date_str} {time_str}"
            self._datetime = datetime.datetime.fromisoformat(dt_str)
            indexes_to_delete.append(idx_date)
            indexes_to_delete.append(idx_time)

        else: #when neither date or time flags are present
            if self.DT_FLAG in flags:
                idx = flags.index(self.DT_FLAG)
                val = vals[idx]
                #print(f"\n**ERROR CATCHER:\n--> self.flags={self.flags}\n--> idx={idx}\n--> val={val}\n")
                self._datetime = datetime.datetime.fromisoformat(val)
                indexes_to_delete.append(idx)
            else:
                #self._datetime = datetime.datetime.utcnow()
                self._datetime = None  #return none for now. It will be handled server side on mysql


        #here I delete the flags from flag list since they have a dedicated variable
        for idx_pos in sorted(indexes_to_delete,reverse=True):
            del self.flag_list[idx_pos]

    def is_dividend(self):
        if len(self.flags) < 1:
            return False 
        
        flags,vals = zip(*self.flags)
        if self.DIVIDEND_FLAG in flags:
            return True 
        else:
            return False

    def get_broker(self):
        if len(self.flags) < 1:
            return self.DEFAULT_BROKER

        flags,vals = zip(*self.flags)
        if self.BROKER_FLAG in flags:
            idx = flags.index(self.BROKER_FLAG)
            broker = vals[idx]
        else:
            broker = 'robinhood'  #default broker for now
        return broker

    #-----Read-only methods
    @property
    def ticker(self):
        return self._ticker
    @property
    def amount(self):
        return self._amount
    @property
    def cost_basis(self):
        return self._cost_basis
    @property
    def datetime(self):
        return self._datetime
    @property
    def date(self):
        try:
            date = self.datetime.date()
        except AttributeError:
            date = None
        return date
    @property
    def time(self):
        try:
            time = self.datetime.time()
        except AttributeError:
            time = None
        return time
    @property
    def flags(self):
        return self.flag_list
    @property 
    def broker(self):
        return self.get_broker()
    
    def __repr__(self):
        return f"<TransactionEvent>: {self.ticker:>5} {float(self.amount):.7f} {float(self.cost_basis):.4f} {self.date} {self.time:%H:%M:%S} {self.flags}"
   

def command_parser(cmd_str):   #aka get_ticker_dict_data
    """Processes a command str without the instruction word ('add','sell','sub','buy',etc)"""
    #clean-up process
    cmd_str          = cmd_str.lower().strip()
    raw_transactions = [transaction.strip() for transaction in cmd_str.split(',')]   #each transaction is separated by a comma
    
    #patterns
    ticker_pattern = r"[a-zA-Z]+"  #could use some alteration of r"(?<!-)[a-zA-Z]+" to ignore flags, but it is already taken care of
    
    #================MAIN LOOP
    last_ticker = ''
    transactions_dict = {}   #dict to map ticker symbol to list of TransactionEvent objects
    
    flag_idx=0
    for idx, trans_str in enumerate(raw_transactions):

        #Parse flags
        flags,trans_str = get_flags(trans_str)  #returns flags and a new string without flags

        # Match the ticker symbol
        res = re.match(ticker_pattern,trans_str)
        if res:
            ticker = res.group()
            trans_str = re.sub(ticker,'',trans_str).strip()  #remove ticker from string
            
            if ticker!=last_ticker:          #reset flag index only when new ticker is different  (to prevent cases when user enters same ticker explicitely i.e: add nrz 0.3 200, nrz 4 10.5)
                flag_idx  =0
            else:
                flag_idx += 1
        else:
            if len(last_ticker) > 0:
                ticker    = last_ticker
                flag_idx += 1
            else:
                print(f"Could not find valid ticker symbol in '{trans_str}' string.\n" + \
                      f"Full command string:\n'{cmd_str}'")
                raise ValueError
        
        
        
        #Determine the parameters of the transaction (amount, cost_basis, etc)
        trans_items = trans_str.split()
        num_shares  = trans_items[0]
        cost_basis  = trans_items[1]
        
        t = TransactionEvent(ticker=ticker,
                             amount=num_shares,
                             cost_basis=cost_basis,
                             flags=flags)
        try:
            transactions_dict[ticker].append(t)
        
        except KeyError:
            transactions_dict[ticker] = [t]   #create list with first item
        last_ticker = ticker
    
    return transactions_dict 

def command_engine(command_str):
    '''
    Parses String containing stock transactions. To simplify things, there is no 
    instruction word, just a list of instructions separated by commas. The old function
    used to use semi-colons to separate between instructions (add, sub, buy, sell), but
    since they are not used anymore, the code will raise an exemption for it.

    Parameters
    ----------
    command_str: str
        The string to parse. It should contain comma-separated transactions. For example:
        aapl 3.5 148.5 -div -b robinhood, msft 10 220.8 -b robinhood, nrz 5 9.68

    
    Returns
    -------
    dict
        Dictionary mapping ticker symbols to a list of TransactionEvent objects. Example:
        {
            'aapl':[<TransactionEvent>, <TransactionEvent>, <TransactionEvent>, ...],
            'msft':[<TransactionEvent>,<TransactionEvent>, ...],
            'nrz':[<TransactionEvent>]
        }
    '''
    #this function is mostly a wrapper for command_parser,
    #but I'm keeping this way in case I later need to pre-process the data.

    #replace semi-colons for commas
    #command_str = command_str.replace(';',',')
    tickers_dict = command_parser(command_str)
    return tickers_dict


def get_flags(flag_string):
    """
    Sample string: 
    s  = 'python main.py -f hello -d  -broker          robinhood -t 2000-10-01           14:44:20.999 -D -R'

    result from re.findall(wp,s):

        [('f', 'hello'),
        ('d', ''),
        ('broker', 'robinhood'),
        ('t', '2000-10-01           14:44:20.999'),
        ('D', ''),
        ('R', '')]
    """
    word_pattern     = r"[a-zA-Z]+"
    #time_pattern     = r"[0-9]+\:[0-9]+\:[0-9]+\.[0-9]+"   #this pattern is not flexible
    time_pattern = r"[0-9\:\.]+"
    datetime_pattern = f"[0-9]+\-[0-9]+\-[0-9]+\s*{time_pattern}"
    #wp = r"\s*-([a-zA-Z]+)\s*([a-zA-Z]+|[0-9]+\-[0-9]+\-[0-9]+\s*[0-9\:\.]+|\s*)"  #this string was tested to work sufficiently well for a well formatted string like

    wp = f"\s*-([a-zA-Z]+)\s*({word_pattern}|{datetime_pattern}|{time_pattern}|\s*)"
    
    flags = re.findall(wp,flag_string)

    clean_string = re.sub(wp,'',flag_string)
    #print(f"--> get_flags():\n\t{flags}\n\tOriginal String: {flag_string}")
    return flags,clean_string