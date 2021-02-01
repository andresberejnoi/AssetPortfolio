import datetime
import re

def OLD_get_ticker_dict_data(cmd_str,valid_flags=['-d','-b','-dt','-t','-date']):
    """Given cmd string already parsed (instruction words removed) Ex:
        'aapl .24 123.4, .111 123.5, msft 0.001 200 -d,nrz 2.4 10.1, .19 9.80'
    
    , find
    all ticker symbols and reutrn them in a tuple with their respective actions"""
    
    cmd_str = cmd_str.lower().strip()
    all_actions = [action.strip() for action in cmd_str.split(',')]  #also removing extra spaces from each action
    
    ticker_pattern = r"[a-z]+"
    last_ticker    = ''     #this will keep track of the last ticker symbol processed

    all_tickers_dic = {}   #will hold all of the ticker_dic dictionaries
    ticker_dict = {
        'transactions':[],
        'flags':[]
    }
    
    flag_idx=0    #a convoluted way to match a list of flags with a particular transaction, it resets when a new ticker symbol is found
    for idx,action in enumerate(all_actions):
        #print('action (original):', action)
        #a single action will look like: 'aapl .24 123.4'
        res = re.match(ticker_pattern,action)
                   
        if res:
            ticker = res.group()
            action = re.sub(ticker,'',action).strip()

            if ticker!=last_ticker:          #reset flag index only when new ticker is different  (to prevent cases when user enters same ticker explicitely i.e: add nrz 0.3 200, nrz 4 10.5)
                flag_idx  =0
            else:
                flag_idx += 1
        else:
            if len(last_ticker) > 0:
                ticker    = last_ticker
                flag_idx += 1
            else:
                print(f"Could not find valid ticker symbol in '{action}' string.\n" + \
                      f"Full command string:\n'{cmd_str}'")
                raise ValueError
                   
        #adding data to ticker_dic
        flag_pattern = r"-[a-z]+"   #successfully finds command line arguments like: '-d' '-f' '-install', etc
        flags_list   = [i.strip() for i in re.findall(flag_pattern,action)]   #find all flags and converts them to a list. 
        
        flags = [(flag_idx,flags_list)]      #adding flag_idx to the tuple to match them to the correct transaction
        if flags is None:
            raise ValueError(f"Variable flags is {flags}.")
        else:
            print(f"FLAGS VARIABLE:\n{flags}")
        action = re.sub(flag_pattern,'',action)    #remove flags from working string
        
        #print('action (w/o flags):',action)
        data_items = action.split()
        
        #put transaction data into a tuple (number of shares purchased is first, followed by cost basis)
        num_shares = data_items[0]
        cost_basis = data_items[1]
        transaction = (num_shares,cost_basis)

        #update current ticker dictionary
        if ticker == last_ticker:
            ticker_dict['transactions'].append(transaction)
            ticker_dict['flags'].extend(flags)
        else:
            #print(f"{'*'*10}\n{ticker.upper()}!={last_ticker.upper()}\nCurrent ticker_dict is:\n{ticker_dict}")
            if len(last_ticker)>0:
                all_tickers_dic[last_ticker] = ticker_dict  #we unload the previous ticker data when changing to new ticker
                
            ticker_dict = all_tickers_dic.get(ticker,{'transactions':[],'flags':[]})  #retrieve ticker dic if it has been created before, or create a new dic if it does not exist
            ticker_dict['transactions'].append(transaction)
            ticker_dict['flags'].extend(flags)
        
        ##STOPPING CONDTION: FINAL UNLOAD
        if (idx+1) == len(all_actions):
            #here we submit data from the current (final) round; without this clause, that data is discarded
            all_tickers_dic[ticker] = ticker_dict
            
        last_ticker = ticker     #updating for next round
                   
    return all_tickers_dic

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
                print(f"\n**ERROR CATCHER:\n--> self.flags={self.flags}\n--> idx={idx}\n--> val={val}\n")
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
    ticker_pattern = r"[a-z]+"
    
    #MAIN LOOP
    last_ticker = ''
    transactions_dict = {}   #dict to map ticker symbol to list of TransactionEvent objects
    
    flag_idx=0
    for idx, trans_str in enumerate(raw_transactions):
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
        
        #Parse flags
        flags,trans_str = get_flags(trans_str)  #returns flags and a new string without flags
        
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
            'msft':[<TransactionEvent>,<TransactionEvent>],
            'nrz':[<TransactionEvent>]
        }
    '''
    #this function is mostly a wrapper for command_parser,
    #but I'm keeping this way in case I later need to pre-process the data.

    #replace semi-colons for commas
    #command_str = command_str.replace(';',',')
    tickers_dict = command_parser(command_str)
    return tickers_dict

def OLD_command_engine(command_str,valid_inst=['add','sub','sell','buy'],valid_flags=['-d','-b','-dt','-t','-date']):
    #split between all commands (delimiter is: ';')
    #commands = re.split(',|;',command_str)
    commands = command_str.lower().split(';')
    new_line = '\n'
    #print(f"\nCommands were split as:\n{new_line.join(commands)}\n\n")
    
    inst_and_dicts_tuples = []  #list to hold tuples of (instruction_str,dict)
    for cmd_str in commands:
        #look for the instruction (add, sub, sell, etc)
        instructions_pattern = "|".join(valid_inst)   #creates string like: 'add|sub|sell|buy' for regex
        inst_list = re.findall(instructions_pattern,cmd_str)
        
        if len(inst_list) != 1:
            print(f"Command entered:\n\t-->'{cmd_str}'\nConflict in `inst_list` --> {inst_list}\n\nIt should contain a valid " + \
                  f"instruction word at the beginning. Valid instructions are:\n{valid_inst}")
            raise ValueError
        inst = inst_list[0]
        
        parsed_str = re.sub(instructions_pattern,'',cmd_str)
        
        tickers_dict = command_parser(parsed_str)
        inst_and_dicts_tuples.append((inst,tickers_dict))
        #print(tickers_dict)
    return inst_and_dicts_tuples

def get_flags(flag_string):
    word_pattern     = r"[a-zA-Z]+"
    #time_pattern     = r"[0-9]+\:[0-9]+\:[0-9]+\.[0-9]+"   #this pattern is not flexible
    time_pattern = r"[0-9\:\.]+"
    datetime_pattern = f"[0-9]+\-[0-9]+\-[0-9]+\s*{time_pattern}"
    #wp = r"\s*-([a-zA-Z]+)\s*([a-zA-Z]+|[0-9]+\-[0-9]+\-[0-9]+\s*[0-9\:\.]+|\s*)"  #this string was tested to work sufficiently well for a well formatted string like

    wp = f"\s*-([a-zA-Z]+)\s*({word_pattern}|{datetime_pattern}|{time_pattern}|\s*)"
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
    flags = re.findall(wp,flag_string)

    '''
    #check if flag contains value. If it is empty, remove the empty space (for example in cases when the flag is '-d' and we don't expect a value)
    #This cleaning is commented out for now. I may want to keep the returns consistent (i.e. always as a tuple instead of mixing single strings with tuples)
    cleaned_flags = []
    for flag in flags:
        flag_val = flag[1]
        if len(flag_val) < 1:
            cleaned_flags.append(flag[0])
        else:
            cleaned_flags.append(flag)
    '''
    clean_string = re.sub(wp,'',flag_string)
    print(f"--> get_flags():\n\t{flags}")
    return flags,clean_string