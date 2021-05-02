import argparse
import os
import sys
from colorama import init, Fore, Style
from pathlib import Path
import logging
import traceback
import time

from functions.general import _human_bytes, get_file_handle, handle_time, get_subs
from functions.formatters import CustomFormatter, CustomCleanFormatter


def build_normalize(normalize):
    if normalize is None:
        return {
            "normalize": False,
        }
    else:
        return {
            "normalize": True,
            "min": normalize[0],
            "max": normalize[1],
        }


def setup_directory(dir):
    Path(os.path.join(dir, "build")).mkdir(exist_ok=True, parents=True)
    logger.debug("Setup directory")


def confirm_args():
    global args
    logger.info(f"Setting directory to {Fore.CYAN}{os.path.abspath(args['dir'])}")
    files = [i for i in os.listdir(args["dir"]) if i != "build"]
    if len(files) > 0:
        if args["noInput"]:
            logger.warning(
                f"(No input) {Style.RESET_ALL}{args['dir']} has existing files."
            )
        else:
            if (
                input(
                    f"{Fore.LIGHTYELLOW_EX}WARNING: {Style.RESET_ALL}{args['dir']} has existing files. Are you sure you want to continue?\n(y/n): "
                ).lower()
                == "n"
            ):
                sys.exit(1)

    if args["startingSort"] not in ["hot", "new", "top", "controversial"]:
        logger.error(f"startingSort has an invalid value ({args['startingSort']})")
        sys.exit(1)

    if args["userCommentLimit"] > 1000:
        logger.warning(
            f"userCommentLimit exceeds cap by {args['userCommentLimit']-1000}. Only 1000 comments will be scraped."
        )
    elif args["userCommentLimit"] < 1:
        logger.error(f"userCommentLimit is less than 1 ({args['userCommentLimit']})")

    if args["normalize"] is not None:
        if args["normalize"][0] > args["normalize"][1]:
            logger.error(
                f"Normalize minimum value ({args['normalize'][0]}) is greater than normalize maximum value ({args['normalize'][1]})"
            )
            sys.exit(1)


def handle_errors(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.error(
            f"Error calling {func.__name__} with args {', '.join(list(args))}, kwargs {dict(kwargs)}: {traceback.format_exc()}"
        )
        sys.exit(1)


def creation_process():
    logger.info("Creating layer 1..")
    layerHandler.setup_build_layer(1)

    # Get initial posts and the author of those posts
    startSubmissions, initialUserCollection = handle_errors(
        users_from_posts,
        args["startingSubreddit"],
        sorting=args["startingSort"],
        limit=args["startingPostLimit"],
    )

    logger.info(f"Received {len(startSubmissions)} submissions")
    logger.info(f"Received {len(initialUserCollection)} users")

    # Get comments from each post
    commentUsers, comments = handle_errors(
        get_post_comments,
        startSubmissions,
        limit=args["postCommentLimit"],
    )
    logger.info(f"Got {len(commentUsers)} users")
    logger.info(f"Got {len(comments)} initial comments")

    initialUserCollection += commentUsers
    del commentUsers
    del startSubmissions

    tmp = len(initialUserCollection)
    if tmp == 0:
        logger.critical("No initial users were collected (excessive blocking?)")
        sys.exit(1)

    # Dump scraped comments to database
    layerHandler.dump_data(comments)

    # Dump to layer 1
    layerHandler.dump_build_layer(1, initialUserCollection)
    logger.info(f"{Fore.LIGHTGREEN_EX}Finished building layer 1")


def process_layer(layer):
    logger.info(
        f"{Fore.LIGHTMAGENTA_EX}Processing layer {layer}... ({get_dump_size()})"
    )
    start = time.time()

    # Prepare next layer
    layerHandler.setup_build_layer(layer + 1)

    # Fetch all usernames to scrape
    usernames = layerHandler.read_build_layer(layer)[: args["userLimit"]]
    lenUsers = len(usernames) - 1

    # Iterate through all users
    for i, user in enumerate(usernames):
        if args["verbose"]:
            logger.debug(f"Getting {user} comments..")

        # Scrape all comments, get submission data from x
        # amount of comments
        newUsers, comments = get_user_comments(
            user,
            normalize,
            limit=args["userCommentLimit"],
            limitUsers=args["userLimit"],
            submissionLimit=args["submissionLimit"],
            userID=i,
            lenUsers=lenUsers,
        )

        if args["verbose"]:
            logger.debug(f"Received {len(newUsers)} users for next layer")
            logger.debug(f"Received {len(comments)} comments")
            logger.info(f"Completed {user}")

        # Add users to the next layer and add to final database
        layerHandler.dump_build_layer(layer + 1, newUsers)
        layerHandler.dump_data(comments)

    end = time.time()
    logger.info(
        f"{Fore.LIGHTGREEN_EX}Finished processing layer {layer} (Elapsed {round(end-start, 2)}s)"
    )


def get_dump_size():
    return _human_bytes(os.path.getsize(os.path.join(args["dir"], "dump.db")))


if __name__ == "__main__":
    init(convert=True, autoreset=True)

    # --------------
    # ARG PARSING
    # --------------

    parser = argparse.ArgumentParser(
        description="Scrape comments with details",
    )

    parser.add_argument(
        "--startingPostLimit", "--il", type=int, help="Posts to start scraping from"
    )

    parser.add_argument(
        "--startingSubreddit",
        "--ssub",
        type=str,
        default="all",
        help="Starting subreddit to scrape from",
    )

    parser.add_argument(
        "--startingSort",
        "--ssort",
        type=str,
        default="hot",
        help="hot/new/top/controversial",
    )

    parser.add_argument(
        "--postCommentLimit",
        "--pcl",
        type=int,
        default=5000,
        help="Maximum comments to scrape from the starting posts",
    )

    parser.add_argument(
        "--userCommentLimit",
        "--ucl",
        type=int,
        default=1000,
        help="Maximum comments to scrape from a single user (capped at 1000)",
    )

    parser.add_argument(
        "--userLimit",
        "--ul",
        type=int,
        help="Maximum users to scrape from at a time",
    )

    parser.add_argument(
        "--submissionLimit",
        "--sl",
        type=int,
        default=15,
        help="Maximum submissions to scrape from a user's comment (Heavily affects speed)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print more verbose info (debugging)",
    )

    parser.add_argument(
        "--fileLogging",
        "--fl",
        action="store_true",
        help="Log to file as well as stdout",
    )

    parser.add_argument(
        "--layers",
        "-l",
        type=int,
        default=3,
        help="Number of layers (excluding creation)",
    )

    parser.add_argument(
        "--dir",
        "-d",
        default="dump",
        help="Directory to dump data in",
    )

    parser.add_argument(
        "--normalize",
        "-n",
        nargs=2,
        type=int,
        help="Normalize the score automatically between a certain range",
    )

    parser.add_argument(
        "--noInput",
        action="store_true",
        help="Disable all inputs",
    )

    parser.add_argument(
        "--formatJSON",
        action="store_true",
        help="Store data in dump.json as well",
    )

    parser.add_argument(
        "--blockUsers",
        default="",
        type=lambda x: get_file_handle(parser, x),
        help="Filename of blocked users (separate by new lines)",
    )

    parser.add_argument(
        "--blockSubreddits",
        default="",
        type=lambda x: get_file_handle(parser, x),
        help="Filename of blocked subreddits (separate by new lines, no 'r/' preceding)",
    )

    parser.add_argument(
        "--blockNSFW",
        action="store_true",
        help="Block all nsfw",
    )

    parser.add_argument(
        "--minScore",
        type=int,
        default=-10000000,
        help="Minimum comment score",
    )

    parser.add_argument(
        "--maxScore",
        type=int,
        default=10000000,
        help="Maximum comment score",
    )

    parser.add_argument(
        "--minTime",
        type=lambda x: handle_time(parser, x),
        help="All comments/submissions must be made from this value (d/m/y H:M:S) (01/01/2021 12:00:00 for example)",
    )

    parser.add_argument(
        "--restrictSubs",
        default="",
        type=lambda x: get_subs(parser, x),
        help="Restrict comments to only belong in these subreddits (filename, separate by new lines)",
    )

    parser.add_argument(
        "--notify",
        action="store_true",
        help="Notify sound when completed",
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Use a GUI rather than a CLI",
    )

    args = vars(parser.parse_args())
    print(args)
    if args["gui"]:
        import main_gui

        sys.exit()

    # Parse normalize for ease of use
    normalize = build_normalize(args["normalize"])

    # --------------
    # OTHER STUFF
    # --------------

    # Setup logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.INFO)
    consoleHandler.setFormatter(CustomFormatter(args["fileLogging"]))

    logger.addHandler(consoleHandler)

    # Setup directory and make sure arguments are valid
    setup_directory(args["dir"])
    confirm_args()

    if args["fileLogging"]:
        fileHandler = logging.FileHandler(os.path.join(args["dir"], "build/log.log"))
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(CustomCleanFormatter(args["fileLogging"]))

        logger.addHandler(fileHandler)

    if args["verbose"]:
        logger.setLevel(logging.DEBUG)
        consoleHandler.setLevel(logging.DEBUG)

    # Import necesssary functions
    # This is delayed to allow parsing arguments to be faster
    from functions.processing import (
        users_from_posts,
        get_post_comments,
        get_user_comments,
        set_lp_logger,
        set_blocked,
    )
    from functions.layerHandling import LayerHandling

    if args["notify"]:
        import winsound

    layerHandler = LayerHandling(logger, args["dir"])

    # Setup build database
    layerHandler.clear_build_db()
    layerHandler.establish_build_db()

    # Setup dump database
    layerHandler.clear_dump_db()
    layerHandler.establish_dump_db()
    layerHandler.setup_dump_table(normalize)

    set_lp_logger(logger, args["verbose"])
    set_blocked(
        args["blockUsers"],
        args["blockNSFW"],
        args["blockSubreddits"],
        args["minScore"],
        args["maxScore"],
        args["restrictSubs"],
    )

    # Create first layer
    try:
        creation_process()
    except Exception:
        logger.critical(
            f"An unexpected exception occurred during creation - {traceback.format_exc()}"
        )
        sys.exit(1)

    # Process each layer
    try:
        for i in range(1, args["layers"] + 1):
            process_layer(i)
    except KeyboardInterrupt:
        logger.info("Finishing layer processing (KeyboardInterrupt)")
    except Exception:
        logger.critical(
            f"An unexpected exception occurred during processing layer {i} - {traceback.format_exc()}"
        )
        sys.exit(1)

    if args["formatJSON"]:
        try:
            layerHandler.json_dump()
            logger.info("Stored JSON at dump.json")
        except Exception:
            logger.error(f"Failed to dump JSON: {traceback.format_exc()}")

    logger.info(
        f"""{Fore.LIGHTGREEN_EX}Stored {args['layers']} layers: {get_dump_size()}"""
    )

    if args["notify"]:
        winsound.PlaySound("notif.wav", winsound.SND_ALIAS)

# Sound effects obtained from https://www.zapsplat.com
