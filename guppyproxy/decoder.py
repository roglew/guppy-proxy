import html
import base64
import urllib
import json

from .util import display_error_box
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QPlainTextEdit, QPushButton
from PyQt5.QtCore import pyqtSlot, pyqtSignal

class DecodeError(Exception):
    pass

def asciihex_encode_helper(s):
    return ''.join('{0:x}'.format(c) for c in s).encode()


def asciihex_decode_helper(s):
    ret = []
    try:
        for a, b in zip(s[0::2], s[1::2]):
            c = chr(a) + chr(b)
            ret.append(chr(int(c, 16)))
        return ''.join(ret).encode()
    except Exception as e:
        raise DecodeError("Unable to decode asciihex")


def base64_decode_helper(s):
    try:
        return base64.b64decode(s)
    except TypeError:
        for i in range(1, 5):
            try:
                s_padded = base64.b64decode(s + '=' * i)
                return s_padded
            except Exception:
                pass
        raise DecodeError("Unable to base64 decode string")


def url_decode_helper(s):
    bs = s.decode()
    return urllib.parse.unquote(bs).encode()


def url_encode_helper(s):
    bs = s.decode()
    return urllib.parse.quote_plus(bs).encode()


def html_encode_helper(s):
    return ''.join(['&#x{0:x};'.format(c) for c in s]).encode()


def html_decode_helper(s):
    return html.unescape(s.decode()).encode()


def pp_json(s):
    d = json.loads(s.strip())
    return json.dumps(d, indent=4, sort_keys=True).encode()


class DecoderWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()

        layout.addWidget(DecoderInput())

        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)


class DecoderInput(QWidget):

    decodeRun = pyqtSignal(bytes)

    decoders = {
        "encode_b64": ("Encode Base64", base64.b64encode),
        "decode_b64": ("Decode Base64", base64.b64encode),
        "encode_ah": ("Encode Asciihex", asciihex_encode_helper),
        "decode_ah": ("Decode Asciihex", asciihex_decode_helper),
        "encode_url": ("URL Encode", url_encode_helper),
        "decode_url": ("URL Decode", url_decode_helper),
        "encode_html": ("HTML Encode", html_encode_helper),
        "decode_html": ("HTML Decode", html_decode_helper),
        "pp_json": ("Pretty-Print JSON", pp_json),
    }

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        tool_layout = QHBoxLayout()

        self.editor = QPlainTextEdit()
        self.encode_entry = QComboBox()
        encode_button = QPushButton("Go!")

        encode_button.clicked.connect(self.encode)

        for k, v in self.decoders.items():
            self.encode_entry.addItem(v[0], k)

        layout.addWidget(self.editor)
        tool_layout.addWidget(self.encode_entry)
        tool_layout.addWidget(encode_button)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)

    @pyqtSlot()
    def encode(self):
        text = self.editor.toPlainText().encode()
        encode_type = self.encode_entry.itemData(self.encode_entry.currentIndex())
        encode_func = DecoderInput.decoders[encode_type][1]
        try:
            encoded = encode_func(text)
        except Exception as e:
            display_error_box("Error processing string:\n" + str(e))
            return
        self.editor.setPlainText(encoded.decode())
