from colorama import Fore, Style
import logging


class CustomCleanFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    format = (
        "[%(asctime)s] [%(filename)-17s:%(lineno)-3s] (%(funcName)-20s)"
        + " %(levelname)-9s"
        + "%(message)s"
    )

    FORMATS = {
        logging.DEBUG: format,
        logging.INFO: format,
        logging.WARNING: format,
        logging.ERROR: format,
        logging.CRITICAL: format,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    format = (
        Fore.LIGHTBLACK_EX
        + f"[%(asctime)s] [{Fore.CYAN}%(filename)-17s{Fore.LIGHTBLACK_EX}:%(lineno)-3s] ({Fore.CYAN}%(funcName)-20s{Fore.LIGHTBLACK_EX})"
        + " {}%(levelname)-9s"
        + Style.RESET_ALL
        + "{}%(message)s"
    )

    FORMATS = {
        logging.DEBUG: format.format(Fore.CYAN, ""),
        logging.INFO: format.format(Fore.LIGHTCYAN_EX, ""),
        logging.WARNING: format.format(Fore.LIGHTYELLOW_EX, ""),
        logging.ERROR: format.format(Fore.LIGHTRED_EX, Fore.RED),
        logging.CRITICAL: format.format(Fore.LIGHTRED_EX, Fore.LIGHTRED_EX),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
