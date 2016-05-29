from telegram.ext import CommandHandler
from .base import MetafetishPickleDBBase
import cgi


class DefinitionManager(MetafetishPickleDBBase):
    def __init__(self, dbdir, cm):
        super().__init__(__name__, dbdir, "definitions", True)
        self.cm = cm

    def register_with_dispatcher(self, dispatcher):
        dispatcher.add_handler(CommandHandler('def', self.show))
        dispatcher.add_handler(CommandHandler('def_show', self.show))
        dispatcher.add_handler(CommandHandler('def_add', self.add))
        dispatcher.add_handler(CommandHandler('def_rm', self.rm))

    def help(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="""
<b>Definitions Module</b>

The definitions module allows users to create definitions for words or phrases. This feature can used to reduce repeated questions about channel topics, or provide extra information in a persistent way.

Entering a new definition is as easy as using the /defadd command.

Each word/phrase can have multiple definitions provided by multiple users.

<b>Commands</b>

%s""" % (self.commands()),
                        parse_mode="HTML")

    def commands(self):
        return """/defhelp - Display definitions help message.
/def - Show definition, if one exists.
/defadd - Add or extend a definition.
/defrm - Remove a definition."""

    def show(self, bot, update):
        def_name = cgi.escape(update.message.text.partition(" ")[2].strip().lower())
        if self.db.get(def_name) is None:
            bot.sendMessage(update.message.chat.id,
                            text='No definition available for %s' %
                            (def_name),
                            parse_mode="HTML")
            return
        def_str = "Definition for <i>%s</i>:\n" % (def_name)
        def_str += self.get_definition_list(def_name)
        bot.sendMessage(update.message.chat.id,
                        text=def_str,
                        parse_mode="HTML",
                        disable_web_page_preview=True)

    def add_definition_conversation(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="Let's add a defintion. What word or phrase would you like to define?")
        (bot, update) = yield
        def_name = cgi.escape(update.message.text.lower())
        update_msg = "Ok, we're defining <i>%s</i>.\n\n" % (def_name)
        if self.db.get(def_name):
            update_msg += "Looks like this has been defined before. What additional definition would you like to give it?"
        else:
            update_msg += "Looks like this is a new term to me. What definition would you like to give it?"
        bot.sendMessage(update.message.chat.id,
                        text=update_msg,
                        parse_mode="HTML")
        (bot, update) = yield
        user_id = update.message.from_user.id
        def_text = cgi.escape(update.message.text)
        self._add_definition(user_id, def_name, def_text)
        update_msg = "Great! The term <i>%s</i> is now defined as:\n\n" % (def_name)
        update_msg += self.get_definition_list(def_name)
        update_msg += "\nAll done! /help"
        bot.sendMessage(update.message.chat.id,
                        text=update_msg,
                        parse_mode="HTML")

    def remove_definition_conversation(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="Let's remove a defintion. What word or phrase would you like to remove a definition from?")
        while True:
            (bot, update) = yield
            def_name = cgi.escape(update.message.text.lower())
            if self.db.get(def_name):
                break
            update_msg = "I can't find <i>%s</i> in my database. Did you mean something else? Try again." % (def_name)
            bot.sendMessage(update.message.chat.id,
                            text=update_msg,
                            parse_mode="HTML")
        update_msg = "Ok, we're removing a definition from <i>%s</i>.\n\nHere's the current definition list:\n%s\n\nEnter the number of the definition would you like to remove." % (def_name, self.get_definition_list(def_name))
        bot.sendMessage(update.message.chat.id,
                        text=update_msg,
                        parse_mode="HTML")
        while True:
            (bot, update) = yield
            user_id = update.message.from_user.id
            try:
                index = int(cgi.escape(update.message.text))
                if index < 1 or self.db.llen(def_name) < index:
                    raise Exception()
                break
            except:
                update_msg = "Doesn't look like %s is a valid definition number. Try again." % (update.message.text)
                bot.sendMessage(update.message.chat.id,
                                text=update_msg)
                continue
        self._remove_definition(user_id, def_name, index - 1)
        update_msg = "Great! Index %d has been removed from term <i>%s</i>." % (index, def_name)
        bot.sendMessage(update.message.chat.id,
                        text=update_msg,
                        parse_mode="HTML")

    def _add_definition(self, user_id, def_name, def_text):
        if self.db.get(def_name) is None:
            self.db.lcreate(def_name)
        d = {"user": user_id,
             "desc": def_text.strip()}
        self.db.ladd(def_name, d)

    def _remove_definition(self, user_id, def_name, def_id):
        self.db.lpop(def_name, def_id)
        if self.db.llen(def_name) is 0:
            self.db.lrem(def_name)

    def get_definition_list(self, def_name):
        def_str = ""
        i = 1
        for d in self.db.lgetall(def_name):
            def_str += "<b>%d.</b> %s\n" % (i, d["desc"])
            i += 1
        return def_str

    def add(self, bot, update):
        c = self.add_definition_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def rm(self, bot, update):
        c = self.remove_definition_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def list(self, bot, update):
        def_list = ", ".join([x for x in self.db.getall()])
        bot.sendMessage(update.message.chat.id,
                        text='Words/Phrases with definitions:\n%s' %
                        (def_list),
                        parse_mode="HTML",
                        disable_web_page_preview=True)
