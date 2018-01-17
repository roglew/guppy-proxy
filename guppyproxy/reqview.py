import threading

from .util import printable_data
from .proxy import InterceptMacro, HTTPRequest
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QLineEdit, QComboBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject

class ReqViewWidget(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.request = None
        self.layout = QGridLayout(self)
        self.layout.setSpacing(3)
        self.layout.setContentsMargins(0, 0, 0, 0)


        self.req_edit = QPlainTextEdit()
        self.rsp_edit = QPlainTextEdit()
        self.req_edit.setReadOnly(True)
        self.rsp_edit.setReadOnly(True)

        self.layout.addWidget(self.req_edit, 0, 0)
        self.layout.addWidget(self.rsp_edit, 0, 1)
        self.setLayout(self.layout)
        
    @pyqtSlot(HTTPRequest)
    def set_request(self, req):
        self.req = req
        self.update_editors()
        
    def update_editors(self):
        self.req_edit.setPlainText("")
        self.rsp_edit.setPlainText("")
        if self.req is not None:
            self.req_edit.setPlainText(printable_data(self.req.full_message()))
            if self.req.response is not None:
                self.rsp_edit.setPlainText(printable_data(self.req.response.full_message()))
