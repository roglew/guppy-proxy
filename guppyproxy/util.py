import os
import string
import time
import datetime
import random
from .proxy import get_full_url, Headers
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name
from PyQt5.QtWidgets import QMessageBox, QMenu, QApplication, QFileDialog
from PyQt5.QtGui import QColor


str_colorcache = {}


class DisableUpdates:
    def __init__(self, *args):
        self.prevs = [(obj, obj.updatesEnabled()) for obj in args]
        self.undoredo = []
        self.readonly = []
        for obj, _ in self.prevs:
            obj.setUpdatesEnabled(False)
            if hasattr(obj, 'setReadOnly'):
                self.undoredo.append((obj, obj.isUndoRedoEnabled()))
                obj.setUndoRedoEnabled(False)
            if hasattr(obj, 'setUndoRedoEnabled'):
                self.readonly.append((obj, obj.isReadOnly()))
                obj.setReadOnly(True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for obj, prev in self.prevs:
            obj.setUpdatesEnabled(prev)
        for obj, prev in self.undoredo:
            obj.setUndoRedoEnabled(prev)
        for obj, prev in self.readonly:
            obj.setReadOnly(prev)


def str_hash_code(s):
    h = 0
    n = len(s) - 1
    for c in s.encode():
        h += c * 31 ** n
        n -= 1
    return h


qtprintable = [c for c in string.printable if c != '\r']


def dbgline():
    from inspect import currentframe, getframeinfo
    cf = currentframe()
    print(getframeinfo(cf.f_back).filename, cf.f_back.f_lineno)


def is_printable(s):
    for c in s:
        if c not in qtprintable:
            return False
    return True


def printable_data(data, include_newline=True):
    chars = []
    printable = string.printable
    if not include_newline:
        printable = [c for c in printable if c != '\n']
    for c in data:
        if chr(c) in printable:
            chars.append(chr(c))
        else:
            chars.append('.')
    return ''.join(chars)


def max_len_str(s, ln):
    if ln <= 3:
        return "..."
    if len(s) <= ln:
        return s
    return s[:(ln - 3)] + "..."


def display_error_box(msg, title="Error"):
    msgbox = QMessageBox()
    msgbox.setIcon(QMessageBox.Warning)
    msgbox.setText(msg)
    msgbox.setWindowTitle(title)
    msgbox.setStandardButtons(QMessageBox.Ok)
    return msgbox.exec_()


def display_info_box(msg, title="Message"):
    msgbox = QMessageBox()
    msgbox.setIcon(QMessageBox.Information)
    msgbox.setText(msg)
    msgbox.setWindowTitle(title)
    msgbox.setStandardButtons(QMessageBox.Ok)
    return msgbox.exec_()


def copy_to_clipboard(s):
    QApplication.clipboard().setText(s)
    

def paste_clipboard():
    return QApplication.clipboard().text()


def save_dialog(parent, default_dir=None, default_name=None):
    default_dir = default_dir or os.getcwd()
    default_name = default_name or ""
    dialog = QFileDialog(parent)
    dialog.setFileMode(QFileDialog.AnyFile)
    dialog.setViewMode(QFileDialog.Detail)
    dialog.setAcceptMode(QFileDialog.AcceptSave)
    dialog.setDirectory(os.getcwd())
    dialog.selectFile(default_name)
    if not (dialog.exec_()):
        return None
    saveloc = dialog.selectedFiles()[0]
    return saveloc


def display_req_context(parent, client, req, event, repeater_widget=None, req_view_widget=None, macro_widget=None, save_option=False):
    menu = QMenu(parent)
    repeaterAction = None
    displayUnmangledReq = None
    displayUnmangledRsp = None
    viewInBrowser = None
    macroAction = None
    saveToHistAction = None

    if save_option:
        saveToHistAction = menu.addAction("Save request to history")

    if repeater_widget is not None:
        repeaterAction = menu.addAction("Send to repeater")

    if req.unmangled and req_view_widget:
        displayUnmangledReq = menu.addAction("View unmangled request")
    if req.response and req.response.unmangled and req_view_widget:
        displayUnmangledRsp = menu.addAction("View unmangled response")

    if req.db_id != "":
        viewInBrowser = menu.addAction("View response in browser")

    curlAction = menu.addAction("Copy as cURL command")
    saveAction = menu.addAction("Save response to file")
    saveFullActionReq = menu.addAction("Save request to file (full message)")
    saveFullActionRsp = menu.addAction("Save response to file (full message)")

    if macro_widget is not None:
        macroAction = menu.addAction("Add to active macro input")

    action = menu.exec_(parent.mapToGlobal(event.pos()))
    if save_option and action == saveToHistAction:
        client.save_new(req)
    if repeaterAction and action == repeaterAction:
        repeater_widget.set_request(req)
    if displayUnmangledReq and action == displayUnmangledReq:
        req_view_widget.set_request(req.unmangled)
    if displayUnmangledRsp and action == displayUnmangledRsp:
        new_req = req.copy()
        new_req.response = req.response.unmangled
        req_view_widget.set_request(new_req)
    if viewInBrowser and action == viewInBrowser:
        url = "http://puppy/rsp/%s" % req.db_id
        copy_to_clipboard(url)
        display_info_box("URL copied to clipboard.\n\nPaste the URL into the browser being proxied")
    if action == curlAction:
        curl = curl_command(req)
        if curl is None:
            display_error_box("Request could not be converted to cURL command")
        try:
            copy_to_clipboard(curl)
        except Exception:
            display_error_box("Error copying command to clipboard")
    if action == saveAction:
        if not req.response:
            display_error_box("No response associated with request")
            return
        fname = req.url.path.rsplit('/', 1)[-1]
        saveloc = save_dialog(parent, default_name=fname)
        if not saveloc:
            return
        with open(saveloc, 'wb') as f:
            f.write(req.response.body)
    if action == saveFullActionRsp:
        if not req.response:
            display_error_box("No response associated with request")
            return
        fname = req.url.path.rsplit('/', 1)[-1] + ".response"
        saveloc = save_dialog(parent, default_name=fname)
        if not saveloc:
            return
        with open(saveloc, 'wb') as f:
            f.write(req.response.full_message())
    if action == saveFullActionReq:
        fname = req.url.path.rsplit('/', 1)[-1] + ".request"
        saveloc = save_dialog(parent, default_name=fname)
        if not saveloc:
            return
        with open(saveloc, 'wb') as f:
            f.write(req.full_message())
    if macroAction and action == macroAction:
        macro_widget.add_requests([req])


def method_color(method):
    if method.lower() == 'get':
        return QColor(240, 240, 255)

    if method.lower() == 'post':
        return QColor(255, 255, 230)

    if method.lower() == 'put':
        return QColor(255, 240, 240)

    return QColor(255, 255, 255)

def sc_color(sc):
    if sc[0] == '2':
        return QColor(240, 255, 240)

    if sc[0] == '3':
        return QColor(255, 240, 255)

    if sc[0] == '4':
        return QColor(255, 240, 240)

    if sc[0] == '5':
        return QColor(255, 255, 230)

    return QColor(255, 255, 255)

def host_color(hostport):
    return str_color(hostport, lighten=150, seed=1)

def str_color(s, lighten=0, seed=0):
    global str_colorcache
    if s in str_colorcache:
        return str_colorcache[s]
    hashval = str_hash_code(s)+seed
    gen = random.Random()
    gen.seed(hashval)
    r = gen.randint(lighten, 255)
    g = gen.randint(lighten, 255)
    b = gen.randint(lighten, 255)

    col = QColor(r, g, b)
    str_colorcache[s] = col
    return col

def hostport(req):
    # returns host:port if to a port besides 80 or 443
    host = req.dest_host
    if req.use_tls and req.dest_port == 443:
        return host
    if (not req.use_tls) and req.dest_port == 80:
        return host
    return "%s:%d" % (host, req.dest_port)


def _sh_esc(s):
    sesc = s.replace("\\", "\\\\")
    sesc = sesc.replace("\"", "\\\"")
    return sesc


def curl_command(req):
    # Creates a curl command that submits a given request
    command = "curl"
    if req.method != "GET":
        command += " -X %s" % req.method
    for k, v in req.headers.pairs():
        if k.lower == "content-length":
            continue
        kesc = _sh_esc(k)
        vesc = _sh_esc(v)
        command += ' --header "%s: %s"' % (kesc, vesc)
        if req.body:
            if not is_printable(req.body):
                return None
            besc = _sh_esc(req.body)
            command += ' -d "%s"' % besc
    command += ' "%s"' % _sh_esc(get_full_url(req))
    return command


def list_remove(lst, inds):
    return [i for j, i in enumerate(lst) if j not in inds]


def hexdump(src, length=16):
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
    lines = []
    for c in range(0, len(src), length):
        chars = src[c:c + length]
        hex = ' '.join(["%02x" % x for x in chars])
        printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or '.') for x in chars])
        lines.append("%04x  %-*s  %s\n" % (c, length * 3, hex, printable))
    return ''.join(lines)


def confirm(message, default='n'):
    """
    A helper function to get confirmation from the user. It prints ``message``
    then asks the user to answer yes or no. Returns True if the user answers
    yes, otherwise returns False.
    """
    if 'n' in default.lower():
        default = False
    else:
        default = True

    print(message)
    if default:
        answer = input('(Y/n) ')
    else:
        answer = input('(y/N) ')

    if not answer:
        return default

    if answer[0].lower() == 'y':
        return True
    else:
        return False


# Taken from http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime
def utc2local(utc):
    epoch = time.mktime(utc.timetuple())
    offset = datetime.datetime.fromtimestamp(epoch) - datetime.datetime.utcfromtimestamp(epoch)
    return utc + offset


def datetime_string(dt):
    dtobj = utc2local(dt)
    time_made_str = dtobj.strftime('%a, %b %d, %Y, %I:%M:%S.%f %p')
    return time_made_str


def query_to_str(query):
    retstr = ""
    for p in query:
        fstrs = []
        for f in p:
            fstrs.append(' '.join(f))

        retstr += (' OR '.join(fstrs))
    return retstr


def textedit_highlight(text, lexer):
    from pygments import highlight
    wrapper_head = """<div class="highlight" style="
        font-size: 10pt;
        font-family: monospace;
        "><pre style="line-height: 100%">"""
    wrapper_foot = "</pre></div>"
    highlighted = highlight(text, lexer,
                            HtmlFormatter(noclasses=True, style=get_style_by_name("colorful"), nowrap=True))
    highlighted = wrapper_head + highlighted + wrapper_foot
    return highlighted
