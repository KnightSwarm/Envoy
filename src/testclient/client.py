import sys, time
from PyQt4.QtGui import QApplication, QMainWindow
from ui.main import Ui_MainWindow
from core import application

app = QApplication(sys.argv)
window = QMainWindow()
ui = Ui_MainWindow()
ui.setupUi(window)
window.setWindowTitle("Envoy Test Client")

main_thread = application.ApplicationThread()
main_thread.start()

window.show()
return_code = app.exec_()
main_thread.stop()

sys.exit(return_code)
