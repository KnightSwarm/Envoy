import sys, time
from PyQt4.QtCore import *
from PyQt4.QtGui import QApplication, QMainWindow
from ui.main import Ui_MainWindow
from core import application

class RoomListModel(QAbstractListModel):
	def __init__(self, source, *args, **kwargs):
		QAbstractListModel.__init__(self, *args, **kwargs)
		self._source = source

app = QApplication(sys.argv)
window = QMainWindow()
ui = Ui_MainWindow()
ui.setupUi(window)

print ui.listview_rooms
window.setWindowTitle("Envoy Test Client")

main_thread = application.ApplicationThread()
main_thread.start()

handler = main_thread.main_application.handler
ui.listview_rooms.setModel(RoomListModel(handler._rooms))

window.show()
return_code = app.exec_()
main_thread.stop()

sys.exit(return_code)
