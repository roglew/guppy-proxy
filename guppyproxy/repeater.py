from .util import printable_data, display_error_box
from .proxy import InterceptMacro, HTTPRequest, parse_request
from .reqview import ReqViewWidget
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QTabWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject


class RepeaterWidget(QWidget):

    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)

        submitButton = QPushButton("Submit")
        submitButton.clicked.connect(self.submit)
        buttons.addWidget(submitButton)
        buttons.addStretch()
        #buttons.addWidget(QPushButton("<"))
        #buttons.addWidget(QPushButton(">"))
        # widgets to set dest host/port/tls
        # checkbox to save inmem
        # some status label
        
        self.reqview = ReqViewWidget()
        self.reqview.req_edit.setReadOnly(False)
        self.layout().addLayout(buttons)
        self.layout().addWidget(self.reqview)
        
        self.req = None
        self.dest_host = ""
        self.dest_port = 80
        self.use_tls = False
        
    def set_request(self, req):
        self.req = req
        self.reqview.set_request(req)
        self.dest_host = req.dest_host
        self.dest_port = req.dest_port
        self.use_tls = req.use_tls

    #def set_dest(self, host, port, use_tls)

    @pyqtSlot()
    def submit(self):
        try:
            req = parse_request(self.reqview.req_edit.get_bytes())
        except:
            display_error_box("Could not parse request")
            return
        req.dest_host = self.dest_host
        req.dest_port = self.dest_port
        req.use_tls = self.use_tls
        self.client.submit(req, save=True)
        self.req = req
        self.set_request(req)

