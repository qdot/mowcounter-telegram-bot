import sys
import os

# Make sure we're using the right python. Assume we're running out of the venv.
INTERP = os.path.join(os.getcwd(), 'bin', 'python')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)
    sys.path.append(os.getcwd())

import configparser
import importlib

config = configparser.ConfigParser()
config.read("config.ini")

bots = {}
for bot in config.sections():
    if "disabled" in config[bot] and config[bot]["webhook"] == "1":
        print("Bot {0} disabled".format(bot))
        continue
    if "webhook" not in config[bot] or config[bot]["webhook"] != "1":
        print("Bot {0} not using webhook".format(bot))
        continue
    if "repo_name" not in config[bot]:
        raise RuntimeError("Cannot find repo for bot {0}".format(bot))
    bot_path = os.path.join(os.getcwd(), config[bot]["repo_name"])
    if not os.path.isdir(bot_path):
        raise RuntimeError("Cannot find path {0} for bot {1}".format(bot_path,
                                                                     bot))
    sys.path.append(bot_path)
    # Assume the bot module is the same as the config file
    if "module_name" not in config[bot]:
        raise RuntimeError("Cannot find module for bot {0}".format(bot))
    module = config[bot]["module_name"]
    importlib.import_module(module)
    bots[config[bot]["token"]] = getattr(sys.modules[module],
                                         "create_webhook_bot")(config[bot])

if len(bots.keys()) == 0:
    raise RuntimeError("Not running any bots!")

from flask import Flask, request
import telegram

application = Flask(__name__)


@application.route('/')
def hello():
    return ""


@application.route('/telegram/<token>', methods=['POST'])
def webhook(token):
    update = telegram.update.Update.de_json(request.get_json(force=True))
    if token not in bots.keys():
        return 'OK'
    bots[token].update_queue.put(update)
    return 'OK'


if __name__ == "__main__":
    application.run()
