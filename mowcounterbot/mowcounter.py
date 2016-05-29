from .base import MetafetishPickleDBBase


class MowCounter(MetafetishPickleDBBase):
    def __init__(self, dbdir, cm):
        # Don't save on every write transactions. Fucking noisy sneps.
        super().__init__(__name__, dbdir, "mowcounter", False)
        self.stickers = self.db.get("stickers")
        # stickers used to be a list. Now it should be a dict
        if self.stickers is None or type(self.stickers) is list:
            self.db.dcreate("stickers")
            self.stickers = self.db.dgetall("stickers")
        self.sticker_requests = self.db.get("sticker_requests")
        if self.sticker_requests is None:
            self.db.lcreate("sticker_requests")
            self.sticker_requests = self.db.get("sticker_requests")
        if self.db.get("mowers") is None:
            self.db.dcreate("mowers")
        self.mowers = self.db.dgetall("mowers")
        if self.db.get("mowgroups") is None:
            self.db.dcreate("mowgroups")
        self.mowgroups = self.db.dgetall("mowgroups")
        self.cm = cm

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
        user_id = str(update.message.from_user.id)
        chat_id = str(update.message.chat.id)
        user = update.message.from_user
        mows = 0
        # The API tests for text as either text or '', not None. God damnit.
        if len(update.message.text) is not 0:
            # count mows. Maximum one mow per message
            mows = 1 if update.message.text.lower().count("mow") else 0
        elif update.message.sticker is not None:
            sticker = update.message.sticker
            # Make sure we have the sticker and it's accepted
            if sticker.file_id not in self.stickers.keys():
                return
            mows = self.stickers[sticker.file_id]
        if mows is 0:
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
        # We know that we'll have names stored in the global table, so just
        # store id and count in group tables.
        if chat_id not in self.mowgroups.keys():
            self.mowgroups[chat_id] = {}
        if user_id not in self.mowgroups[chat_id].keys():
            self.mowgroups[chat_id][user_id] = mows
        else:
            self.mowgroups[chat_id][user_id] += mows

    def dump(self):
        self.db.dump()

    def show_own_count(self, bot, update):
        user_id = str(update.message.from_user.id)
        chat_id = str(update.message.chat.id)
        user = update.message.from_user
        if user_id not in self.mowers.keys():
            bot.sendMessage(update.message.chat.id,
                            text="%s %s has no mows!" % (user.first_name, user.last_name))
            return
        globallist = sorted(self.mowers.items(),
                            key=lambda x: x[1]["mows"], reverse=True)
        global_rank = [x[0] for x in globallist].index(user_id) + 1
        global_size = len(globallist)
        group_mows = 0
        group_rank = 0
        group_size = 0
        if chat_id in self.mowgroups and user_id in self.mowgroups[chat_id]:
            group_mows = self.mowgroups[chat_id][user_id]
            grouplist = sorted(self.mowgroups[chat_id].items(),
                               key=lambda x: x[1], reverse=True)
            group_rank = [x[0] for x in grouplist].index(user_id) + 1
            group_size = len(grouplist)
        bot.sendMessage(update.message.chat.id,
                        text="%s %s has mowed %d times in this group (Rank: %d of %d), and %d times globally (Rank: %d of %d)." % (user.first_name, user.last_name, group_mows, group_rank, group_size, self.mowers[user_id]["mows"], global_rank, global_size))
        self.db.dump()

    def show_top10_count(self, bot, update):
        chat_id = str(update.message.chat.id)
        grouptop10 = ""
        if chat_id in self.mowgroups.keys():
            groupmowers = sorted(self.mowgroups[chat_id].items(),
                                 key=lambda x: x[1], reverse=True)[:10]
            grouptop10 = "<b>Top 10 Mowers in this group:</b>\n\n"
            i = 0
            for (id, mower_count) in groupmowers:
                i += 1
                grouptop10 += "<b>%d.</b> %s %s - %d Mows\n" % (i, self.mowers[id]["first_name"], self.mowers[id]["last_name"], mower_count)
        globalmowers = sorted(self.mowers.items(), key=lambda x: x[1]["mows"], reverse=True)[:10]
        globaltop10 = "\n\n<b>Top 10 Mowers globally:</b>\n\n"
        i = 0
        for (id, mower) in globalmowers:
            i += 1
            globaltop10 += "<b>%d.</b> %s %s - %d Mows\n" % (i, mower["first_name"], mower["last_name"], mower["mows"])
        bot.sendMessage(update.message.chat.id,
                        text=grouptop10 + globaltop10,
                        parse_mode="HTML")
        self.db.dump()

    def list_groups(self, bot, update):
        group_names = []
        for g in self.mowgroups.keys():
            chat = bot.getChat(g)
            group_names.append("%s - @%s - %s %s - %s" % (chat.title, chat.username, chat.first_name, chat.last_name, g))
        bot.sendMessage(update.message.chat.id,
                        text="Groups I am currently counting mows in:\n %s" % "\n".join(group_names))

    def list_stickers(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="Here's the list of stickers that count for/against mow counts:")
        for (k, v) in self.stickers.items():
            bot.sendSticker(update.message.chat.id,
                            k)
            bot.sendMessage(update.message.chat.id,
                            text="^^^^ Sticker Value: %d" % v)

    def request_sticker_conversation(self, bot, update):
        sticker = None
        while True:
            bot.sendMessage(update.message.chat.id,
                            text="Send me the sticker you'd like to request to be added, or /cancel.")
            (bot, update) = yield
            if update.message.sticker is not None:
                sticker = update.message.sticker
                break
            bot.sendMessage(update.message.chat.id,
                            text="That's not a sticker!")
        if sticker.file_id in self.stickers.keys() or sticker.file_id in self.sticker_requests:
            bot.sendMessage(update.message.chat.id,
                            text="I'm already tracking or waiting to review that sticker!")
            return
        self.db.ladd("sticker_requests", sticker.file_id)
        self.db.dump()
        bot.sendMessage(update.message.chat.id,
                        text="Sticker requested! The admins will review the sticker and add it if it is mow-worthy. Thanks!")

    def request_sticker(self, bot, update):
        c = self.request_sticker_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def review_stickers_conversation(self, bot, update):
        while len(self.sticker_requests) > 0:
            s = self.sticker_requests[0]
            while True:
                bot.sendSticker(update.message.chat.id,
                                s)
                bot.sendMessage(update.message.chat.id,
                                text="Send 0 to reject sticker, or a pos/neg int to specify sticker value, or /cancel.")
                (bot, update) = yield
                try:
                    value = int(update.message.text)
                    if value != 0:
                        self.stickers[s] = value
                        bot.sendMessage(update.message.chat.id,
                                        text="Sticker added with value %d" % value)
                    self.sticker_requests.remove(s)
                    self.db.dump()
                    break
                except:
                    continue
        bot.sendMessage(update.message.chat.id,
                        text="Sticker review done!")

    def reset(self, bot, update):
        for u in self.mowers.keys():
            self.mowers = {}
        for g in self.mowgroups.keys():
            for u in self.mowgroups[g].keys():
                self.mowgroups[g] = {}
        self.db.dump()
        bot.sendMessage(update.message.chat.id,
                        text="Mow counts reset!")

    def review_stickers(self, bot, update):
        c = self.review_stickers_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def broadcast_message_conversation(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="What message would you like to broadcast to groups I'm in?")
        (bot, update) = yield
        message = update.message.text
        for g in self.mowgroups.keys():
            bot.sendMessage(g,
                            text=message)

    def broadcast_message(self, bot, update):
        c = self.broadcast_message_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)
