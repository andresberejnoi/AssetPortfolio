"""This is just a prototype file. The real deal will come later, after some experimentation"""
from command_engine import command_engine
import json
import time

def main(args):
    #run main loop 
    init_str = f"""{'-'*80}\n\t\tPORTFOLIO AND ASSET TRACKER\n{'-'*80}\nHere you can enter your new purchases:\n"""
    print(init_str)
    #user_input = ''
    while True:
        user_input = input(f"\n{'-'*10}\nCommand:\n\t-> ")

        if user_input.lower() == 'exit':
            break
        actions = command_engine(user_input)

        print(f"Detected {len(actions)} number of different ticker transactions.\n"+ \
              "Here they are:\n")
        for inst,act_dict in actions:
            print(f"Instruction: {inst.upper()}\n{json.dumps(act_dict,indent=2)}")
    
        time.sleep(2)

    print(f"{'-'*16}\nPROGRAM FINISHED\n{'-'*16}")

if __name__ == '__main__':
    args=None
    main(args)