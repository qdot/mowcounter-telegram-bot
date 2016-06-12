from nptelegrambot.base import NPModuleBase
from nptelegrambot.chats import ChatRedisTransactions
from nptelegrambot.users import UserRedisTransactions
import cgi


# Mowcounter needs to hit chat and user keys too, so just reuse the transaction
# classes to make sure everything keeps the correct naming
class MowRedisTransactions(ChatRedisTransactions, UserRedisTransactions):
    def __init__(self, redis):
        super().__init__(redis)
        self.redis = redis

    def add_sticker_request(self, user_id, file_id):
        self.redis.hmset("mowcounter:sticker-requests", {file_id: user_id})

    def remove_sticker_request(self, file_id):
        self.redis.hdel("mowcounter:sticker-requests", file_id)

    def get_sticker_requests(self):
        return self.redis.hgetall("mowcounter:sticker-requests")

    def get_stickers(self):
        return self.redis.hgetall("mowcounter:sticker-values")

    def get_sticker_value(self, sticker_id):
        v = self.redis.hget("mowcounter:sticker-values", sticker_id)
        if v is not None:
            return int(v)
        return None

    def add_sticker(self, user_id, file_id, value):
        self.redis.hset("mowcounter:sticker-values", file_id, value)
        self.redis.hset("mowcounter:sticker-users", file_id, user_id)

    def remove_sticker(self, file_id):
        self.redis.hdel("mowcounter:sticker-values", file_id)
        self.redis.hdel("mowcounter:sticker-users", file_id)

    def get_sticker_values(self):
        return self.redis.hgetall("mowcounter:sticker-values")

    def update_mow_count(self, user_id, user_username, user_fname,
                         user_lname, chat_id, chat_title, chat_username,
                         mow_count):
        user_id = str(user_id)
        chat_id = str(chat_id)
        # pipe = self.redis.pipeline()
        self.add_user(user_id, user_username, user_fname, user_lname)
        self.add_chat(chat_id, chat_title, chat_username)
        self.update_chat_status(chat_id, "member")
        self.redis.zincrby("mowcounter:user-scores", user_id, mow_count)
        self.redis.zincrby("mowcounter:" + chat_id + "-scores",
                           user_id,
                           mow_count)

    def reset_counts(self):
        self.redis.delete("user-scores")
        chats = self.get_chats_ids()
        for c in chats:
            self.redis.delete("mowcounter:" + c + "-scores")

    def get_own_count(self, user_id, chat_id):
        user_id = str(user_id)
        chat_id = str(chat_id)
        r = {"local_score": 0,
             "local_rank": 0,
             "local_total": 0,
             "global_score": 0,
             "global_rank": 0,
             "global_total": 0}

        # global score
        r["global_score"] = self.redis.zscore("mowcounter:user-scores",
                                              user_id)
        if r["global_score"] is None:
            return None
        # global rank
        r["global_rank"] = self.redis.zrevrank("mowcounter:user-scores",
                                               user_id)
        # global total
        r["global_total"] = self.redis.zcard("mowcounter:user-scores")

        chat_key = "mowcounter:" + chat_id + "-scores"
        # local score
        r["local_score"] = self.redis.zscore(chat_key, user_id)
        # local rank
        r["local_rank"] = self.redis.zrevrank(chat_key, user_id)
        # local total
        r["local_total"] = self.redis.zcard(chat_key)
        if not r["local_score"]:
            r["local_score"] = 0
            if not r["local_total"]:
                r["local_total"] = 0
            r["local_rank"] = r["local_total"]
        return r

    def get_chat_top10(self, chat_id):
        chat_id = str(chat_id)
        top10 = self.redis.zrevrange("mowcounter:" + chat_id + "-scores",
                                     0, 9,
                                     withscores=True, score_cast_func=int)
        top10list = []
        for (user_id, score) in top10:
            user_dict = {}
            u = self.redis.hgetall(user_id)
            user_dict["name"] = u["firstname"] + ((" " + u["lastname"]) if len(u["lastname"]) > 0 else "")
            user_dict["score"] = score
            top10list.append(user_dict)
        return top10list

    def get_global_top10(self, chat_id):
        chat_id = str(chat_id)
        top10 = self.redis.zrevrange("mowcounter:user-scores", 0, 9,
                                     withscores=True, score_cast_func=int)
        top10list = []
        for (user_id, score) in top10:
            user_dict = {}
            u = self.redis.hgetall(user_id)
            user_dict["name"] = u["firstname"] + ((" " + u["lastname"]) if len(u["lastname"]) > 0 else "")
            user_dict["score"] = score
            top10list.append(user_dict)
        return top10list

    def get_own_chat_count(self, user_id):
        # Get all chat keys
        chats = self.get_chat_ids()
        scores = {}
        for chat_id in chats:
            score_hash = "mowcounter:" + chat_id + "-scores"
            score = self.redis.zscore(score_hash, user_id)
            if score is None:
                continue
            chat_info = self.get_chat(chat_id)
            scores[chat_info["title"]] = {}
            scores[chat_info["title"]]["score"] = score
            scores[chat_info["title"]]["rank"] = self.redis.zrevrank(score_hash,
                                                                      user_id)
            scores[chat_info["title"]]["size"] = self.redis.zcard(score_hash)
        return scores

    def get_total_mows(self):
        all_scores = self.redis.zrange("mowcounter:user-scores", 0, -1,
                                       withscores=True,
                                       score_cast_func=int)
        return sum([v[1] for v in all_scores])


class MowCounter(NPModuleBase):
    def __init__(self, store):
        super().__init__(__name__)
        self.store = MowRedisTransactions(store)

    def rm_sticker(self, bot, update):
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
        if sticker.file_id not in self.store.get_stickers().keys():
            bot.sendMessage(update.message.chat.id,
                            text="I don't know that sticker!")
            return
        self.store.remove_sticker(sticker.file_id)
        bot.sendMessage(update.message.chat.id,
                        text="Sticker removed!")

    def check_mows(self, bot, update):
        user = update.message.from_user
        chat = update.message.chat
        mows = 0
        # The API tests for text as either text or '', not None. God damnit.
        if len(update.message.text) is not 0:
            # count mows. Maximum one mow per message
            if update.message.text.lower().count("mow"):
                mows = 1
            elif update.message.text.lower().count("wom"):
                mows = -1
        elif update.message.sticker is not None:
            sticker = update.message.sticker
            # Make sure we have the sticker and it's accepted
            value = self.store.get_sticker_value(sticker.file_id)
            if value is None:
                return
            mows = value
        if mows is 0:
            return
        self.store.update_mow_count(user.id, user.username, user.first_name,
                                    user.last_name, chat.id, chat.title,
                                    chat.username, mows)

    def show_own_count(self, bot, update):
        user_id = str(update.message.from_user.id)
        chat_id = str(update.message.chat.id)
        user = update.message.from_user
        r = self.store.get_own_count(user_id, chat_id)
        if r is None:
            bot.sendMessage(update.message.chat.id,
                            text="%s %s has no mows!" % (user.first_name, user.last_name))
            return
        total_mows = self.store.get_total_mows()
        status_msg = ("%s has mowed %d times in this chat (Rank: %d of %d), and %d times globally (Rank: %d of %d, %f%% of Global Mows)." %
                      ((user.first_name + ((" " + user.last_name) if len(user.last_name) > 0 else "")),
                       r["local_score"], r["local_rank"] + 1, r["local_total"],
                       r["global_score"], r["global_rank"] + 1, r["global_total"],
                       (r["global_score"] / total_mows) * 100))
        if (update.message.chat.id > 0):
            status_msg += "\n\n"
            scores = self.store.get_own_chat_count(user_id)
            for (chat_name, chat_info) in scores.items():
                status_msg += "%s\n" % (chat_name)
                status_msg += "Score: %d - Rank: %d of %d\n\n" % (chat_info["score"], chat_info["rank"], chat_info["size"])
        bot.sendMessage(update.message.chat.id,
                        text=status_msg)
        return

    def show_top10_count(self, bot, update):
        chat_id = str(update.message.chat.id)
        chat_top10 = self.store.get_chat_top10(chat_id)
        global_top10 = self.store.get_global_top10(chat_id)
        msg = "<b>Top 10 Count for Chat '%s':</b>\n\n" % update.message.chat.title
        i = 1
        for u in chat_top10:
            msg += ("<b>%d.</b> " % (i)) + cgi.escape("%s - %s\n" % (u["name"], u["score"]))
            i += 1
        msg += "\n<b>Top 10 Count Globally:</b>\n\n"
        i = 1
        for u in global_top10:
            msg += ("<b>%d.</b> " % (i)) + cgi.escape("%s - %s\n" % (u["name"], u["score"]))
            i += 1

        msg += "\n\n<b>Total Mows:</b> %d" % self.store.get_total_mows()
        bot.sendMessage(update.message.chat.id,
                        text=msg,
                        parse_mode="HTML")

    def list_stickers(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="Here's the list of stickers that count for/against mow counts:")
        for (k, v) in self.store.get_stickers().items():
            bot.sendSticker(update.message.chat.id,
                            k)
            bot.sendMessage(update.message.chat.id,
                            text="^^^^ Sticker Value: %d" % int(v))

    def request_sticker(self, bot, update):
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
        if sticker.file_id in self.store.get_stickers().keys() or sticker.file_id in self.store.get_sticker_requests().keys():
            bot.sendMessage(update.message.chat.id,
                            text="I'm already tracking or waiting to review that sticker!")
            return
        self.store.add_sticker_request(update.message.from_user.id,
                                       sticker.file_id)
        bot.sendMessage(update.message.chat.id,
                        text="Sticker requested! The admins will review the sticker and add it if it is mow-worthy. Thanks!")

    def review_stickers(self, bot, update):
        for (sticker_id, user_id) in self.store.get_sticker_requests().items():
            while True:
                bot.sendSticker(update.message.chat.id,
                                sticker_id)
                bot.sendMessage(update.message.chat.id,
                                text="Send 0 to reject sticker, or a pos/neg int to specify sticker value, or /cancel.")
                (bot, update) = yield
                try:
                    value = int(update.message.text)
                    if value != 0:
                        self.store.add_sticker(user_id, sticker_id, value)
                        bot.sendMessage(update.message.chat.id,
                                        text="Sticker added with value %d" % value)
                    self.store.remove_sticker_request(sticker_id)
                    break
                except:
                    continue
        bot.sendMessage(update.message.chat.id,
                        text="Sticker review done!")

    def reset(self, bot, update):
        self.store.reset_counts()
        bot.sendMessage(update.message.chat.id,
                        text="Mow counts reset!")
