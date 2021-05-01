import praw
import dotenv
import os
import itertools
from colorama import Fore, Style
import traceback

from functions.general import progress_bar, normalize_range

dotenv.load_dotenv()

id = os.getenv("client_id")
secret = os.getenv("client_secret")
ua = os.getenv("user_agent")

from_iterable = itertools.chain.from_iterable

r = praw.Reddit(client_id=id, client_secret=secret, user_agent=ua)
r.config.log_requests = 0
skw = Fore.CYAN
ekw = Style.RESET_ALL


def clean_users(userList):
    return [i for i in userList if i not in blockedUsers]


def set_lp_logger(_logger, _verbose):
    global logger
    global verbose
    logger = _logger
    verbose = _verbose


def set_blocked(
    users,
    nsfw,
    subreddits,
    minScore,
    maxScore,
    restrictSubs,
):
    global blockedUsers
    global blockedSubreddits
    global blockNSFW
    global scoreRange
    global restrictedSubs

    blockedUsers = users["content"]
    logger.info(f"Loaded {Fore.CYAN}{len(blockedUsers)}{Style.RESET_ALL} blocked users")

    blockedSubreddits = subreddits["content"]
    logger.info(
        f"Loaded {Fore.CYAN}{len(blockedSubreddits)}{Style.RESET_ALL} blocked subreddits"
    )

    blockNSFW = nsfw
    logger.info("Blocking nsfw" if blockNSFW else "Not blocking nsfw")
    if blockNSFW:
        logger.warning("Blocking nsfw may skip many users")

    scoreRange = (minScore, maxScore)
    logger.info(f"Set score range {scoreRange[0]} to {scoreRange[1]}")

    restrictedSubs = {
        "active": True if len(restrictSubs) > 0 else False,
        "subs": [r.subreddit(i) for i in restrictSubs],
    }
    if len(restrictedSubs) > 0:
        logger.info(f"Restricting to {len(restrictSubs)} subreddits")


def checkSafe(subj):
    """
    False: NSFW
    True: Safe
    """
    try:
        if blockNSFW and subj.subreddit["over_18"]:
            logger.warning(f"Blocked nsfw {subj.name}")
            return False
    except Exception:
        if blockNSFW and subj.over18:
            logger.warning(f"Blocked subreddit {subj.display_name_prefixed}")
            return False
    return True


def checkSub(subj):
    if restrictedSubs["active"]:
        if subj not in restrictedSubs["subs"]:
            return False
    return True


def users_from_posts(subreddit, sorting="hot", limit=100):
    """
    Collects submission IDs with author names from a subreddit
    from a starting point

    Parameters:
        subreddit   (str)               Subreddit to scrape
        sorting     (str)   ["top"]     Sorting to scrape with
        limit       (int)   [100]       Max submissions

    Returns:
        (list)
        [
            (
                submission (Submission),
                ...
            ),
            (
                author (Redditor),
                ...
            )
        ]
    """
    if limit is None:
        limit = 100

    logger.debug(
        f"Getting {skw}{limit}{ekw} posts from r/{skw}{subreddit}{ekw} sorting by {skw}{sorting}{ekw}"
    )
    method = getattr(r.subreddit(subreddit), sorting)
    posts = method(limit=limit)
    lp = list(posts)
    logger.debug(f"Got {skw}{len(lp)}/{limit}{ekw} posts")
    values = [
        (i, i.author)
        for i in lp
        if (i.author.name not in blockedUsers and checkSafe(i.author))
    ]
    return [i[0] for i in values], [i[1] for i in values]


def get_post_comments(submission, limit=5000):
    """
    Get comment authors from submission

    Parameters:
        submission  (Submission)            Submission to use
                    (list/tuple)
        limit       (int)           [5000]  Max commments to get

    Returns:
        (list)
        [
            author (Redditor),
            ...
        ]
    """
    if verbose:
        logger.info(
            f"Getting {skw}{limit}{ekw} comments from {skw}{len(submission)}{ekw} submissions"
        )

    def getData(submission):
        if verbose:
            logger.debug(
                f"Getting {skw}{limit}{ekw} comments from submission {skw}{submission.id}{ekw}"
            )

        if not checkSafe(submission.subreddit):
            logger.warning(f"Skipping {skw}{submission.id}{ekw} (NSFW)")
            return ()
        # submission.comments.replace_more(limit=None)
        queue = submission.comments[:]

        data = []
        while queue and limit > len(data):
            try:
                comment = queue.pop(0)
            except IndexError:
                break
            try:
                if comment.author not in blockedUsers and checkSafe(comment.author):
                    data.append(comment.author)
                if limit > len(data):
                    queue.extend(comment.replies)
            except Exception:
                break

        if verbose:
            logger.debug(
                f"Got {skw}{len(data)}{ekw}/{skw}{limit}{ekw} comments from {skw}{submission.id}"
            )
        return tuple(dict.fromkeys(data))

    def handleIteration(s, i, _max):
        data = getData(s)
        progress_bar(i + 1, _max)
        return data

    if isinstance(submission, (list, tuple)):
        _max = len(submission)
        return list(
            from_iterable(
                [handleIteration(s, i, _max) for i, s in enumerate(submission)]
            )
        )
    else:
        return getData(submission)


def get_user_comments(
    user,
    normalize,
    sorting="new",
    limit=None,
    limitUsers=None,
    submissionLimit=10,
    userID=1,
    lenUsers=1,
):
    """
    Gets a maximum of 1000 comments from a users profile along
    with their scores. The author of the submission of each
    comment will also be supplied.

    Parameters:
        username    (Redditor)              Username to scrape from
        normalized  (dict)                  Normalize argument
        sorting     (str)       ["new"]     Sorting to scrape with
        limit       (int/None)  [None]      Max comments to scrape

    Returns:
        (list)
        [
            (
                submissionAuthor (Redditor),
                ...
            ),
            (
                {
                    "comment": commentExample (str),
                    "score": score (int)
                },
                ...
            )
        ]
    """
    if isinstance(user, str):
        try:
            user = r.redditor(user)
        except Exception:
            logger.warning(f"u/{user} cannot be found")
            return ((), ())
    if verbose:
        logger.info(
            f"Getting {skw}{limit}{ekw} comments from u/{skw}{user.name}{ekw} sorting by {skw}{sorting}{ekw} (limitUsers={skw}{limitUsers}{ekw}, submissionLimit={skw}{submissionLimit}{ekw})"
        )

    def getData(user, baseCommentsSaved):
        if verbose:
            logger.debug(f"Getting {skw}{limit}{ekw} comments from {skw}{user.name}")

        if not checkSafe(user):
            return ((), ())

        method = getattr(user.comments, sorting)
        response = method(limit=limit)
        lr = list(response)
        if verbose:
            logger.debug(f"Got response of {len(lr)} items")
        commentData, submissionData = [], []

        for j, i in enumerate(lr):
            try:
                if len(submissionData) < submissionLimit:
                    if i.submission.author not in blockedUsers:
                        if checkSub(i.submission.subreddit):
                            submissionData.append(i.submission.author)
                            if verbose:
                                logger.debug(
                                    f"Collected submission author u/{skw}{i.submission.author}"
                                )
                        else:
                            logger.warning(f"Skipping beyond restriction")
                    commentData.append(
                        {
                            "comment": i.body,
                            "score": normalize_range(
                                i.score,
                                _max=normalize["max"],
                                _min=normalize["min"],
                            )
                            if normalize["normalize"]
                            else i.score,
                        }
                    )

                if not verbose:
                    progress_bar(
                        baseCommentsSaved[0] + len(commentData),
                        maxCommentsSaved,
                        alwaysReturn=True,
                    )
            except AttributeError:
                # NoneType (user is deleted or banned)
                logger.warning(f"{skw}{i}{ekw} is deleted/banned/otherwise")
                pass

        if verbose:
            logger.info(
                f"Received {skw}{len(commentData)}{ekw} comments for u/{skw}{user.name}"
            )
            logger.info(
                f"Received {skw}{len(submissionData)}{ekw} submission authors for u/{skw}{user.name}"
            )
        return tuple(dict.fromkeys(submissionData)), tuple(commentData)

    if isinstance(user, (list, tuple)):
        if limitUsers is None:
            limitUsers = len(user)

        commentData, submissionData = [], []
        listIter = user[:limitUsers]
        maxCommentsSaved = len(listIter) * limit  # Target comments (max)
        baseCommentsSaved = 0
        progress_bar(baseCommentsSaved, maxCommentsSaved)

        for i, u in enumerate(listIter):
            tmpSubmission, tmpComment = getData(u, baseCommentsSaved)
            commentData.extend(tmpComment)
            submissionData.extend(tmpSubmission)
            baseCommentsSaved += limit

        logger.info(
            f"Received {skw}{len(commentData)}{ekw} comments for {skw}{limitUsers}{ekw}/{skw}{len(user)}{ekw} users"
        )
        logger.info(
            f"Received {skw}{len(submissionData)}{ekw} submission authors for {skw}{limitUsers}{ekw}/{skw}{len(user)}{ekw} users"
        )

        return (tuple(submissionData), tuple(commentData))
    else:
        maxCommentsSaved = (lenUsers + 1) * limit  # Target comments (max)
        baseCommentsSaved = userID * limit
        try:
            rval = getData(user, (baseCommentsSaved, maxCommentsSaved))
        except Exception:
            logger.error(traceback.format_exc())
            rval = ((), ())
        return rval
