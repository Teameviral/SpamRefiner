import inspect
import time
import logging
import re
from pathlib import Path

from telethon import events
from telethon.tl import functions
from telethon.tl import types


from SpamRefiner import CMD_LIST, LOAD_PLUG, tbot
import glob
import sys
from SpamRefiner import ubot
from pymongo import MongoClient
from SpamRefiner import MONGO_DB_URI
from SpamRefiner.accessary.sql.checkuser_sql import add_usersid_in_db, already_added, get_all_users


client = MongoClient()
client = MongoClient(MONGO_DB_URI)
db = client["SpamRefiner"]
blacklist = db.black
sudo = db.sudo

def register(**args):
    pattern = args.get("pattern")
    r_pattern = r"^[/]"

    if pattern is not None and not pattern.startswith("(?i)"):
        args["pattern"] = "(?i)" + pattern

    args["pattern"] = pattern.replace("^/", r_pattern, 1)
    stack = inspect.stack()
    previous_stack_frame = stack[1]
    file_test = Path(previous_stack_frame.filename)
    file_test = file_test.stem.replace(".py", "")
    reg = re.compile("(.*)")

    if pattern is not None:
        try:
            cmd = re.search(reg, pattern)
            try:
                cmd = cmd.group(1).replace("$", "").replace("\\", "").replace("^", "")
            except BaseException:
                pass

            try:
                CMD_LIST[file_test].append(cmd)
            except BaseException:
                CMD_LIST.update({file_test: [cmd]})
        except BaseException:
            pass

    def decorator(func):
        async def wrapper(check):
            if check.edit_date:
                return
            if check.fwd_from:
                return
            if check.is_group or check.is_private:
                pass
            else:
                print("i don't work in channels")
            if check.is_group:
               if check.chat.megagroup:
                  pass
               else:
                  return
                          
            users = blacklist.find({})
            for c in users:
                if check.sender_id == c["user"]:
                    return
            babe = sudo.find({})
            for k in babe:
                if check.sender_id == k["user"]:
                   pass
            if already_added(check.sender_id):
               pass
            elif not already_added(check.sender_id):
               add_usersid_in_db(check.sender_id)
            try:
                await func(check)
                try:
                    LOAD_PLUG[file_test].append(func)
                except Exception:
                    LOAD_PLUG.update({file_test: [func]})
            except BaseException:
                return
            else:
                pass

        tbot.add_event_handler(wrapper, events.NewMessage(**args))
        return wrapper

    return decorator


def spamrefinerrobot(**args):
    pattern = args.get("pattern", None)
    disable_edited = args.get("disable_edited", False)
    ignore_unsafe = args.get("ignore_unsafe", False)
    unsafe_pattern = r"^[^/!#@\$A-Za-z]"
    group_only = args.get("group_only", False)
    disable_errors = args.get("disable_errors", False)
    insecure = args.get("insecure", False)
    if pattern is not None and not pattern.startswith("(?i)"):
        args["pattern"] = "(?i)" + pattern

    if "disable_edited" in args:
        del args["disable_edited"]

    if "ignore_unsafe" in args:
        del args["ignore_unsafe"]

    if "group_only" in args:
        del args["group_only"]

    if "disable_errors" in args:
        del args["disable_errors"]

    if "insecure" in args:
        del args["insecure"]

    if pattern:
        if not ignore_unsafe:
            args["pattern"] = args["pattern"].replace("^.", unsafe_pattern, 1)

    def decorator(func):
        async def wrapper(check):
            if check.edit_date and check.is_channel and not check.is_group:
                return
            if group_only and not check.is_group:
                return
            if check.via_bot_id and not insecure and check.out:
                # Ignore outgoing messages via inline bots for security reasons
                return

            try:
                await func(check)
            except events.StopPropagation:
                raise events.StopPropagation
            except KeyboardInterrupt:
                pass
            except BaseException as e:
                print(e)
            else:
                pass

        if not disable_edited:
            ubot.add_event_handler(wrapper, events.MessageEdited(**args))
        ubot.add_event_handler(wrapper, events.NewMessage(**args))
        return wrapper

    return decorator



def load_module(shortname):
    if shortname.startswith("__"):
        pass
    elif shortname.endswith("_"):
        import importlib
        import SpamRefiner.events

        path = Path(f"SpamRefiner/accessary/{shortname}.py")
        name = "SpamRefiner.accessary.{}".format(shortname)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print("Successfully imported " + shortname)
    else:
        import importlib
        import SpamRefiner.events

        path = Path(f"SpamRefiner/accessary/{shortname}.py")
        name = "SpamRefiner.accessary.{}".format(shortname)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.register = register
        mod.spamrefinerrobot = spamrefinerrobot
        mod.tbot = tbot
        mod.logger = logging.getLogger(shortname)
        spec.loader.exec_module(mod)
        sys.modules["SpamRefiner.accessary." + shortname] = mod
        print("Successfully imported " + shortname)


path = "SpamRefiner/accessary/*.py"
files = glob.glob(path)
for name in files:
    with open(name) as f:
        path1 = Path(f.name)
        shortname = path1.stem
        load_module(shortname.replace(".py", ""))
