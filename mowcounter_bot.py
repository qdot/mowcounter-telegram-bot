#!/usr/bin/python3

import sys
import logging
from mowcounterbot import MowCounterTelegramBot

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    try:
        bot = MowCounterTelegramBot(MowCounterTelegramBot.parse_cli_arguments())
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    print("Starting up bot")
    bot.setup_commands()
    bot.start_loop()
    bot.shutdown()
    print("Shutting down bot")

if __name__ == "__main__":
    main()
