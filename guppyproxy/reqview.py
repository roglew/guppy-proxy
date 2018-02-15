import re

from .util import datetime_string
from .proxy import HTTPRequest, get_full_url, parse_request
from .hexteditor import ComboEditor
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QHeaderView, QAbstractItemView, QLineEdit, QTabWidget, QVBoxLayout, QToolButton, QHBoxLayout
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_for_mimetype, TextLexer
from pygments.lexers.textfmts import HttpLexer
from pygments.util import ClassNotFound
from pygments.token import Token


class HybridHttpLexer(Lexer):
    tl = TextLexer()
    hl = HttpLexer()

    def get_tokens_unprocessed(self, text):
        try:
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
                    yield (index + len(h), tokentype, value)


class InfoWidget(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.request = None
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.infotable = QTableWidget()
        self.infotable.setColumnCount(2)

        self.infotable.verticalHeader().hide()
        self.infotable.horizontalHeader().hide()
        self.infotable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.infotable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.infotable.horizontalHeader().setStretchLastSection(True)

        self.layout().addWidget(self.infotable)

    def _add_info(self, k, v):
        row = self.infotable.rowCount()
        self.infotable.insertRow(row)
        item1 = QTableWidgetItem(k)
        item1.setFlags(item1.flags() ^ Qt.ItemIsEditable)
        self.infotable.setItem(row, 0, item1)
        self.infotable.setItem(row, 1, QTableWidgetItem(v))

    def set_request(self, req):
        self.infotable.setUpdatesEnabled(False)
        try:
            self.request = req
            self.infotable.setRowCount(0)
            if self.request is None:
                return
            reqlen = len(self.request.body)
            reqlen = '%d bytes' % reqlen
            rsplen = 'No response'

            mangle_str = 'Nothing mangled'
            if self.request.unmangled:
                mangle_str = 'Request'

            if self.request.response:
                response_code = str(self.request.response.status_code) + \
                    ' ' + self.request.response.reason
                rsplen = self.request.response.content_length
                rsplen = '%d bytes' % rsplen

                if self.request.response.unmangled:
                    if mangle_str == 'Nothing mangled':
                        mangle_str = 'Response'
                    else:
                        mangle_str += ' and Response'
            else:
                response_code = ''

            time_str = '--'
            if self.request.time_end is not None and self.request.time_start is not None:
                time_delt = self.request.time_end - self.request.time_start
                time_str = "%.2f sec" % time_delt.total_seconds()

            if self.request.use_tls:
                is_ssl = 'YES'
            else:
                is_ssl = 'NO'

            if self.request.time_start:
                time_made_str = datetime_string(self.request.time_start)
            else:
                time_made_str = '--'

            verb = self.request.method
            host = self.request.dest_host

            self._add_info('Made on', time_made_str)
            self._add_info('URL', get_full_url(self.request))
            self._add_info('Host', host)
            self._add_info('Path', self.request.url.path)
            self._add_info('Verb', verb)
            self._add_info('Status Code', response_code)
            self._add_info('Request Length', reqlen)
            self._add_info('Response Length', rsplen)
            if self.request.response and self.request.response.unmangled:
                self._add_info('Unmangled Response Length', self.request.response.unmangled.content_length)
            self._add_info('Time', time_str)
            self._add_info('Port', str(self.request.dest_port))
            self._add_info('SSL', is_ssl)
            self._add_info('Mangled', mangle_str)
            self._add_info('Tags', ', '.join(self.request.tags))
        finally:
            self.infotable.setUpdatesEnabled(True)


class TagList(QTableWidget):
    tagsUpdated = pyqtSignal(set)

    # list part of the tag tab
    def __init__(self, *args, **kwargs):
        QTableWidget.__init__(self, *args, **kwargs)
        self.tags = set()

        # Set up table
        self.setColumnCount(1)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def add_tag(self, tag):
        self.tags.add(tag)
        self.redraw_table()
        self.tagsUpdated.emit(set(self.tags))

    def set_tags(self, tags):
        self.tags = set(tags)
        self.redraw_table()
        self.tagsUpdated.emit(set(self.tags))

    def clear_tags(self):
        self.tags = set()
        self.redraw_table()
        self.tagsUpdated.emit(set(self.tags))

    def _append_str_row(self, fstr):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(fstr))

    def redraw_table(self):
        self.setRowCount(0)
        for tag in sorted(self.tags):
            self._append_str_row(tag)

    @pyqtSlot()
    def delete_selected(self):
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        for idx in rows:
            tag = self.item(idx.row(), 0).text()
            self.tags.remove(tag)
        self.redraw_table()
        self.tagsUpdated.emit(set(self.tags))

    def get_tags(self):
        return set(self.tags)


class TagWidget(QWidget):
    tagsUpdated = pyqtSignal(set)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.taglist = TagList()
        self.taglist.tagsUpdated.connect(self.tagsUpdated)
        self.layout().addWidget(self.taglist)

        self.taginput = QLineEdit()
        self.taginput.returnPressed.connect(self.add_tag)
        self.addbutton = QToolButton()
        self.addbutton.setText("+")
        self.removebutton = QToolButton()
        self.removebutton.setText("-")
        editbar = QHBoxLayout()
        editbar.addWidget(self.addbutton)
        editbar.addWidget(self.removebutton)
        editbar.addWidget(self.taginput)

        self.removebutton.clicked.connect(self.taglist.delete_selected)
        self.addbutton.clicked.connect(self.add_tag)

        self.layout().addLayout(editbar)

    @pyqtSlot()
    def add_tag(self):
        if self.readonly:
            return
        tag = self.taginput.text()
        if tag == "":
            return
        self.taglist.add_tag(tag)
        self.taginput.setText("")

    def set_read_only(self, readonly):
        self.readonly = readonly
        self.addbutton.setEnabled(not readonly)
        self.removebutton.setEnabled(not readonly)


class ReqViewWidget(QWidget):
    requestEdited = pyqtSignal(HTTPRequest)

    def __init__(self, info_tab=False, tag_tab=False, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.request = None
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        view_layout = QGridLayout()
        view_layout.setSpacing(3)
        view_layout.setContentsMargins(0, 0, 0, 0)

        self.req_edit = ComboEditor()
        self.rsp_edit = ComboEditor()
        self.req_edit.setReadOnly(True)
        self.rsp_edit.setReadOnly(True)

        view_layout.addWidget(self.req_edit, 0, 0)
        view_layout.addWidget(self.rsp_edit, 0, 1)
        view_widg = QWidget()
        view_widg.setLayout(view_layout)

        use_tab = False
        if info_tab or tag_tab:  # or <other tab> or <other other tab>
            use_tab = True
            tab_widget = QTabWidget()
            tab_widget.addTab(view_widg, "Messages")

        self.info_tab = False
        self.info_widg = None
        if info_tab:
            self.info_tab = True
            self.info_widg = InfoWidget()
            tab_widget.addTab(self.info_widg, "Info")

        self.tag_tab = False
        self.tag_widg = None
        if tag_tab:
            self.tag_tab = True
            self.tag_widg = TagWidget()
            tab_widget.addTab(self.tag_widg, "Tags")

        if use_tab:
            self.layout().addWidget(tab_widget)
        else:
            self.layout().addWidget(view_widg)

    def set_read_only(self, ro):
        self.req_edit.setReadOnly(ro)

    def set_tags_read_only(self, ro):
        if self.tag_tab:
            self.tag_widg.set_read_only(ro)

    def get_request(self):
        try:
            req = parse_request(self.req_edit.get_bytes())
            req.dest_host = self.dest_host
            req.dest_port = self.dest_port
            req.use_tls = self.use_tls
            if self.tag_widg:
                req.tags = self.tag_widg.taglist.get_tags()
            return req
        except Exception as e:
            raise e
            return None

    @pyqtSlot(HTTPRequest)
    def set_request(self, req):
        self.req = req
        self.dest_host = ""
        self.dest_port = -1
        self.use_tls = False
        if req:
            self.dest_host = req.dest_host
            self.dest_port = req.dest_port
            self.use_tls = req.use_tls
        self.update_editors()
        if self.info_tab:
            self.info_widg.set_request(req)
        if self.tag_tab:
            if req:
                self.tag_widg.taglist.set_tags(req.tags)

    def update_editors(self):
        self.req_edit.set_bytes(b"")
        self.rsp_edit.set_bytes(b"")
        lex = HybridHttpLexer()
        if self.req is not None:
            self.req_edit.set_bytes_highlighted(self.req.full_message(), lexer=lex)
            if self.req.response is not None:
                self.rsp_edit.set_bytes_highlighted(self.req.response.full_message(), lexer=lex)
