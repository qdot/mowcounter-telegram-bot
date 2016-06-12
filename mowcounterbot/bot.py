from telegram.ext import MessageHandler, Filters
from nptelegrambot import NPTelegramBot, ConversationHandler, PermissionCommandHandler
from nptelegrambot.chats import ChatFilters
from .mowcounter import MowCounter
from functools import partial


class MowCounterTelegramBot(NPTelegramBot):
    def __init__(self, config):
        super().__init__(config)
        self.mow = MowCounter(self.store)

    def setup_commands(self):
        super().setup_commands()
        self.dispatcher.add_handler(MessageHandler([Filters.sticker],
                                                   self.handle_message),
                                    group=1)
        self.dispatcher.add_handler(MessageHandler([Filters.text,
                                                    Filters.sticker],
                                                   self.handle_mow), group=3)
        self.dispatcher.add_handler(MessageHandler([Filters.text,
                                                    Filters.sticker],
                                                   self.chats.run_join_checks), group=4)

        self.chats.add_join_filter(partial(ChatFilters.min_size_filter,
                                           min_size=10))

        # Definition module commands
        self.dispatcher.add_handler(PermissionCommandHandler('mowtop10',
                                                             [],
                                                             self.mow.show_top10_count))
        self.dispatcher.add_handler(PermissionCommandHandler('mowcount',
                                                             [],
                                                             self.mow.show_own_count))
        self.dispatcher.add_handler(PermissionCommandHandler('mowreset',
                                                             [self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.mow.reset))
        self.dispatcher.add_handler(ConversationHandler('mowrequeststicker',
                                                        [self.require_privmsg],
                                                        self.conversations,
                                                        self.mow.request_sticker))
        self.dispatcher.add_handler(PermissionCommandHandler('mowstickers',
                                                             [self.require_privmsg],
                                                             self.mow.list_stickers))
        self.dispatcher.add_handler(ConversationHandler('mowreviewstickers',
                                                        [self.require_privmsg,
                                                         partial(self.require_flag, flag="admin")],
                                                        self.conversations,
                                                        self.mow.review_stickers))

        # On errors, just print to console and hope someone sees it
        self.dispatcher.add_error_handler(self.handle_error)

    def handle_help(self, bot, update):
        help_text = ["Hi! I'm @mowcounter_bot, the bot that counts mows.",
                     "",
                     "If you mow in a channel I'm in, I count it. The end.",
                     "",
                     "I'm open to be invited to any channel, so if you have a place that needs mows counted, just invite me!",
                     "",
                     "If you have any questions, my owner is @qdot76367. I'm an open source bot, too! Feel free to run your own. http://github.com/qdot/mow-counter-bot/",
                     "",
                     "Here's a list of commands I support:",
                     "",
                     "/mowcount - show how many times you've mowed.",
                     "/mowtop10 - show mow high score table.",
                     "/mowrequeststicker - request a sticker be added to count for mows."]
        bot.sendMessage(update.message.chat.id,
                        "\n".join(help_text),
                        parse_mode="HTML",
                        disable_web_page_preview=True)

    def handle_mow(self, bot, update):
        # Ignore messages not in groups
        if update.message.chat.id > 0:
            return
        self.mow.check_mows(bot, update)


def create_webhook_bot(config):
    bot = MowCounterTelegramBot(config)
    bot.setup_commands()
    bot.start_webhook_thread()
    return bot

