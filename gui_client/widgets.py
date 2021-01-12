from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import QDate, QDateTime, QRect, QThread, QObject, pyqtSignal, QThreadPool, QRunnable, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog, QPushButton, QLabel, QGroupBox, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, \
    QMainWindow, QComboBox, QBoxLayout, QLineEdit, QDialog, QTextBrowser, QMessageBox, QRadioButton, QProgressBar, \
    QStackedWidget


class File(QGroupBox):
    def __init__(self, filename, deletebutton=False, movebutton=False):
        super(QGroupBox, self).__init__()

        self.setObjectName(filename)

        self.filename = filename
        self.deletebutton = deletebutton
        self.movebutton = movebutton

    def connect(self):
        pass

    def disconnect(self):
        pass
