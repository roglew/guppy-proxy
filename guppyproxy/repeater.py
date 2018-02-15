from .util import display_error_box
from .reqview import ReqViewWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSlot


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

        self.reqview = ReqViewWidget(tag_tab=True)
        self.reqview.set_read_only(False)
        self.reqview.set_tags_read_only(False)
        self.layout().addLayout(buttons)
        self.layout().addWidget(self.reqview)

        self.req = None
        self.dest_host = ""
        self.dest_port = 80
        self.use_tls = False

    def set_request(self, req):
        self.req = req
        self.dest_host = ""
        self.dest_port = -1
        self.use_tls = False
        if req:
            self.req = req
            self.req.tags = set(["repeater"])
            self.dest_host = req.dest_host
            self.dest_port = req.dest_port
            self.use_tls = req.use_tls
        self.reqview.set_request(self.req)

    @pyqtSlot(set)
    def update_req_tags(self, tags):
        if self.req:
            self.req.tags = tags

    @pyqtSlot()
    def submit(self):
        req = self.reqview.get_request()
        if not req:
            display_error_box("Could not parse request")
            return
        req.tags.add("repeater")
        self.client.submit(req, save=True)
        self.req = req
        self.set_request(req)
