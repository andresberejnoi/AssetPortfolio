import json     #just for printing dictionaries in an easy-to-read way
import sys
from command_engine import command_engine

def check_command_engine(test_cases):
    '''
    test_cases: list of strings (test cases for the engine)
    '''
    for i,test in enumerate(test_cases):
        print('='*30)
        print(f"TEST #{i+1}\nInput string:\n'{test}'\n\n")
        try:
            list_of_dicts = command_engine(test)
        except ValueError as e:
            print(e)

        for inst,d in list_of_dicts:
            print(f"Instruction: {inst.upper()}\n{json.dumps(d,indent=3)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        test_set = 'one'
    else:
        test_set = sys.argv[1]
        
    one_test_cases = ['add aapl .24 123.4, 0.3 200, msft 0.001 200 -d,nrz 2.4 10.1, .19 9.80, aapl 0.5 203, t 3.5 29.8',
                      'add aapl .24 123.4, msft 0.001 200 -d,nrz 2.4 10.1, .19 9.80;sub wmt 3 214.8',
                      'add aapl .24 123.4, msft 0.001 200 -d,nrz 2.4 10.1, .19 9.80',
                      'add 0.345 201 , nrz 10 10, vz 0.3 60; add amzn 0.004 3160,voo 0.001 336',
                      'add nrz 12.3 10.0',
                      'add aapl 23.5 200',
                      '',
                      '-d',]

    two_test_cases = ['add nrz 12.3 10.0;sub amzn 0.3 4000; add aapl 10 100',]

    three_test_cases = [
        'add nrz 5 10.5, nrz 3 10 -d',
        'add aapl 0.5 200 -d, 0.5 201',
        'add aapl 0.5 200 -d, 0.5 201, msft 0.4 100 -d, 40 200 -d, msft 1 200 -d, nrz 10 10 -d',
    ]

    tests = {
        'one'  : one_test_cases,
        'two'  : two_test_cases,
        'three': three_test_cases,
    }
    check_command_engine(tests[test_set])