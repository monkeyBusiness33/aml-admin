
"""
This module decorates/patches methods of logging.Logger class, plus patches already existing logger instances.
It's quite harmless, unless you use some weird non-tty stdout/stderr.
Primary effects:
  - Makes log colored
  - Forces usage of stdout instead of stderr for all StreamHandler and explicit streams of other handlers (because PyCharm tends to display all stderr in red, and stderr is default in Python logging)
  - Forces stdout and stderr to agree that they are tty (again PyCharm, its streams don't considered to be tty, but stuff like Celery checks .isatty() to decide whether to colorize the output)
"""

import sys
import logging
import itertools
import random


# Control sequences (just google VT52 to see the compatibility burden straight from 1975)
color_set = "\x1b[{}m"
color_reset = "\x1b[0m"


# useless stuff displayed before applying patches... yes, I felt very bored
intro_words = ["magic", "MaGiC", "voodoo", "sorcery", "wizardry", "witchery", "foobar", "rainbow"]
intro_adjectives = ["colourful", "evil", "fairy", "random"]
intro_colors = [34, 36, 32, 33, 35]


logger_methods_colors = {
    # method names and their desired highlight colors
    "debug": "1;90",
    "info": "1;32",
    "warning": "1;33",
    "error": "1;91",
    "critical": "1;95",
    "exception": "1;95",
}

# Adjusting handlers: Python logging.StreamHandler targets stderr by default.
# Django default logging configuration doesn't change it, too.
# New loggers (they will be initially created with the proper stream).
original_constructor = logging.StreamHandler.__init__  # must grab a reference outside of the lambda
logging.StreamHandler.__init__ = lambda zelf, stream=None: original_constructor(zelf, sys.stdout if stream in [sys.stderr, None] else stream)
# Existing loggers
patched_objects = set()
for logger in logging.Logger.manager.loggerDict.values():
    for handler in getattr(logger, "handlers", list()):
        if isinstance(handler, logging.StreamHandler):
            if handler.stream == sys.stderr:
                handler.stream = sys.stdout
                patched_objects.add(handler)


# the isatty() stuff below solves the problem with IDE streams not being recognized as TTY
# normally sys.stdout is sufficient, but some stubborn stuff like Celery explicitly checks sys.stderr even if it doesn't write there
for stream in [sys.stdout, sys.stderr]:
    try:
        isatty = stream.isatty()
    except Exception:
        isatty = False
    if not isatty:
        patched_objects.add(stream)
        stream.isatty = lambda: True  # stdout is now a TTY no matter what


def colorize_string(msg, color="1;32", extras=""):
    return str().join([color_set.format(color), extras, str(msg), color_reset])


def decorate_for_tty(method, color="1;39", extras=""):
    """
    decorate a method, replacing its first argument (must be str!) with the same, but colorized
    (it also knows how to decorate bound methods)
    """
    method_is_bound = bool(getattr(method, "__self__", None))  # existing loggers cause bound methods
    msg_arg_index = 0 if method_is_bound else 1  # message argument is located there

    def wrapper(*args, **kwargs):
        args = list(args)  # it's an immutable tuple when received
        args[msg_arg_index] = colorize_string(args[msg_arg_index], color, extras)
        return method(*args, **kwargs)

    return wrapper


# decorate classes
for entity in [logging.Logger]:
    for method_name, color_str in logger_methods_colors.items():
        if isinstance(entity, logging.PlaceHolder):
            continue  # ignore the PlaceHolder object, it's not functional and not a public API
        new_method = decorate_for_tty(getattr(entity, method_name), color_str)
        setattr(entity, method_name, new_method)
        patched_objects.add(entity)


# fancy useless stuff
intro_seq = zip(itertools.cycle(intro_colors), random.choice(intro_words))
intro_msg = "{adj} {word}{reset}".format(
    adj=random.choice(intro_adjectives).capitalize(),
    word=str().join((color_set + "{}").format(*symbol) for symbol in intro_seq),
    reset=color_reset,
)

# reporting
sys.stdout.write("{intro_msg}{c}: patched {n} object{s}{cr}\n".format(
    intro_msg=intro_msg,
    c=color_set.format("1;90"),
    n=len(patched_objects),
    s="" if len(patched_objects) == 1 else "s",
    cr=color_reset,
))

# debug with the following line:
# sys.stdout.write("Patched objects: {}\n".format(", ".join(str(e) for e in patched_objects) or "none"))

