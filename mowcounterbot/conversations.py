from .base import MetafetishModuleBase


class ConversationManager(MetafetishModuleBase):
    def __init__(self):
        # Conversations only survive as long as the process, so no need to
        # pickledb here.
        super().__init__(__name__)
        # Conversation dictionary. Key will be user id for the conversation.
        # Value will get a generator object.
        self.conversations = {}

    def add(self, update, conversation):
        self.conversations[update.message.chat.id] = conversation

    def check(self, bot, update):
        chat_id = update.message.chat.id
        if chat_id not in self.conversations.keys():
            return False
        try:
            # send only takes a single argument, so case up the current bot and
            # update in a tuple
            self.conversations[chat_id].send((bot, update))
        except StopIteration:
            self.cancel(bot, update)
        return True

    def cancel(self, bot, update):
        chat_id = update.message.chat.id
        if chat_id not in self.conversations.keys():
            return False
        del self.conversations[chat_id]
        return True

    def shutdown(self):
        for (chat_id, c) in self.conversations:
            # Send a message here saying we're shutting down?
            pass
