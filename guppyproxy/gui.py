import random
import threading

from .util import printable_data
from .proxy import InterceptMacro, HTTPRequest
from .reqlist import ReqListUpdater, ReqBrowser
from .reqview import ReqViewWidget
from .repeater import RepeaterWidget
from .interceptor import InterceptorWidget
from .decoder import DecoderWidget
from .hexteditor import ComboEditor, HexEditor
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QTabWidget, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject, Qt
            
class GuppyWindow(QWidget):
    titles = (
        "Guppy Proxy",
        "Super Hacker Proxy 3000",
        "Proxicado",
        "Proxy Attack Proxy ProxY",
        "Slurp Bruite",
        "Pappy",
        "Sports.exe",
        "Gappy",
        "Mickosoft Accel",
        "Microsoft Word '98",
    )
    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        self.initUi()

    def initUi(self):
        self.setFocusPolicy(Qt.StrongFocus)
        tabWidget = QTabWidget()
        repeaterWidget = RepeaterWidget(self.client)
        self.interceptorWidget = InterceptorWidget(self.client)
        historyWidget = ReqBrowser(self.client, repeater_widget=repeaterWidget)
        decoderWidget = DecoderWidget()

        tabWidget.addTab(historyWidget, "History")
        tabWidget.addTab(repeaterWidget, "Repeater")
        tabWidget.addTab(self.interceptorWidget, "Interceptor")
        tabWidget.addTab(decoderWidget, "Decoder")

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(tabWidget)

        #self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle(random.choice(GuppyWindow.titles))
        self.show()
        
    def close(self):
        self.interceptorWidget.close()

