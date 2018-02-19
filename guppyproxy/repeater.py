from .util import display_error_box
from .reqview import ReqViewWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QCheckBox, QLabel, QSizePolicy
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
        buttons.setSpacing(8)

        submitButton = QPushButton("Submit")
        submitButton.clicked.connect(self.submit)
        self.dest_host_input = QLineEdit()
        self.dest_port_input = QLineEdit()
        self.dest_port_input.setMaxLength(5)
        self.dest_port_input.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.dest_usetls_input = QCheckBox()
        
        buttons.addWidget(submitButton)
        buttons.addWidget(QLabel("Host:"))
        buttons.addWidget(self.dest_host_input)
        buttons.addWidget(QLabel("Port:"))
        buttons.addWidget(self.dest_port_input)
        buttons.addWidget(QLabel("Use TLS:"))
        buttons.addWidget(self.dest_usetls_input)
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
        
    def _set_host(self, host):
        self.dest_host_input.setText(host)

    def _set_port(self, port):
        if port is None or port <= 0:
            self.dest_port_input.setText("")
        else:
            self.dest_port_input.setText(str(port))

    def _set_usetls(self, usetls):
        if usetls:
            self.dest_usetls_input.setCheckState(2)
        else:
            self.dest_usetls_input.setCheckState(0)
            
    def _set_dest_info(self, host, port, usetls):
        self._set_host(host)
        self._set_port(port)
        self._set_usetls(usetls)
            
    def _get_dest_info(self):
        host = self.dest_host_input.text()
        try:
            port = int(self.dest_port_input.text())
        except:
            port = -1
        if self.dest_usetls_input.checkState() == 0:
            usetls = False
        else:
            usetls = True
        return (host, port, usetls)

    def set_request(self, req):
        self._set_dest_info("", -1, False)
        if req:
            self.req = req
            self.req.tags = set(["repeater"])
            self._set_dest_info(req.dest_host, req.dest_port, req.use_tls)
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
        host, port, usetls = self._get_dest_info()
        if port is None:
            display_error_box("Invalid port")
            return
        req.dest_host = host
        req.dest_port = port
        req.dest_usetls = usetls
        self.client.submit(req, save=True)
        self.req = req
        self.set_request(req)
