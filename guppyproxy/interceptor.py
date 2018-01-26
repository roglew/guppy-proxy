from .util import printable_data, display_error_box
from .proxy import InterceptMacro, HTTPRequest, parse_request, parse_response
from .reqview import ReqViewWidget
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QTabWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject

import threading

edit_queue = []

class InterceptEvent:
    
    def __init__(self):
        self.e = threading.Event()
        self.canceled = False
        self.message = None
        
    def wait(self):
        self.e.wait()
        return self.message
        
    def set(self, message):
        self.message = message
        self.e.set()
        
    def cancel(self):
        self.canceled = True
        self.set(None)

class InterceptedMessage:

    def __init__(self, request=None, response=None, wsmessage=None):
        self.request = request
        self.response = response
        self.wsmessage = wsmessage
        self.event = InterceptEvent()
        
        self.message_type = None
        if self.request:
            self.message_type = "request"
        elif self.response:
            self.message_type = "response"
        elif self.wsmessage:
            self.message_type = "wsmessage"
            
class InterceptorMacro(InterceptMacro, QObject):
    """
    A class representing a macro that modifies requests as they pass through the
    proxy
    """
    
    messageReceived = pyqtSignal(InterceptedMessage)
    
    def __init__(self, int_widget):
        InterceptMacro.__init__(self)
        QObject.__init__(self)
        self.int_widget = int_widget
        self.messageReceived.connect(self.int_widget.message_received)
        self.name = "InterceptorMacro"

    def mangle_request(self, request):
        int_msg = InterceptedMessage(request=request)
        self.messageReceived.emit(int_msg)
        req = int_msg.event.wait()
        if int_msg.event.canceled:
            return request
        req.dest_host = request.dest_host
        req.dest_port = request.dest_port
        req.use_tls = request.use_tls
        return req

    def mangle_response(self, request, response):
        int_msg = InterceptedMessage(response=response)
        self.messageReceived.emit(int_msg)
        rsp = int_msg.event.wait()
        if int_msg.event.canceled:
            return response
        return rsp

    def mangle_websocket(self, request, response, message):
        # just don't do this right now
        pass

class InterceptorWidget(QWidget):
    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        self.int_conn = None
        self.queued_messages = []
        self.editing_message = None
        self.editing = False
        
        self.int_req = False
        self.int_rsp = False
        self.int_ws = False
        
        # layouts
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(10)

        # widgets
        intReqButton = QPushButton("Int. Requests")
        intRspButton = QPushButton("Int. Responses")
        intWsButton = QPushButton("Int. Websocket")
        forwardButton = QPushButton("Forward")
        cancelButton = QPushButton("Cancel")
        self.editor = QPlainTextEdit()
        
        intReqButton.setCheckable(True)
        intRspButton.setCheckable(True)
        intWsButton.setCheckable(True)
        
        intWsButton.setEnabled(False)
        
        forwardButton.clicked.connect(self.forward_message)
        cancelButton.clicked.connect(self.cancel_edit)
        intReqButton.toggled.connect(self.int_req_toggled)
        intRspButton.toggled.connect(self.int_rsp_toggled)
        intWsButton.toggled.connect(self.int_ws_toggled)

        #submitButton.clicked.connect(self.submit)

        buttons.addWidget(forwardButton)
        buttons.addWidget(cancelButton)
        buttons.addWidget(intReqButton)
        buttons.addWidget(intRspButton)
        buttons.addWidget(intWsButton)
        # checkbox for req/rsp/ws
        self.layout().addLayout(buttons)
        self.layout().addWidget(self.editor)
        
    @pyqtSlot(bool)
    def int_req_toggled(self, state):
        self.int_req = state
        self.restart_intercept()

    @pyqtSlot(bool)
    def int_rsp_toggled(self, state):
        self.int_rsp = state
        self.restart_intercept()

    @pyqtSlot(bool)
    def int_ws_toggled(self, state):
        self.int_ws = state
        self.restart_intercept()
        
    @pyqtSlot(InterceptedMessage)
    def message_received(self, msg):
        self.queued_messages.append(msg)
        # Update queue list
        self.edit_next_message()
        
    def set_edited_message(self, msg):
        if msg.message_type == "request":
            self.editor.setPlainText(msg.request.full_message().decode())
        elif msg.message_type == "response":
            self.editor.setPlainText(msg.response.full_message().decode())
        elif msg.message_type == "wsmessage":
            # this is not gonna work
            self.editor.setPlainText(msg.wsmessage.message.decode())
    
    def edit_next_message(self):
        self.editor.setPlainText("")
        if self.editing:
            return
        if not self.queued_messages:
            return
        self.editing_message = self.queued_messages.pop()
        self.set_edited_message(self.editing_message)
        self.editing = True
        
    @pyqtSlot()
    def forward_message(self):
        if not self.editing:
            return
        if self.editing_message.message_type == "request":
            try:
                req = parse_request(self.editor.toPlainText().encode())
            except:
                display_error_box("Could not parse request")
                return
            self.editing_message.event.set(req)
        elif self.editing_message.message_type == "response":
            try:
                rsp = parse_response(self.editor.toPlainText().encode())
            except:
                display_error_box("Could not parse response")
                return
            self.editing_message.event.set(rsp)
        elif self.editing_message.message_type == "wsmessage":
            pass
        self.editing = False
        self.edit_next_message()
        
    @pyqtSlot()
    def cancel_edit(self):
        if self.editing_message:
            self.editing_message.event.cancel()
        self.editing = False
        self.edit_next_message()
        
    def clear_edit_queue(self):
        while self.queued_messages or self.editing_message:
            if self.editing_message:
                self.editing_message.event.cancel()
                self.editing_message = False
            if self.queued_messages:
                self.editing_message = self.queued_messages.pop()
            
        
    def restart_intercept(self):
        self.close()
        self.editor.setPlainText("")
        self.editing=False

        if not (self.int_req or self.int_rsp or self.int_ws):
            return

        mangle_macro = InterceptorMacro(self)
        mangle_macro.intercept_requests = self.int_req
        mangle_macro.intercept_responses = self.int_rsp
        mangle_macro.intercept_ws = self.int_ws
        self.int_conn = self.client.new_conn()
        self.int_conn.intercept(mangle_macro)
        
    def close(self):
        if self.int_conn:
            self.int_conn.close()
            self.int_conn = None
        self.clear_edit_queue()

