from telegram.ext import CommandHandler
from .base import MetafetishPickleDBBase
import cgi


class UserNotFoundException(Exception):
    pass


class UserFlagGroupNotFoundException(Exception):
    pass


class UserManager(MetafetishPickleDBBase):
    def __init__(self, dbdir, cm):
        super().__init__(__name__, dbdir, "users", True)
        self.has_admin = True
        if self.get_num_users() == 0:
            self.has_admin = False
        self.cm = cm

    def register_with_dispatcher(self, dispatcher):
        dispatcher.add_handler(CommandHandler('register', self.register))
        dispatcher.add_handler(CommandHandler('profile_hide',
                                              self.set_hide_profile))
        dispatcher.add_handler(CommandHandler('profile_show',
                                              self.set_show_profile))

    def get_num_users(self):
        return len(self.db.getall())

    def is_valid_user(self, user_id):
        if str(user_id) in self.db.getall():
            return True
        return False

    def register(self, bot, update):
        user_id = str(update.message.from_user.id)
        if self.is_valid_user(user_id):
            return
        # Use the user_id as the dictionary key. Unfortunately the id is an
        # int so this requires casting to make sure comparisons work.
        user_db = {"flags": ["admin" if not self.has_admin else ""],
                   "fields": {},
                   "show_profile": False,
                   "username": update.message.from_user.username,
                   "displayname": "%s %s" % (update.message.from_user.first_name,
                                             update.message.from_user.last_name)}
        if not self.has_admin:
            bot.sendMessage(update.message.chat.id,
                            text="You're the first user, therefore you're the <b>admin</b>.",
                            parse_mode="HTML")
        self.has_admin = True
        self.db.set(str(user_id), user_db)

    def help(self, bot, update):
        bot.sendMessage(update.message.chat.id,
                        text="""
<b>User Module</b>

The user module allows users to create profiles for themselves.

Each user can also have profiles, which consists of a field name (with no whitespace) and description of that field. This allows users to share whatever information they might want about themselves. Profiles sharing is offby default, and can be turned on and off as needed.

Note that field names are case insensitive for search, but will display as entered.

<b>Commands</b>

%s
""" % (self.commands()),
                        parse_mode="HTML")

    def commands(self):
        return """/userhelp - Display users help message.
/useraddfield - Add or update a profile field.
/userrmfield - Remove a profile field.
/usershowprofile - Turn profile sharing on.
/userhideprofile - Turn profile sharing off.
/userprofile - Show the profile of another user."""

    def show_profile(self, bot, update, show_profile):
        user_id = str(update.message.from_user.id)
        self.db.dadd(user_id, ("show_profile", show_profile))
        bot.sendMessage(update.message.chat.id,
                        text="Profile display is now turned <b>%s</b>." % ("ON" if show_profile else "OFF"),
                        parse_mode="HTML")

    def get_user_by_name_or_id(self, user_name_or_id):
        user_id = None
        user = None
        if user_name_or_id in self.db.getall():
            user_id = user_name_or_id
            user = self.db.get(user_name_or_id)
        else:
            for id in self.db.getall():
                data = self.db.get(id)
                if data["username"] == user_name_or_id:
                    user_id = id
                    user = data
        return (user_id, user)

    def edit_flag_conversation(self, bot, update, remove):
        bot.sendMessage(update.message.chat.id,
                        text="What is the name or id of the user who you'd like to edit flags for?")
        while True:
            (bot, update) = yield
            user_name_or_id = update.message.text
            (user_id, user) = self.get_user_by_name_or_id(user_name_or_id)
            if user_id:
                break
            bot.sendMessage(update.message.chat.id,
                            text="I can't find that user in my database, please try again or /cancel.")

        bot.sendMessage(update.message.chat.id,
                        text="What is the name of the flag you would like to edit for %s?" % (user["username"]))
        # TODO: show permissions flag keyboard here
        (bot, update) = yield
        user_flag = update.message.text
        if remove:
            if user_flag not in user["flags"]:
                user["flags"].append(user_flag)
                self.db.set(user_id, user)
                bot.sendMessage(update.message.chat.id,
                                text="Added flag %s to %s" % (user_flag, user_name_or_id))
            else:
                bot.sendMessage(update.message.chat.id,
                                text="User %s already has flag %s" % (user_name_or_id, user_flag))
        else:
            if user_flag in user["flags"]:
                user["flags"].remove(user_flag)
                self.db.set(user_id, user)
                bot.sendMessage(update.message.chat.id,
                                text="Removed flag %s from %s" % (user_flag, user_name_or_id))
            else:
                bot.sendMessage(update.message.chat.id,
                                text="User %s does not have flag %s" % (user_name_or_id, user_flag))

    def add_flag(self, bot, update):
        c = self.edit_flag_conversation(bot, update, True)
        c.send(None)
        self.cm.add(update, c)

    def remove_flag(self, bot, update):
        c = self.edit_flag_conversation(bot, update, False)
        c.send(None)
        self.cm.add(update, c)

    def has_flag(self, user_id, flag):
        if type(user_id) is not str:
            user_id = str(user_id)
        try:
            user = self.db.get(user_id)
        except KeyError:
            return False
        if flag in user["flags"]:
            return True
        return False

    def get_fields(self, bot, update):
        try:
            (prof_command, prof_name) = update.message.text.split()
        except:
            prof_name = update.message.from_user.username
        self.logger.warn("NAME %s" % prof_name)
        (user_id, user) = self.get_user_by_name_or_id(prof_name)
        if not user_id or not user["show_profile"]:
            bot.sendMessage(update.message.chat.id,
                            text="User not found, or does not have a public profile")
            return
        fields = "<b>User Profile for %s</b>\n\n" % (prof_name)
        for (k, v) in user["fields"].items():
            fields += "<b>%s</b>\n\n%s\n\n" % (k, v)
        bot.sendMessage(update.message.chat.id,
                        text=fields,
                        parse_mode="HTML",
                        disable_web_page_preview=True)

    def add_field_conversation(self, bot, update):
        user_id = str(update.message.from_user.id)
        bot.sendMessage(update.message.chat.id,
                        text="What is the name of the profile field you'd like to add?")
        (bot, update) = yield
        field_name = cgi.escape(update.message.text.strip())
        bot.sendMessage(update.message.chat.id,
                        text="What would you like to set field %s to?" % (field_name))
        # TODO: show permissions flag keyboard here
        (bot, update) = yield
        field_value = cgi.escape(update.message.text.strip())
        user = self.db.get(user_id)
        user["fields"][cgi.escape(field_name)] = cgi.escape(field_value)
        self.db.set(user_id, user)
        bot.sendMessage(update.message.chat.id,
                        text="Field %s is now set/updated in your profile." % (field_name))

    def remove_field_conversation(self, bot, update):
        user_id = str(update.message.from_user.id)
        bots.sendMessage(update.message.chat.id,
                        text="What is the name of the profile field you'd like to remove?")
        (bot, update) = yield
        field_name = cgi.escape(update.message.text.strip())
        user = self.db.get(user_id)
        try:
            del user["fields"][cgi.escape(field_name)]
        except KeyError:
            bot.sendMessage(update.message.chat.id,
                            text="Can't find field %s in your profile." % (field_name))
            return
        bot.sendMessage(update.message.chat.id,
                        text="Field %s has been removed from your profile." % (field_name))

    def add_field(self, bot, update):
        c = self.add_field_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def remove_field(self, bot, update):
        c = self.remove_field_conversation(bot, update)
        c.send(None)
        self.cm.add(update, c)

    def show_list(self, bot, update):
        users = "User list:\n\n"
        for k in self.db.getall():
            user_info = self.db.get(k)
            users += "- %s : %s : %s\n" % (user_info["username"],
                                           user_info["displayname"],
                                           k)
        bot.sendMessage(update.message.chat.id,
                        text=users)
