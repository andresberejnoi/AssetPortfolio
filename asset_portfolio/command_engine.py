import datetime
import re

def get_ticker_dic_data(cmd_str,valid_flags=['-d']):
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


def command_engine(command_str,valid_inst=['add','sub','sell','buy'],valid_flags=['-d']):
    #split between all commands (delimiter is: ';')
    #commands = re.split(',|;',command_str)
    commands = command_str.lower().split(';')
    new_line = '\n'
    #print(f"\nCommands were split as:\n{new_line.join(commands)}\n\n")
    
    inst_and_dicts_tuples = []  #list to hold tuples of (instruction,dict)
    for cmd_str in commands:
        #look for the instruction (add, sub, sell, etc)
        instructions_pattern = "|".join(valid_inst)   #creates string like: 'add|sub|sell|buy' for regex
        inst_list = re.findall(instructions_pattern,cmd_str)
        
        if len(inst_list) != 1:
            print(f"Command entered:\n'{cmd_str}'.\n\nIt should contain valid a " + \
                  f"instruction word at the beginning. Valid instructions are:\n{valid_inst}")
            raise ValueError
        inst = inst_list[0]
        
        parsed_str = re.sub(instructions_pattern,'',cmd_str)
        
        tickers_dict = get_ticker_dic_data(parsed_str,valid_flags)
        inst_and_dicts_tuples.append((inst,tickers_dict))
        #print(tickers_dict)
    return inst_and_dicts_tuples

def flag_processing(flag_string):
    wp = r"\s*-([a-zA-Z]+)\s*([a-zA-Z]+|[0-9]+\-[0-9]+\-[0-9]+\s*[0-9\:\.]+|\s*)"  #this string was tested to work sufficiently well for a well formatted string like

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