from .base import MetafetishPickleDBBase


class GroupManager(MetafetishPickleDBBase):
    def __init__(self, dbdir):
        super().__init__(__name__, dbdir, "groups", True)

    def add_group(self, bot, update):
        group_name = update.message.text.partition(" ")[2].strip().lower()
        if group_name[0] is not "@":
            bot.sendMessage(update.message.chat_id,
                            text="Please specify group name with a leading @! (You used %s)" % (group_name))
            return
        try:
            me = bot.getMe()
            chat_status = bot.getChatMember(group_name, me.id)
            if chat_status.status != "administrator":
                bot.sendMessage(update.message.chat_id,
                                text="Please make sure I'm an admin in %s!" % (group_name))
                return
        except:
            bot.sendMessage(update.message.chat_id,
                            text="Please make sure %s exists and that I'm an admin there!" % (group_name))
            return
        self.db.set(group_name, {})
        bot.sendMessage(update.message.chat_id,
                        text='Group %s added!' % (group_name))

    def rm_group(self, bot, update):
        group_name = update.message.text.partition(" ")[2].strip().lower()
        if group_name[0] is not "@":
            bot.sendMessage(update.message.chat_id,
                            text="Please specify group name with a leading @! (You used %s)" % (group_name))
            return
        try:
            me = bot.getMe()
            chat_status = bot.getChatMember(group_name, me.id)
            if chat_status.status != "left":
                bot.sendMessage(update.message.chat_id,
                                text="Please make sure I'm no longer in %s!" % (group_name))
                return
        except:
            pass
        self.db.rem(group_name)
        bot.sendMessage(update.message.chat_id,
                        text='Group %s removed!' % (group_name))

    def user_in_groups(self, bot, user_id):
        if type(user_id) is not str:
            user_id = str(user_id)
        try:
            for group in self.db.dkeys("groups"):
                users = self.db.get(group)
                if user_id not in users.keys():
                    continue
                user_status = users[user_id]
                if user_status in ["creator", "administrator", "member"]:
                    return True
        except:
            pass
        # Any time we don't find the member in either channel, update all
        # tracked channels
        is_in_group = False
        for group in self.db.getall():
            member = bot.getChatMember(group, user_id)
            if member is None:
                continue
            user_db = self.db.get(group)
            user_db[user_id] = member.status
            self.db.set(group, user_db)
            if member.status in ["creator", "administrator", "member"]:
                is_in_group = True
        return is_in_group

    def get_groups(self):
        return self.db.getall()
    # def update_group_list(self, bot, user_id):
    #     users = self.db.dkeys("users")
    #     for u in users:
    #         user_status = self.db.dget("users", u)
    #         member = bot.getChatMember(self.group_name, u)
    #         if user_status is not member.status:
    #             self.db.dadd("users", u, member.status)
