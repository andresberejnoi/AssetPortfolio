# Things To Do For Next Update (v0.3.0)

Here I will list the things I hope to get done by the next version of the project. 

- Create official variable for current version, such as `__version__`

- Crypto address tracker implemented:
    - Allows to enter address to track
    - User can indicate if address is his/her own or if it is just for watching (keep this outside the database so that it can be changed at any moment) but it will not be required to enter that information. 
    - Shows current balance in address
    - Can show total transactions in address

- Add more Graphs to the site
    - Modify the plot on main page so that it runs a proper embeded Bokeh server (only if necessary)
    - Add current market data to that plot (superimposed)
    - Create a pie chart of dividend percentages per stock
    - Create a plot or table of payment calendar
    - Add information about current dividend income based on latest dividend information
    - Add graph with Portfolio breakdown by assets (stocks, bonds, ETF, crypto, cash)

- Add procedure to create env.py or env file at the first launch of the program
    - The program should check if an env file exists already, and if it does not, the user will be prompted to enter necessary information that will populate the env file and allow the program to run

- Add page where user can look up stock or crypto by time held
    - The page should list assets held long term (over 12 months) and short term (>12 months) separately so that one can quickly assess holdings
    - Keep it modular. This could eventually be extended for tax calculations.

- Allow user to indicate sub portfolios
    - This can probably be stored in a plain text file and read everytime the program launches. For example, the user can put a list of tickers to be part of a dividend portfolio, while others are in a growth portfolio

- Dividend Increase Script
    - Write a script to regurlarly check the new or current dividends so that I do not have to do that by hand (it will most likely involve some web scrapping)

- Database migration script
    - Make it possible to migrate database to new one if I decide to make a change, such as adding a new column to one of the existing tables. This should preserve the existing data.

- Database Backup Script
    - Write a script that will routinely  perform a backup of the database on some web hosted service, such as Google Drive or Dropbox. The routine part can be handled externally with a cron job from the Raspberry Pi.
    - Script must check if the last backup is different from the current one (maybe use some hash or something to uniquely identify it)
    - Keep a number of past backups (maybe last 5 or 10?)

- Restructure code so that Global information is available from a single location
    - For example, add database location in an environment.

- Start Transition into deployment
    - Create a deployment branch that should be stable
        - Also, learn about deployment and continuous integration (CI)
    - Add tests to use MySQL database, or some other engine compatible with SQLAlchemy and which allows accurate decimal representation of numbers (I need at least 9 decimals of precision). SQLite is the one currently used for testing purposes

