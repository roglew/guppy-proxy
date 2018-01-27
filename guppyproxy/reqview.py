import threading
import re

from .util import printable_data
from .proxy import InterceptMacro, HTTPRequest, _parse_message
from .hexteditor import ComboEditor
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QLineEdit, QComboBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_for_mimetype, guess_lexer, TextLexer
from pygments.lexers.textfmts import HttpLexer
from pygments.util import ClassNotFound
from pygments.token import Token

class HybridHttpLexer(Lexer):
    tl = TextLexer()
    hl = HttpLexer()
    
    def get_tokens_unprocessed(self, text):
        try:
            t = text.encode()
            split = re.split(r"(?:\r\n|\n)(?:\r\n|\n)", text, 1)
            if len(split) == 2:
                h = split[0]
                body = split[1]
            else:
                h = split[0]
                body = ''
        except Exception as e:
            for v in self.tl.get_tokens_unprocessed(text):
                yield v
            raise e
            
        for token in self.hl.get_tokens_unprocessed(h):
            yield token

        if len(body) > 0:
            second_parser = None
            if "Content-Type" in h:
                try:
                    ct = re.search("Content-Type: (.*)", h)
                    if ct is not None:
                        hval = ct.groups()[0]
                        mime = hval.split(";")[0]
                        second_parser = get_lexer_for_mimetype(mime)
                except ClassNotFound:
                    pass
            if second_parser is None:
                yield (len(h), Token.Text, text[len(h):])
            else:
                for index, tokentype, value in second_parser.get_tokens_unprocessed(text[len(h):]):
                    yield (index+len(h), tokentype, value)
        

class ReqViewWidget(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.request = None
        self.layout = QGridLayout(self)
        self.layout.setSpacing(3)
        self.layout.setContentsMargins(0, 0, 0, 0)


        self.req_edit = ComboEditor()
        self.rsp_edit = ComboEditor()
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
        self.req_edit.set_bytes(b"")
        self.rsp_edit.set_bytes(b"")
        lex = HybridHttpLexer()
        if self.req is not None:
            self.req_edit.set_bytes_highlighted(self.req.full_message(), lexer=lex)
            if self.req.response is not None:
                self.rsp_edit.set_bytes_highlighted(self.req.response.full_message(), lexer=lex)
