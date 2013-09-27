# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt4 UI code generator 4.9.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(972, 679)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.listview_rooms = QtGui.QListView(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listview_rooms.sizePolicy().hasHeightForWidth())
        self.listview_rooms.setSizePolicy(sizePolicy)
        self.listview_rooms.setMinimumSize(QtCore.QSize(150, 0))
        self.listview_rooms.setMaximumSize(QtCore.QSize(150, 16777215))
        self.listview_rooms.setObjectName(_fromUtf8("listview_rooms"))
        self.horizontalLayout.addWidget(self.listview_rooms)
        self.line = QtGui.QFrame(self.centralwidget)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.horizontalLayout.addWidget(self.line)
        self.webview_room = QtWebKit.QWebView(self.centralwidget)
        self.webview_room.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webview_room.setObjectName(_fromUtf8("webview_room"))
        self.horizontalLayout.addWidget(self.webview_room)
        self.listview_users = QtGui.QListView(self.centralwidget)
        self.listview_users.setMinimumSize(QtCore.QSize(220, 0))
        self.listview_users.setMaximumSize(QtCore.QSize(220, 16777215))
        self.listview_users.setObjectName(_fromUtf8("listview_users"))
        self.horizontalLayout.addWidget(self.listview_users)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout)
        self.webview_debug = QtWebKit.QWebView(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.webview_debug.sizePolicy().hasHeightForWidth())
        self.webview_debug.setSizePolicy(sizePolicy)
        self.webview_debug.setMinimumSize(QtCore.QSize(0, 140))
        self.webview_debug.setMaximumSize(QtCore.QSize(16777215, 140))
        self.webview_debug.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webview_debug.setObjectName(_fromUtf8("webview_debug"))
        self.verticalLayout_2.addWidget(self.webview_debug)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 972, 25))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))

from PyQt4 import QtWebKit
