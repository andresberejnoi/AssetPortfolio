"""Collection of tools to use in different situations"""



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