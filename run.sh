#!/bin/sh
watchmedo auto-restart --pattern="*.py" -R -- python3.4 mowcounter_bot.py --token=token.txt --dbdir=dbs
