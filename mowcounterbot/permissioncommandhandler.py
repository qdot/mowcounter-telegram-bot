import logging
from telegram.ext import CommandHandler


class PermissionCommandHandler(CommandHandler):
    def __init__(self, command, perm_checks, callback, pass_args=False,
                 pass_update_queue=False):
        super().__init__(command,
                         callback,
                         pass_update_queue,
                         pass_args)
        self.logger = logging.getLogger(__name__)
        if type(perm_checks) is not list:
            raise RuntimeError("Permissions checks must be a list!")
        self.perm_checks = perm_checks

    def handle_update(self, update, dispatcher):
        for check in self.perm_checks:
            if not check(dispatcher.bot, update):
                return
        super().handle_update(update, dispatcher)
