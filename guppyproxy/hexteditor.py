import base64
from .util import printable_data, qtprintable, textedit_highlight, DisableUpdates
from .proxy import _parse_message, Headers
from itertools import count
from PyQt5.QtWidgets import QWidget, QTextEdit, QTableWidget, QVBoxLayout, QTableWidgetItem, QTabWidget, QStackedLayout, QLabel, QComboBox
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QImage, QColor, QTextImageFormat, QTextDocument, QTextDocumentFragment, QTextBlockFormat
from PyQt5.QtCore import Qt, pyqtSlot, QUrl
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_mimetype, TextLexer
from pygments.lexers.data import JsonLexer
from pygments.lexers.html import HtmlLexer
from pygments.styles import get_style_by_name


class PrettyPrintWidget(QWidget):
    VIEW_NONE = 0
    VIEW_HIGHLIGHTED = 1
    VIEW_JSON = 2
    VIEW_HTMLXML = 3
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.headers = Headers()
        self.data = b''
        self.view = 0
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedLayout()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.nopp_widg = QLabel("No pretty version available")
        self.stack.addWidget(self.nopp_widg)
        self.highlighted_widg = QTextEdit()
        self.highlighted_widg.setReadOnly(True)
        self.stack.addWidget(self.highlighted_widg)
        self.json_widg = QTextEdit()
        self.json_widg.setReadOnly(True)
        self.stack.addWidget(self.json_widg)
        self.htmlxml_widg = QTextEdit()
        self.htmlxml_widg.setReadOnly(True)
        self.stack.addWidget(self.htmlxml_widg)

        self.selector = QComboBox()
        self.selector.addItem("Manually Select Printer", self.VIEW_NONE)
        self.selector.addItem("Highlighted", self.VIEW_HIGHLIGHTED)
        self.selector.addItem("JSON", self.VIEW_JSON)
        self.selector.addItem("HTML/XML", self.VIEW_HTMLXML)
        self.selector.currentIndexChanged.connect(self._combo_changed)
        
        self.layout().addWidget(self.selector)
        self.layout().addLayout(self.stack)
        
    def guess_format(self):
        if 'Content-Type' in self.headers:
            ct = self.headers.get('Content-Type').lower()
            if 'json' in ct:
                self.set_view(self.VIEW_JSON)
            elif 'html' in ct or 'xml' in ct:
                self.set_view(self.VIEW_HTMLXML)
            else:
                self.set_view(self.VIEW_HIGHLIGHTED)
        else:
            self.set_view(self.VIEW_NONE)
        
    @pyqtSlot()
    def _combo_changed(self):
        field = self.selector.itemData(self.selector.currentIndex())
        old = self.selector.blockSignals(True)
        self.set_view(field)
        self.selector.blockSignals(old)

    def set_view(self, view):
        if view == self.VIEW_NONE:
            self.clear_output()
            self.stack.setCurrentIndex(self.VIEW_NONE)
        elif view == self.VIEW_JSON:
            self.clear_output()
            self.fill_json()
            self.stack.setCurrentIndex(self.VIEW_JSON)
        elif view == self.VIEW_HTMLXML:
            self.clear_output()
            self.fill_htmlxml()
            self.stack.setCurrentIndex(self.VIEW_HTMLXML)
        elif view == self.VIEW_HIGHLIGHTED:
            self.clear_output()
            self.fill_highlighted()
            self.stack.setCurrentIndex(self.VIEW_HIGHLIGHTED)
        else:
            return
        self.selector.setCurrentIndex(view)
        self.view = view
        
    def clear_output(self):
        self.json_widg.setPlainText("")
        self.htmlxml_widg.setPlainText("")
        
    def set_bytes(self, bs):
        self.clear_output()
        self.headers = Headers()
        self.data = b''
        if not bs:
            return
        _, h, body = _parse_message(bs, lambda x: None)
        self.headers = h
        self.data = body
        
    def fill_json(self):
        from .decoder import pp_json
        with DisableUpdates(self.json_widg):
            self.json_widg.setPlainText("")
            if not self.data:
                return
            try:
                j = pp_json(self.data.decode())
            except Exception:
                return
            highlighted = textedit_highlight(j, JsonLexer())
            self.json_widg.setHtml(highlighted)
            
    def fill_htmlxml(self):
        from lxml import etree, html

        with DisableUpdates(self.htmlxml_widg):
            self.htmlxml_widg.setPlainText("")
            if not self.data:
                return
            try:
                fragments = html.fragments_fromstring(self.data.decode())
                parsed_frags = []
                for f in fragments:
                    parsed_frags.append(etree.tostring(f, pretty_print=True))
                pretty = b''.join(parsed_frags)
            except Exception:
                return
            highlighted = textedit_highlight(pretty, HtmlLexer())
            self.htmlxml_widg.setHtml(highlighted)
            
    def fill_highlighted(self):
        with DisableUpdates(self.htmlxml_widg):
            self.highlighted_widg.setPlainText("")
            if not self.data:
                return
            ct = self.headers.get('Content-Type').lower()
            if ";" in ct:
                ct = ct.split(";")[0]
            lexer = get_lexer_for_mimetype(ct)
            highlighted = textedit_highlight(self.data, lexer)
            self.highlighted_widg.setHtml(highlighted)


class HextEditor(QWidget):
    byte_image = QImage()
    byte_image.loadFromData(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAQklEQVQYlYWPMQoAMAgD82jpSzL613RpqG2FBly8QwywQlJ1UENSipAilIAS2FKFziFZ8LIVOjg6ocJx/+ELD/zVnJcqe5vHUAJgAAAAAElFTkSuQmCC"))
    byte_url = "data://byte.png"
    byte_property = 0x100000 + 1
    nonce_property = 0x100000 + 2
    byte_nonce = count()

    def __init__(self, enable_pretty=True):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.enable_pretty = enable_pretty
        self.setLayout(layout)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.lexer = TextLexer()

        self.textedit = QTextEdit()
        self.textedit.setAcceptRichText(False)
        doc = self.textedit.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        font.setPointSize(10)
        doc.setDefaultFont(font)
        doc.addResource(QTextDocument.ImageResource,
                        QUrl(self.byte_url),
                        HextEditor.byte_image)
        self.textedit.focusInEvent = self.focus_in_event
        self.textedit.focusOutEvent = self.focus_left_event
        self.data = b''

        self.pretty_mode = False
        self.layout().addWidget(self.textedit)

    def focus_in_event(self, e):
        QTextEdit.focusInEvent(self.textedit, e)
        if not self.textedit.isReadOnly():
            self.set_bytes(self.data)
            self.pretty_mode = False

    def focus_left_event(self, e):
        QTextEdit.focusOutEvent(self.textedit, e)
        if not self.textedit.isReadOnly():
            self.data = self.get_bytes()
            self.set_bytes_highlighted(self.data)
            self.pretty_mode = True

    def setReadOnly(self, ro):
        self.textedit.setReadOnly(ro)

    def _insert_byte(self, cursor, b):
        f = QTextImageFormat()
        f2 = QTextCursor().charFormat()
        cursor.document().addResource(QTextDocument.ImageResource,
                                    QUrl(self.byte_url),
                                    HextEditor.byte_image)
        f.setName(self.byte_url)
        f.setProperty(HextEditor.byte_property, b + 1)
        f.setProperty(HextEditor.nonce_property, next(self.byte_nonce))
        cursor.insertImage(f)
        cursor.setCharFormat(QTextCursor().charFormat())

    def clear(self):
        self.textedit.setPlainText("")

    def set_lexer(self, lexer):
        self.lexer = lexer

    def set_bytes(self, bs):
        self.pretty_mode = False
        self.data = bs
        chunks = HextEditor._split_by_printables(bs)
        self.clear()
        cursor = QTextCursor(self.textedit.document())
        cursor.beginEditBlock()

        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()

        for chunk in chunks:
            if chr(chunk[0]) in qtprintable:
                cursor.insertText(chunk.decode())
            else:
                for b in chunk:
                    self._insert_byte(cursor, b)
        cursor.endEditBlock()

    def set_bytes_highlighted(self, bs, lexer=None):
        if not self.enable_pretty:
            self.set_bytes(bs)
            return
        with DisableUpdates(self.textedit):
            self.textedit.setUndoRedoEnabled(False)
            oldro = self.textedit.isReadOnly()

            self.textedit.setReadOnly(True)
            self.pretty_mode = True
            self.clear()
            self.data = bs
            if lexer:
                self.lexer = lexer
            printable = printable_data(bs)
            highlighted = textedit_highlight(printable, self.lexer)
            self.textedit.setHtml(highlighted)

            self.textedit.setUndoRedoEnabled(True)
            self.textedit.setReadOnly(oldro)

    def get_bytes(self):
        if not self.pretty_mode:
            self.data = self._get_bytes()
        return self.data

    def _get_bytes(self):
        from .util import hexdump
        bs = bytearray()
        block = self.textedit.document().firstBlock()
        newline = False
        while block.length() > 0:
            if newline:
                bs.append(ord('\n'))
            newline = True
            it = block.begin()
            while not it.atEnd():
                f = it.fragment()
                fmt = f.charFormat()
                byte = fmt.intProperty(HextEditor.byte_property)
                if byte > 0:
                    text = f.text().encode()
                    if text == b"\xef\xbf\xbc":
                        bs.append(byte - 1)
                    else:
                        bs += text
                else:
                    text = f.text()
                    bs += text.encode()
                it += 1
            block = block.next()
        return bytes(bs)

    @classmethod
    def _split_by_printables(cls, bs):
        if len(bs) == 0:
            return []

        def is_printable(c):
            return c in qtprintable

        chunks = []
        printable = is_printable(chr(bs[0]))
        a = 0
        b = 1
        while b < len(bs):
            if is_printable(chr(bs[b])) != printable:
                chunks.append(bs[a:b])
                a = b
                printable = not printable
            b += 1
        chunks.append(bs[a:b])
        return chunks


class HexEditor(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.data = bytearray()
        self.datatable = QTableWidget()
        self.datatable.cellChanged.connect(self._cell_changed)
        self.datatable.horizontalHeader().setStretchLastSection(True)
        self.row_size = 16
        self.read_only = False
        self.redraw_table()
        self.layout().addWidget(self.datatable)

    def set_bytes(self, bs):
        self.data = bytearray(bs)
        self.redraw_table()

    def get_bytes(self):
        return bytes(self.data)

    def setReadOnly(self, ro):
        self.read_only = ro
        self.redraw_table()

    def _redraw_strcol(self, row):
        start = self.row_size * row
        end = start + self.row_size
        data = self.data[start:end]
        print_data = printable_data(data, include_newline=False)
        item = QTableWidgetItem(print_data)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.datatable.setItem(row, self.str_col, item)

    def redraw_table(self, length=None):
        with DisableUpdates(self.datatable):
            oldsig = self.datatable.blockSignals(True)
            self.row_size = length or self.row_size
            self.datatable.setColumnCount(self.row_size + 1)
            self.datatable.setRowCount(0)
            self.str_col = self.row_size

            self.datatable.horizontalHeader().hide()
            self.datatable.verticalHeader().hide()

            rows = int(len(self.data) / self.row_size)
            if len(self.data) % self.row_size > 0:
                rows += 1
            self.datatable.setRowCount(rows)

            for i in range(rows * self.row_size):
                row = i / self.row_size
                col = i % self.row_size
                if i < len(self.data):
                    dataval = "%02x" % self.data[i]
                    item = QTableWidgetItem(dataval)
                    if self.read_only:
                        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                else:
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.datatable.setItem(row, col, item)

            for row in range(rows):
                self._redraw_strcol(row)
            self.datatable.blockSignals(oldsig)
            self.datatable.resizeColumnsToContents()
            self.datatable.resizeRowsToContents()

    @classmethod
    def _format_hex(cls, n):
        return ("%02x" % n).upper()

    @pyqtSlot(int, int)
    def _cell_changed(self, row, col):
        oldsig = self.datatable.blockSignals(True)
        if col == self.str_col:
            return
        if len(self.data) == 0:
            return

        data_ind = self.row_size * row + col
        if data_ind >= len(self.data):
            return

        data_text = self.datatable.item(row, col).text()
        try:
            data_val = int(data_text, 16)
            if data_val < 0x0 or data_val > 0xff:
                raise Exception()
        except Exception as e:
            item = QTableWidgetItem(self._format_hex(self.data[data_ind]))
            self.datatable.setItem(row, col, item)
            self.datatable.blockSignals(oldsig)
            return

        if data_text != self._format_hex(data_val):
            self.datatable.setItem(row, col, QTableWidgetItem(self._format_hex(data_val)))

        self.data[data_ind] = data_val
        self._redraw_strcol(row)
        self.datatable.blockSignals(oldsig)


class ComboEditor(QWidget):
    def __init__(self, pretty_tab=True, enable_pretty=True):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.data = b''
        self.enable_pretty = enable_pretty

        self.tabWidget = QTabWidget()
        self.hexteditor = HextEditor(enable_pretty=self.enable_pretty)
        self.hexeditor = HexEditor()
        self.ppwidg = PrettyPrintWidget()

        self.hexteditor_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.hexteditor, "Text")
        self.hexeditor_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.hexeditor, "Hex")
        self.pp_ind = -1
        if pretty_tab:
            self.pp_ind = self.tabWidget.count()
            self.tabWidget.addTab(self.ppwidg, "Pretty")
        self.tabWidget.currentChanged.connect(self._tab_changed)

        self.previous_tab = self.tabWidget.currentIndex()

        self.layout().addWidget(self.tabWidget)


    @pyqtSlot(int)
    def _tab_changed(self, i):
        # commit data from old tab
        if self.previous_tab == self.hexteditor_ind:
            self.data = self.hexteditor.get_bytes()
        if self.previous_tab == self.hexeditor_ind:
            self.data = self.hexeditor.get_bytes()

        # set up new tab
        if i == self.hexteditor_ind:
            if self.hexteditor.pretty_mode:
                self.hexteditor.set_bytes_highlighted(self.data)
            else:
                self.hexteditor.set_bytes(self.data)
        if i == self.hexeditor_ind:
            self.hexeditor.set_bytes(self.data)
        if i == self.pp_ind:
            self.ppwidg.set_bytes(self.data)
            self.ppwidg.guess_format()

        # update previous tab
        self.previous_tab = self.tabWidget.currentIndex()
        

    @pyqtSlot(bytes)
    def set_bytes(self, bs):
        self.data = bs
        self.tabWidget.setCurrentIndex(0)
        if self.tabWidget.currentIndex() == self.hexteditor_ind:
            self.hexteditor.set_bytes(bs)
        elif self.tabWidget.currentIndex() == self.hexeditor_ind:
            self.hexeditor.set_bytes(bs)
        elif self.tabWidget.currentIndex() == self.pp_ind:
            self.ppwidg.set_bytes(bs)


    @pyqtSlot(bytes)
    def set_bytes_highlighted(self, bs, lexer=None):
        self.data = bs
        self.tabWidget.setCurrentIndex(0)
        if self.enable_pretty:
            self.hexteditor.set_bytes_highlighted(bs, lexer=lexer)
        else:
            self.set_bytes(bs)

    def get_bytes(self):
        if self.tabWidget.currentIndex() == self.hexteditor_ind:
            self.data = self.hexteditor.get_bytes()
        elif self.tabWidget.currentIndex() == self.hexeditor_ind:
            self.data = self.hexeditor.get_bytes()
        return self.data

    def setReadOnly(self, ro):
        self.hexteditor.setReadOnly(ro)
        self.hexeditor.setReadOnly(ro)
