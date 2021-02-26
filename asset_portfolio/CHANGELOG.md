# Changelog for From last Versions

I will list the changes or additions to the project as I go along. I might not list every single thing, but I will try to include at least the most relevant ones. Lastest version should always be written at the top.

---
**----changelog version 0.3.0----**
- Created `__init__.py` file that contains variable `__version__` with version `0.3.0`
- Fixed form resubmission in main page after entering transactions. It was merely a matter of redirecting to the page instead of using `render_template()`
- Added new route `holdings.html` that displays security holdings split in shares held over longer than 366 days (for long term capital gains reasons) and less than 366 days (for short term capital gains).

---