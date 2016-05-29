#!/usr/bin/python3

import logging
from mowcounterbot import MowCounterTelegramBotCLI

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    try:
        bot = MowCounterTelegramBotCLI()
    except RuntimeError:
        return 0
    print("Starting up bot")
    bot.start_loop()
    bot.shutdown()
    print("Shutting down bot")


if __name__ == "__main__":
    main()
