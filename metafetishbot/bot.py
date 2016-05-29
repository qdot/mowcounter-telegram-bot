from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from .permissioncommandhandler import PermissionCommandHandler
from .users import UserManager
from .groups import GroupManager
from .conversations import ConversationManager
from .mowcounter import MowCounter
from threading import Thread
import argparse
import os
import logging
from functools import partial


class MowCounterTelegramBot(object):
    FLAGS = ["admin", "def_edit", "user_flags"]

    def __init__(self, dbdir, tg_token):
        if not dbdir or not os.path.isdir(dbdir):
            print("Valid database directory required!")
            raise RuntimeError()
        self.logger = logging.getLogger(__name__)
        self.updater = Updater(token=tg_token)
        self.dispatcher = self.updater.dispatcher
        self.conversations = ConversationManager()
        self.users = UserManager(dbdir, self.conversations)
        self.groups = GroupManager(dbdir)
        self.mow = MowCounter(dbdir, self.conversations)

        self.modules = [self.users, self.groups, self.mow]

        # Make sure the message handlers are in different groups so they are
        # always run
        self.dispatcher.add_handler(MessageHandler([Filters.text, Filters.sticker],
                                                   self.handle_message), group=1)

        self.dispatcher.add_handler(MessageHandler([Filters.text, Filters.sticker],
                                                   self.handle_mow), group=2)

        # Default commands
        self.dispatcher.add_handler(PermissionCommandHandler('start',
                                                             [self.try_register,
                                                              self.require_privmsg],
                                                             self.handle_start))
        self.dispatcher.add_handler(PermissionCommandHandler('help',
                                                             [self.try_register,
                                                              self.require_privmsg],
                                                             self.handle_help))
        self.dispatcher.add_handler(PermissionCommandHandler('settings',
                                                             [self.try_register,
                                                              self.require_privmsg],
                                                             self.handle_settings))
        self.dispatcher.add_handler(CommandHandler('cancel',
                                                   self.handle_cancel))

        # Admin commands
        self.dispatcher.add_handler(PermissionCommandHandler('userlist',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.users.show_list))
        self.dispatcher.add_handler(PermissionCommandHandler('useraddflag',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.users.add_flag))
        self.dispatcher.add_handler(PermissionCommandHandler('userrmflag',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.users.remove_flag))
        self.dispatcher.add_handler(PermissionCommandHandler('groupadd',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.groups.add_group))
        self.dispatcher.add_handler(PermissionCommandHandler('grouprm',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.groups.rm_group))
        self.dispatcher.add_handler(PermissionCommandHandler('outputcommands',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.output_commands))

        # Definition module commands
        self.dispatcher.add_handler(PermissionCommandHandler('mowtop10',
                                                             [self.require_group,
                                                              self.try_register],
                                                             self.mow.show_top10_count))
        self.dispatcher.add_handler(PermissionCommandHandler('mowcount',
                                                             [self.require_group,
                                                              self.try_register],
                                                             self.mow.show_own_count))
        self.dispatcher.add_handler(PermissionCommandHandler('mowaddsticker',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.mow.add_sticker))
        self.dispatcher.add_handler(PermissionCommandHandler('mowrmsticker',
                                                             [self.try_register,
                                                              self.require_privmsg,
                                                              partial(self.require_flag, flag="admin")],
                                                             self.mow.rm_sticker))

        # On errors, just print to console and hope someone sees it
        self.dispatcher.add_error_handler(self.handle_error)

    def handle_start(self, bot, update):
        user_id = update.message.from_user.id
        start_text = ["Hi! I'm @metafetish_bot, the bot for the MowCounter Telegram Group Network.", ""]
        should_help = False
        if len(self.groups.get_groups()) > 0 and not self.groups.user_in_groups(bot, user_id):
            start_text += ["Before we get started, you'll need to join one of the following groups:"]
            for g in self.groups.get_groups():
                start_text += ["- %s" % (g)]
            start_text += ["Once you've joined, message me with /start again and we can continue!"]
        else:
            start_text += ["It looks like you're in one of my groups, so let's get started!", ""]
            should_help = True

        bot.sendMessage(update.message.chat.id,
                        "\n".join(start_text))
        if should_help:
            self.handle_help(bot, update)

    def handle_help(self, bot, update):
        user_id = update.message.from_user.id
        if (len(self.groups.get_groups()) > 0 and not self.groups.user_in_groups(bot, user_id)) or not self.users.is_valid_user(user_id):
            self.handle_start(bot, update)
            return
        help_text = ["Hi! I'm @mowcounter_bot, the bot that counts mows.",
                     "",
                     "If you mow in a channel I'm in, I count it. The end.", 
                     "",
                     "Here's a list of commands I support:",
                     "",
                     "/mowcount - show how many times you've mowed.",
                     "/mowtop10 - show mow high score table."]
        bot.sendMessage(update.message.chat.id,
                        "\n".join(help_text),
                        parse_mode="HTML")

    def handle_settings(self, bot, update):
        pass

    def handle_error(self, bot, update, error):
        self.logger.warn("Exception thrown! %s", self.error)

    def try_register(self, bot, update):
        user_id = update.message.from_user.id
        if not self.users.is_valid_user(user_id):
            self.users.register(bot, update)
        # Always returns true, as running any command will mean the user is
        # registered. We just want to make sure they're in the DB so flags can
        # be added if needed.
        return True

    def require_group(self, bot, update):
        # Special Case: If the bot has no users yet, we need to let the first
        # user register so they can be an admin. After that, always require
        # membership
        if self.users.get_num_users() == 0:
            return True
        if len(self.groups.get_groups()) == 0:
            return True
        user_id = update.message.from_user.id
        if not self.groups.user_in_groups(bot, user_id):
            bot.sendMessage(update.message.chat.id,
                            text="Please join the 'metafetish' group to use this bot! http://telegram.me/metafetish")
            return False
        return True

    # When used with PermissionCommandHandler, Function requires currying with
    # flag we want to check for.
    def require_flag(self, bot, update, flag):
        user_id = update.message.from_user.id
        if not self.users.has_flag(user_id, flag):
            bot.sendMessage(update.message.chat.id,
                            text="You do not have the required permissions to run this command.")
            return False
        return True

    def require_privmsg(self, bot, update):
        if update.message.chat.id < 0:
            bot.sendMessage(update.message.chat.id,
                            reply_to_message_id=update.message.id,
                            text="Please message that command to me. Only the following commands are allowed in public chats:\n- /def")
            return False
        return True

    def output_commands(self, bot, update):
        command_str = ""
        for m in self.modules:
            command_str += m.commands() + "\n"
        bot.sendMessage(update.message.chat.id,
                        text=command_str)

    def handle_message(self, bot, update):
        # Ignore messages from groups
        if update.message.chat.id < 0:
            return
        if self.conversations.check(bot, update):
            return
        self.try_register(bot, update)
        self.handle_help(bot, update)

    def handle_mow(self, bot, update):
        # Ignore messages not in groups
        # if update.message.chat.id > 0:
        #     return
        self.mow.check_mows(bot, update)

    def handle_cancel(self, bot, update):
        if update.message.chat.id < 0:
            return
        if not self.conversations.cancel_conversation(bot, update):
            bot.sendMessage(update.message.chat.id,
                            text="Don't have anything to cancel!")
            self.handle_help(bot, update)
            return
        bot.sendMessage(update.message.chat.id,
                        text="Command canceled!")

    def start_loop(self):
        self.updater.start_polling()
        self.updater.idle()

    def shutdown(self):
        for m in self.modules:
            m.shutdown()


class MowCounterTelegramBotCLI(MowCounterTelegramBot):
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--dbdir", dest="dbdir",
                            help="Directory for pickledb storage")
        parser.add_argument("-t", "--token", dest="token_file",
                            help="File containing telegram API token")
        args = parser.parse_args()

        if not args.token_file:
            print("Token file argument required!")
            parser.print_help()
            raise RuntimeError()

        try:
            with open(args.token_file, "r") as f:
                tg_token = f.readline().strip()
        except:
            print("Cannot open token file!")
            raise RuntimeError()

        if not args.dbdir or not os.path.isdir(args.dbdir):
            print("Valid database directory required!")
            parser.print_help()
            raise RuntimeError()
        super().__init__(args.dbdir, tg_token)


class MowCounterTelegramBotThread(MowCounterTelegramBot):
    def __init__(self, dbdir, tg_token):
        super().__init__(dbdir, tg_token)
        # Steal the queue from the updater.
        self.update_queue = self.updater.update_queue

        # Start the thread
        self.thread = Thread(target=self.dispatcher.start, name='dispatcher')
        self.thread.start()

    def add_update(self, update):
        self.update_queue.put(update)

    def shutdown(self):
        self.thread.join(1)
        super().shutdown()

