import sys
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QWidget
from gui import Ui_MainWindow
import os
import tkinter
import json

from functions.processing import checkSubreddit


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

    """
    Signal/slot functions
    """

    def set_directory(self):
        dir = QFileDialog.getExistingDirectory(None, 'Select a folder to dump data in:', 'C:\\', QFileDialog.ShowDirsOnly)
        if self.files_exist(dir):
            ret = QMessageBox.warning(
                self, self.tr("Kularity"),
                self.tr(f"There are existing files in {dir}.\n" + \
                        "Are you sure you want to use this directory?"),
                QMessageBox.Yes | QMessageBox.No)

            if ret == QMessageBox.Yes:
                self.ui.dir.setText(os.path.abspath(dir))
            else:
                self.ui.dir.setText(os.path.abspath(os.path.join(dir, 'dump')))

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
        self.ui.tabWidget.setCurrentWidget(self.ui.tabWidget.findChild(QWidget, "formulae"))

    def check_subreddit(self):
        # Thread(target=self.check_subreddit_thread()).start()
        pass

    def add_filtering(self):
        vars = self.get_filtering_vars()

        user = vars['input'].text()
        if len(user) > 3:
            vars['widget'].addItem(user)
            vars['input'].setText("")

    def load_filtering(self):
        vars = self.get_filtering_vars()

        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Open list"),
            os.environ['USERPROFILE']
        )[:-1]

        users = []
        for f in fileName:
            try:
                with open(f, 'r') as f:
                    users.extend(f.read().replace('\r', '').split('\n'))
            except UnicodeDecodeError:
                QMessageBox.error(
                    self, self.tr("Kularity"),
                    self.tr(f"{f} is not a valid file"),
                    QMessageBox.Ok)
                return

        vars['widget'].addItems(users)
        QMessageBox.information(
            self, self.tr("Kularity"),
            self.tr(f"Added {len(users)} users"),
            QMessageBox.Ok)

    def remove_filtering(self):
        vars = self.get_filtering_vars()

        vars['widget'].takeItem(vars['widget'].currentRow())

    def clear_filtering(self):
        vars = self.get_filtering_vars()

        length = len(self.get_listwidget_items(vars['widget']))
        if length > 0:
            ret = QMessageBox.warning(
                self, self.tr("Kularity"),
                self.tr(f"Are you sure you want to clear the list?\nThere are {length} items."),
                QMessageBox.Yes | QMessageBox.No)

            if ret == QMessageBox.Yes:
                vars['widget'].clear()
                QMessageBox.information(
                    self, self.tr("Kularity"),
                    self.tr(f"Cleared {length} items"),
                    QMessageBox.Ok,
                )

    def start_scraping(self):
        pass

    def load_args(self):
        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Open list"),
            os.environ['USERPROFILE']
        )[0]

        if fileName:
            args = json.load(open(fileName, 'r'))
            self.set_args(args)

    def save_args(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save arguments to file', os.environ['USERPROFILE'], selectedFilter='*.json')[0]
        print(fileName)

        if fileName:
            if os.path.isfile(fileName):
                if QMessageBox.warning(
                    self, self.tr("Kularity"),
                    self.tr(f"{fileName} already exists. Are you sure you want to overwrite this file?"),
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.No:
                    return

            args = self.get_args()
            json.dump(args, open(fileName, 'w'))

            QMessageBox.information(
                self, self.tr("Kularity"),
                self.tr(f"Arguments saved to {fileName}"),
                QMessageBox.Ok,
            )

    def convert_args_bat(self):
        pass

    def convert_args_cmd(self):
        pass

    def load_default_args(self):
        if QMessageBox.warning(
            self, self.tr("Kularity"),
            self.tr("Are you sure you want to reset to default arguments?"),
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
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
            "noInput": False,
            "formatJSON": ref.formatJSON.isChecked(),
            "blockUsers": blockUsers,
            "blockSubreddits": blockSubreddits,
            "blockNSFW": ref.blockNSFW.isChecked(),
            "minScore": -10000000,
            "maxScore": 10000000,
            "minTime": None,
            "restrictSubs": self.get_listwidget_items(self.filterMapping[2]['widget']),
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
            "dir": os.path.abspath(os.path.join(os.getcwd(), 'dump')),
            "normalize": False,
            "noInput": False,
            "formatJSON": False,
            "blockUsers": {
                "active": False,
                "content": []
            },
            "blockSubreddits": {
                "active": False,
                "content": []
            },
            "blockNSFW": False,
            "minScore": -10000000,
            "maxScore": 10000000,
            "minTime":     None,
            "restrictSubs": [],
            "notify": True,
            "gui": False
        }

    def set_args(self, args):
        self.ui.startingPostLimit.setValue(args['startingPostLimit'])
        self.ui.startingSubreddit.setText(args['startingSubreddit'])
        self.ui.postCommentLimit.setValue(args['postCommentLimit'])
        self.ui.userCommentLimit.setValue(args['userCommentLimit'])
        self.ui.userLimit.setValue(args['userLimit'])
        self.ui.submissionLimit.setValue(args['submissionLimit'])
        self.ui.verbose.setChecked(args['verbose'])
        self.ui.fileLogging.setChecked(args['fileLogging'])
        self.ui.layers.setValue(args['layers'])
        self.ui.dir.setText(args['dir'])
        self.ui.normalize.setChecked(args['normalize'])
        self.handle_normalize()
        self.ui.formatJSON.setChecked(args['formatJSON'])

        self.ui.blockedUsersList_2.clear()
        self.ui.blockedUsersList_2.addItems(args['blockUsers']['content'])

        self.ui.blockedSubredditsList.clear()
        self.ui.blockedSubredditsList.addItems(args['blockSubreddits']['content'])

        self.ui.restrictedSubredditList.clear()
        self.ui.restrictedSubredditList.addItems(args['restrictSubs'])

        self.ui.blockNSFW.setChecked(args['blockNSFW'])
        self.ui.notify.setChecked(args['notify'])

        self.ui.startingSort.setCurrentIndex(
            self.ui.startingSort.findText(args['startingSort'], QtCore.Qt.MatchFixedString)
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
                self, self.tr("Kularity"),
                self.tr(f"r/{name} is invalid\n" + \
                        "You should choose another subreddit."),
                QMessageBox.Ok)
            self.ui.startingSubreddit.setText("all")

    def get_filtering_vars(self):
        return self.filterMapping[self.ui.tabWidget_2.currentIndex()]

    def get_listwidget_items(self, widget):
        return [widget.item(i) for i in range(widget.count() - 1)]

    def handle_list(self, index):
        fv = self.filterMapping[index]['widget']
        items = self.get_listwidget_items(fv)
        return {
            "active": len(items) > 0,
            "content": items,
        }


app = QApplication(sys.argv)

window = MainWindow()
window.setup()
window.show()

sys.exit(app.exec_())
