import sys
from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QWidget,
)
from gui import Ui_MainWindow
import os
import tkinter
import json
import clipboard
import traceback
import logging
from pathlib import Path
import time
from threading import Thread

from functions.processing import checkSubreddit
from functions.general import _human_bytes, get_file_handle, handle_time, get_subs
from functions.formatters import CustomFormatter, CustomCleanFormatter


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    def setup(self):
        self.set_args(self.get_default_args())
        self.filterMapping = {
            0: {
                "input": self.ui.addUser_2,
                "widget": self.ui.blockedUsersList_2,
            },
            1: {
                "input": self.ui.addSubreddit,
                "widget": self.ui.blockedSubredditsList,
            },
            2: {
                "input": self.ui.addRestrictedSub,
                "widget": self.ui.restrictedSubredditList,
            },
        }
        self.ui.status.setStyleSheet("color: rgb(226, 15, 15);")

    """
    Signal/slot functions
    """

    def set_directory(self):
        dir = QFileDialog.getExistingDirectory(
            None, "Select a folder to dump data in:", "C:\\", QFileDialog.ShowDirsOnly
        )
        if self.files_exist(dir):
            ret = QMessageBox.warning(
                self,
                self.tr("Kularity"),
                self.tr(
                    f"There are existing files in {dir}.\n"
                    + "Are you sure you want to use this directory?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if ret == QMessageBox.No:
                self.ui.dir.setText(os.path.abspath(os.path.join(dir, "dump")))
                return

        self.ui.dir.setText(os.path.abspath(dir))

    def toggle_normalize(self):
        self.handle_normalize()

    def min_changed(self):
        min, max = self.ui.normalizeMin.value(), self.ui.normalizeMax.value()
        if min > max:
            self.ui.normalizeMax.setValue(min)

    def max_changed(self):
        min, max = self.ui.normalizeMin.value(), self.ui.normalizeMax.value()
        if min > max:
            self.ui.normalizeMin.setValue(max)

    def view_formulae(self):
        self.ui.tabWidget.setCurrentWidget(
            self.ui.tabWidget.findChild(QWidget, "formulae")
        )

    def check_subreddit(self):
        # Thread(target=self.check_subreddit_thread()).start()
        pass

    def add_filtering(self):
        vars = self.get_filtering_vars()

        user = vars["input"].text()
        if len(user) > 3:
            vars["widget"].addItem(user)
            vars["input"].setText("")

    def load_filtering(self):
        vars = self.get_filtering_vars()

        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Open list"),
            os.path.join(os.environ["USERPROFILE"], "desktop"),
        )[:-1]

        users = []
        for f in fileName:
            try:
                with open(f, "r") as f:
                    users.extend(f.read().replace("\r", "").split("\n"))
            except UnicodeDecodeError:
                QMessageBox.error(
                    self,
                    self.tr("Kularity"),
                    self.tr(f"{f} is not a valid file"),
                    QMessageBox.Ok,
                )
                return

        vars["widget"].addItems(users)
        QMessageBox.information(
            self,
            self.tr("Kularity"),
            self.tr(f"Added {len(users)} users"),
            QMessageBox.Ok,
        )

    def remove_filtering(self):
        vars = self.get_filtering_vars()

        vars["widget"].takeItem(vars["widget"].currentRow())

    def clear_filtering(self):
        vars = self.get_filtering_vars()

        length = len(self.get_listwidget_items(vars["widget"]))
        if length > 0:
            ret = QMessageBox.warning(
                self,
                self.tr("Kularity"),
                self.tr(
                    f"Are you sure you want to clear the list?\nThere are {length} items."
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if ret == QMessageBox.Yes:
                vars["widget"].clear()
                QMessageBox.information(
                    self,
                    self.tr("Kularity"),
                    self.tr(f"Cleared {length} items"),
                    QMessageBox.Ok,
                )

    def reset_pb(self):
        self.ui.singlepb.setValue(0)
        self.ui.layerpb.setValue(0)

    def start_scraping(self):

        self.reset_pb()
        self.ui.pushButton_3.setEnabled(False)
        self.ui.pushButton_3.setText("Scraping..")
        self.status("Starting..")
        self.ui.status.setStyleSheet("color: rgb(15, 226, 17);")
        self.ui.tabWidget.setEnabled(False)

        try:
            QApplication.instance().processEvents()
            Thread(target=self.scrape).start()
        except Exception:
            print(traceback.format_exc())

    def scrape(self):
        def process_layer(layer):
            self.status(f"Processing layer {layer}... ({get_dump_size()})")
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
                    sorting="hot",
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
                f"Finished processing layer {layer} (Elapsed {round(end-start, 2)}s)"
            )

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
                return

            # Dump scraped comments to database
            layerHandler.dump_data(comments)

            # Dump to layer 1
            layerHandler.dump_build_layer(1, initialUserCollection)
            logger.info("Finished building layer 1")

        def get_dump_size():
            return _human_bytes(os.path.getsize(os.path.join(args["dir"], "dump.db")))

        def build_normalize(normalize):
            if normalize in (None, False):
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

        def handle_errors(func, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.error(
                    f"Error calling {func.__name__} with args {', '.join(list(args))}, kwargs {dict(kwargs)}: {traceback.format_exc()}"
                )
                return

        args = self.get_args()
        start = time.time()
        self.status("Setting up..")

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

        if args["fileLogging"]:
            fileHandler = logging.FileHandler(
                os.path.join(args["dir"], "build/log.log")
            )
            fileHandler.setLevel(logging.DEBUG)
            fileHandler.setFormatter(CustomCleanFormatter(args["fileLogging"]))

            logger.addHandler(fileHandler)

        if args["verbose"]:
            logger.setLevel(logging.DEBUG)
            consoleHandler.setLevel(logging.DEBUG)

        # Import necesssary functions
        # This is delayed to allow parsing arguments to be faster
        from functions.processing_gui import (
            users_from_posts,
            get_post_comments,
            get_user_comments,
            set_lp_logger,
            set_blocked,
            set_progress,
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
        set_progress(self.ui.singlepb)

        self.status("Creating layer 1..")

        # Create first layer
        try:
            QApplication.instance().processEvents()
            creation_process()
        except Exception:
            self.error(
                f"An unexpected exception occurred during creation - {traceback.format_exc()}"
            )

        self.status("Begin processing layers..")

        # Process each layer
        try:
            self.ui.layerpb.setMaximum(args["layers"] + 1)
            for i in range(1, args["layers"] + 1):
                QApplication.instance().processEvents()
                process_layer(i)
                self.ui.layerpb.setValue(i + 1)
        except Exception:
            self.error(
                f"An unexpected exception occurred during processing layer {i} - {traceback.format_exc()}"
            )

        if args["formatJSON"]:
            self.status("Formatting json..")
            try:
                layerHandler.json_dump()
            except Exception:
                self.error(f"Failed to dump JSON: {traceback.format_exc()}")

        if args["notify"]:
            winsound.PlaySound("notif.wav", winsound.SND_ALIAS | winsound.SND_ASYNC)

        self.status(f"Completed! (Elapsed {round(time.time() - start, 2)}s)")

        QMessageBox.information(
            self,
            self.tr("Kularity"),
            self.tr(f"""Stored {args['layers']} layers: {get_dump_size()}"""),
            QMessageBox.Ok,
        )

        self.reset_pb()
        self.ui.pushButton_3.setEnabled(True)
        self.ui.pushButton_3.setText("Start scraping")
        self.status("Inactive")
        self.ui.status.setStyleSheet("color: rgb(226, 15, 15);")
        self.ui.tabWidget.setEnabled(True)

    def load_args(self):
        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Open list"),
            os.path.join(os.environ["USERPROFILE"], "desktop"),
        )[0]

        if fileName:
            try:
                args = json.load(open(fileName, "r"))
            except Exception:
                return QMessageBox.critical(
                    self,
                    self.tr("Kularity"),
                    self.tr(f"{fileName} has an invalid format."),
                    QMessageBox.Ok,
                )
            self.set_args(args)

    def save_args(self):
        fileName = QFileDialog.getSaveFileName(
            self,
            "Save arguments to file",
            os.path.join(os.environ["USERPROFILE"], "desktop"),
            selectedFilter="*.json",
        )[0]

        if fileName:
            if os.path.isfile(fileName):
                if (
                    QMessageBox.warning(
                        self,
                        self.tr("Kularity"),
                        self.tr(
                            f"{fileName} already exists. Are you sure you want to overwrite this file?"
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    == QMessageBox.No
                ):
                    return

            args = self.get_args()
            json.dump(args, open(fileName, "w"))

            QMessageBox.information(
                self,
                self.tr("Kularity"),
                self.tr(f"Arguments saved to {fileName}"),
                QMessageBox.Ok,
            )

    def convert_args_bat(self):
        fileName = QFileDialog.getSaveFileName(
            self,
            "Save arguments to bat",
            os.path.join(os.environ["USERPROFILE"], "desktop"),
            selectedFilter="*.bat",
        )[0]

        if fileName:
            args = self.get_args()
            converted = self.convert_args(args, "bat")
            with open(fileName, "w") as f:
                f.write(converted)
                print(converted)

            QMessageBox.information(
                self,
                self.tr("Kularity"),
                self.tr(f"Argument batchfile saved to {fileName}"),
                QMessageBox.Ok,
            )

    def convert_args_cmd(self):
        args = self.get_args()
        converted = self.convert_args(args, "cmd")
        clipboard.copy(converted)

        QMessageBox.information(
            self,
            self.tr("Ksularity"),
            self.tr(f"Command copied to clipboard\nCommand: {converted}"),
            QMessageBox.Ok,
        )

    def load_default_args(self):
        if (
            QMessageBox.warning(
                self,
                self.tr("Kularity"),
                self.tr("Are you sure you want to reset to default arguments?"),
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.set_args(self.get_default_args())

    """
    Other functions
    """

    def get_args(self):
        ref = self.ui

        if ref.normalize.isChecked():
            normalize = (ref.normalizeMin.value(), ref.normalizeMax.value())
        else:
            normalize = False

        blockUsers = self.handle_list(0)
        blockSubreddits = self.handle_list(1)

        return {
            "startingPostLimit": ref.startingPostLimit.value(),
            "startingSubreddit": ref.startingSubreddit.text(),
            "startingSort": ref.startingSort.currentText(),
            "postCommentLimit": ref.postCommentLimit.value(),
            "userCommentLimit": ref.userCommentLimit.value(),
            "userLimit": ref.userLimit.value(),
            "submissionLimit": ref.submissionLimit.value(),
            "verbose": ref.verbose.isChecked(),
            "fileLogging": ref.fileLogging.isChecked(),
            "layers": ref.layers.value(),
            "dir": ref.dir.text(),
            "normalize": normalize,
            "noInput": True,
            "formatJSON": ref.formatJSON.isChecked(),
            "blockUsers": blockUsers,
            "blockSubreddits": blockSubreddits,
            "blockNSFW": ref.blockNSFW.isChecked(),
            "minScore": -10000000,
            "maxScore": 10000000,
            "minTime": None,
            "restrictSubs": self.get_listwidget_items(self.filterMapping[2]["widget"]),
            "notify": ref.notify.isChecked(),
            "gui": False,
        }

    def get_default_args(self):
        return {
            "startingPostLimit": 100,
            "startingSubreddit": "all",
            "startingSort": "hot",
            "postCommentLimit": 5000,
            "userCommentLimit": 1000,
            "userLimit": 10000000,
            "submissionLimit": 15,
            "verbose": False,
            "fileLogging": False,
            "layers": 3,
            "dir": os.path.abspath(os.path.join(os.getcwd(), "dump")),
            "normalize": False,
            "formatJSON": False,
            "blockUsers": {"active": False, "content": []},
            "blockSubreddits": {"active": False, "content": []},
            "blockNSFW": False,
            "minScore": -10000000,
            "maxScore": 10000000,
            "minTime": None,
            "restrictSubs": [],
            "notify": True,
            "gui": False,
            "noInput": True,
        }

    def set_args(self, args):
        normalize = not (isinstance(args["normalize"], bool))

        self.ui.startingPostLimit.setValue(args["startingPostLimit"])
        self.ui.startingSubreddit.setText(args["startingSubreddit"])
        self.ui.postCommentLimit.setValue(args["postCommentLimit"])
        self.ui.userCommentLimit.setValue(args["userCommentLimit"])
        self.ui.userLimit.setValue(args["userLimit"])
        self.ui.submissionLimit.setValue(args["submissionLimit"])
        self.ui.verbose.setChecked(args["verbose"])
        self.ui.fileLogging.setChecked(args["fileLogging"])
        self.ui.layers.setValue(args["layers"])
        self.ui.dir.setText(args["dir"])
        self.ui.normalize.setChecked(normalize)

        if normalize:
            self.ui.normalizeMin.setValue(args["normalize"][0])
            self.ui.normalizeMax.setValue(args["normalize"][1])

        self.handle_normalize()
        self.ui.formatJSON.setChecked(args["formatJSON"])

        self.ui.blockedUsersList_2.clear()
        self.ui.blockedUsersList_2.addItems(args["blockUsers"]["content"])

        self.ui.blockedSubredditsList.clear()
        self.ui.blockedSubredditsList.addItems(args["blockSubreddits"]["content"])

        self.ui.restrictedSubredditList.clear()
        self.ui.restrictedSubredditList.addItems(args["restrictSubs"])

        self.ui.blockNSFW.setChecked(args["blockNSFW"])
        self.ui.notify.setChecked(args["notify"])

        self.ui.startingSort.setCurrentIndex(
            self.ui.startingSort.findText(
                args["startingSort"], QtCore.Qt.MatchFixedString
            )
        )

    def handle_normalize(self):
        checked = self.ui.normalize.isChecked()
        print(checked)
        self.ui.normalizeMin.setEnabled(checked)
        self.ui.normalizeMax.setEnabled(checked)

    def files_exist(self, dir):
        files = [i for i in os.listdir(dir) if i != "build"]
        return len(files) > 0

    def show_images(self, imagePaths):
        root = tkinter.Tk()
        canvas = tkinter.Canvas(root, width=1500, height=400)
        canvas.pack()
        imgs = [tkinter.PhotoImage(file=i) for i in imagePaths]
        x = 0
        for i in imgs:
            canvas.create_image(0, x, anchor=tkinter.NW, image=i)
            x += 500
        root.mainloop()

    def check_subreddit_thread(self):
        name = self.ui.startingSubreddit.text()
        if not checkSubreddit(name):
            QMessageBox.warning(
                self,
                self.tr("Kularity"),
                self.tr(
                    f"r/{name} is invalid\n" + "You should choose another subreddit."
                ),
                QMessageBox.Ok,
            )
            self.ui.startingSubreddit.setText("all")

    def get_filtering_vars(self):
        return self.filterMapping[self.ui.tabWidget_2.currentIndex()]

    def get_listwidget_items(self, widget):
        return [widget.item(i).text() for i in range(widget.count())]

    def handle_list(self, index):
        fv = self.filterMapping[index]["widget"]
        items = self.get_listwidget_items(fv)
        return {
            "active": len(items) > 0,
            "content": items,
        }

    def error(self, txt):
        QMessageBox.critical(
            self,
            self.tr("Kularity"),
            self.tr(txt),
            QMessageBox.Ok,
        )

    def status(self, txt):
        self.ui.status.setText(txt)

    def convert_args(self, args, to):
        def build_line(args):
            formattedArgs = []
            print(args)

            for k, v in args.items():
                print(k, v)
                if v in (False, None):
                    continue
                elif v is True:
                    v = ""

                if isinstance(v, (tuple, list)):
                    if len(v) == 0:
                        continue
                    v = " ".join([str(i) for i in v])
                elif isinstance(v, dict):
                    if not v["active"] or len(v["content"]) == 0:
                        continue
                    fn = os.path.join(os.environ["TEMP"], f"tmp-{k}.txt")
                    with open(fn, "w") as f:
                        f.write("\n".join(v["content"]))
                    v = fn

                if k == "dir":
                    v = f'"{v}"'

                finalv = f" {v}" if v != "" else ""

                formattedArgs.append(f"--{k}{finalv}")

            mainFile = os.path.join(os.getcwd(), "main.py")

            return f'python {mainFile} {" ".join(formattedArgs)}'

        if to == "cmd":
            return build_line(args)
        elif to == "bat":
            return f"""@echo off
title Kularity scraping
rem Bypass "Terminate Batch Job" prompt.
if "%~1"=="-FIXED_CTRL_C" (
   REM Remove the -FIXED_CTRL_C parameter
   SHIFT
) ELSE (
   REM Run the batch with <NUL and -FIXED_CTRL_C
   CALL <NUL %0 -FIXED_CTRL_C %*
   GOTO :EOF
)
cls
{build_line(args)}
pause
"""


app = QApplication(sys.argv)

window = MainWindow()
window.setup()
window.show()

sys.exit(app.exec_())
