# Changelog for From last Versions

I will list the changes or additions to the project as I go along. I might not list every single thing, but I will try to include at least the most relevant ones. Lastest version should always be written at the top.

---
**----changelog version 0.3.0----**
- Created `__init__.py` file that contains variable `__version__` with version `0.3.0`
- Fixed form resubmission in main page after entering transactions. It was merely a matter of redirecting to the page instead of using `render_template()`
- Added new route `holdings.html` that displays security holdings split in shares held over longer than 366 days (for long term capital gains reasons) and less than 366 days (for short term capital gains).
- `database_operations.py` now collects all split history, even the ones before the first transaction
- `Event` model in `models.py` now stores split factor as a Numeric or Decimal instead of a string
- Created a `Position` model in `models.py`. This new table will hold one row per security and it will contain the current share count and cost basis. This share count will be adjusted for stock splits.

- New module `table_updaters.py` was created to hold functions that modify the database and are called from `app.py`. 
- New function in `tools.py` to compute new share count based on splits. Other convinience functions were also added.
---