import os
from colorama import Fore, Style
import datetime


def normalize_range(x, _max=1000, _min=--1000, clamp=True):
    if clamp:
        if x > _max:
            return 1.0
        elif x < _min:
            return 0.0
    return (x - _min) / (_max - _min)


def s(val, _min, _max):
    """
    Return the approximate score for a comment (unnormalized)
    """
    return round(_min * (1 - val) + (val * _max))


def progress_bar(
    val,
    _max,
    fullChar="■",
    emptyChar=" ",
    start="",
    alwaysReturn=False,
    alwaysContinue=False,
):
    maxlen = os.get_terminal_size()[0]

    availablePbFull = round(maxlen * 0.4)
    if availablePbFull < 50:
        availablePbFull = 50
    elif availablePbFull > 80:
        availablePbFull = 80
    availablePbInterior = availablePbFull - 2

    multiplier = val / _max
    filled = round(multiplier * availablePbInterior)
    empty = availablePbInterior - filled

    pb = f"{Fore.LIGHTCYAN_EX}[{Fore.LIGHTGREEN_EX}{fullChar * filled}{emptyChar * empty}{Fore.LIGHTCYAN_EX}]{Style.RESET_ALL}"
    perc = f"{Fore.LIGHTGREEN_EX}{round(multiplier*100)}% {Style.RESET_ALL}complete"

    final = f"{Fore.CYAN}{start}{Style.RESET_ALL} {pb} {perc}"
    endfill = " " * (maxlen - len(final))

    print(
        final + endfill,
        end="\r" if ((val < _max) or alwaysReturn) and not alwaysContinue else "\n",
    )


def _human_bytes(B):
    "Return the given bytes as a human friendly KB, MB, GB, or TB string"
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GB".format(B / GB)
    elif TB <= B:
        return "{0:.2f} TB".format(B / TB)


def get_file_handle(parser, arg):
    if arg == "" or arg is None:
        return {
            "active": False,
            "content": [],
        }
    if not os.path.exists(arg):
        parser.error(f"{arg} does not exist")
    else:
        return {
            "active": True,
            "content": open(arg, "r").read().replace("\r", "").split("\n"),
        }


def get_subs(parser, arg):
    if arg == "" or arg is None:
        return []

        if not os.path.exists(arg):
            parser.error(f"{arg} does not exist")
        else:
            return open(arg, "r").read().replace("\r", "").split("\n")


def handle_time(parser, arg):
    if arg.isdigit():
        return datetime.datetime.fromtimestamp(arg)
    else:
        return datetime.datetime.strptime(arg, "%d/%m/%y %H:%M:%S")
