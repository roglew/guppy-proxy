import html
import base64
import urllib
import json

from guppyproxy.util import display_error_box
from guppyproxy.hexteditor import ComboEditor
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QPlainTextEdit, QPushButton
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from datetime import datetime

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
    for i in range(0, 8):
        try:
            s_padded = base64.b64decode(s + '=' * i)
            return s_padded
        except Exception as e2:
            pass
    raise DecodeError("Unable to base64 decode string: %s" % s)


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
    return json.dumps(d, indent=2, sort_keys=True).encode()

def decode_jwt(s):
    # in case they paste the whole auth header or the token with "bearer"
    s = s.strip()
    fields = s.split(b' ')
    s = fields[-1].strip()
    parts = s.split(b'.')
    ret = b''
    for part in parts:
        try:
            ret += base64_decode_helper(part.decode()) + b'\n\n'
        except:
            ret += b"[error decoding]\n\n"
    return ret

def decode_unixtime(s):
    ts = int(s)
    dfmt = '%b %d, %Y %I:%M:%S %p'
    try:
        return datetime.utcfromtimestamp(ts).strftime(dfmt).encode()
    except ValueError:
        ts = ts/1000
        return datetime.utcfromtimestamp(ts).strftime(dfmt).encode()

class DecoderWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()

        self.decoder_input = DecoderInput()
        layout.addWidget(self.decoder_input)

        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)


class DecoderInput(QWidget):

    decodeRun = pyqtSignal(bytes)

    decoders = {
        "encode_b64": ("Encode Base64", base64.b64encode),
        "decode_b64": ("Decode Base64", base64_decode_helper),
        "encode_ah": ("Encode Asciihex", asciihex_encode_helper),
        "decode_ah": ("Decode Asciihex", asciihex_decode_helper),
        "encode_url": ("URL Encode", url_encode_helper),
        "decode_url": ("URL Decode", url_decode_helper),
        "encode_html": ("HTML Encode", html_encode_helper),
        "decode_html": ("HTML Decode", html_decode_helper),
        "decode_unixtime": ("Format Unix Timestamp", decode_unixtime),
        "pp_json": ("Pretty-Print JSON", pp_json),
        "decode_jwt": ("Decode JWT Token", decode_jwt),
    }

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        tool_layout = QHBoxLayout()

        self.editor = ComboEditor(pretty_tab=False, enable_pretty=False)
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
        text = self.editor.get_bytes()
        encode_type = self.encode_entry.itemData(self.encode_entry.currentIndex())
        encode_func = DecoderInput.decoders[encode_type][1]
        try:
            encoded = encode_func(text)
        except Exception as e:
            display_error_box("Error processing string:\n" + str(e))
            return
        self.editor.set_bytes(encoded)
