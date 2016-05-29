from .base import MetafetishPickleDBBase


class MowCounter(MetafetishPickleDBBase):
    def __init__(self, dbdir, cm):
        # Don't save on every write transactions. Fucking noisy sneps.
        super().__init__(__name__, dbdir, "mowcounter", False)
        try:
            self.stickers = self.db.lgetall("stickers")
        except KeyError:
            self.db.lcreate("stickers")
            self.stickers = self.db.lgetall("stickers")
        if self.db.get("mowers") is not None:
            self.mowers = self.db.dgetall("mowers")
        else:
            self.db.dcreate("mowers")
            self.mowers = self.db.dgetall("mowers")
        self.cm = cm

    def reset_conversation(self, bot, update):
        pass

    def reset(self, bot, update):
        c = self.reset_conversation(bot, update)
        c.send(None)
        self.cm.add(c)

    def add_sticker_conversation(self, bot, update):
        sticker = None
        while True:
            bot.sendMessage(update.message.chat.id,
                            text="Send me the sticker you'd like to add, or /cancel.")
            (bot, update) = yield
            if update.message.sticker is not None:
                sticker = update.message.sticker
                break
            bot.sendMessage(update.message.chat.id,
                            text="That's not a sticker!")
        if sticker.file_id in self.stickers:
            bot.sendMessage(update.message.chat.id,
                            text="I'm already counting that sticker!")
            return
        self.stickers.append(sticker.file_id)
        self.db.ladd("stickers", sticker.file_id)
        self.db.dump()
        bot.sendMessage(update.message.chat.id,
                        text="Sticker added!")

    def rm_sticker_conversation(self, bot, update):
        sticker = None
        while True:
            bot.sendMessage(update.message.chat.id,
                            text="Send me the sticker you'd like to add, or /cancel.")
            (bot, update) = yield
            if update.message.sticker is not None:
                sticker = update.message.sticker
                break
            bot.sendMessage(update.message.chat.id,
                            text="That's not a sticker!")
        if sticker.file_id in self.stickers:
            bot.sendMessage(update.message.chat.id,
                            text="I'm already counting that sticker!")
            return
        self.stickers.remove(sticker.file_id)
        self.db.lrem(sticker.file_id)
        self.db.dump()
        bot.sendMessage(update.message.chat.id,
                        text="Sticker removed!")

    def add_sticker(self, bot, update):
        c = self.add_sticker_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def rm_sticker(self, bot, update):
        c = self.rm_sticker_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def check_mows(self, bot, update):
        self.logger.warn("CALLING MOW COUNTER")
        user_id = str(update.message.from_user.id)
        user = update.message.from_user
        mows = 0
        # The API tests for text as either text or '', not None. God damnit.
        if len(update.message.text) is not 0:
            # count mows
            mows = update.message.text.lower().count("mow")
        elif update.message.sticker is not None:
            sticker = update.message.sticker
            if sticker.file_id in self.stickers:
                mows = 1
        if mows is 0:
            self.logger.warn("Got no mows!")
            return
        self.logger.warn("Counted %d mows" % mows)
        if user_id not in self.mowers.keys():
            self.mowers[user_id] = { "mows": mows,
                                     "first_name": user.first_name,
                                     "last_name": user.last_name
                                     }
        else:
            self.mowers[user_id] = { "mows": mows + self.mowers[user_id]["mows"],
                                     "first_name": user.first_name,
                                     "last_name": user.last_name
                                     }

    def dump(self):
        self.db.dump()

    def show_own_count(self, bot, update):
        user_id = str(update.message.from_user.id)
        user = update.message.from_user
        if user_id not in self.mowers.keys():
            bot.sendMessage(update.message.chat.id,
                            text="%s %s has no mows!" % (user.first_name, user.last_name))
            return
        bot.sendMessage(update.message.chat.id,
                        text="%s %s has mowed %d times." % (user.first_name, user.last_name, self.mowers[user_id]["mows"]))
        self.db.dump()

    def show_top10_count(self, bot, update):
        mowers = sorted(self.mowers.items(), key=lambda x: x[1]["mows"], reverse=True)[:10]
        top10 = "<b>Top 10 Mowers:</b>\n\n"
        i = 0
        for (id, mower) in mowers:
            i += 1
            top10 += "<b>%d.</b> %s %s - %d Mows\n" % (i, mower["first_name"], mower["last_name"], mower["mows"])
        bot.sendMessage(update.message.chat.id,
                        text=top10,
                        parse_mode="HTML")
        self.db.dump()
