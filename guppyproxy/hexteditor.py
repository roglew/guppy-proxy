import base64
import sys
import string
from .util import printable_data, hexdump, qtprintable
from PyQt5.QtWidgets import QWidget, QTextEdit, QTableWidget, QHeaderView, QVBoxLayout, QTableWidgetItem, QTabWidget
from PyQt5.QtGui import QFont, QTextCursor, QTextDocumentFragment, QTextCharFormat, QImage, QTextDocument, QTextImageFormat, QColor
from PyQt5.QtCore import QUrl, QVariant, Qt, pyqtSlot, pyqtSignal
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer
from pygments.styles import get_style_by_name

class HextEditor(QWidget):
    byte_image = QImage()
    byte_image.loadFromData(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAW0lEQVQ4jb2TyQkAMAgE7cd+7Me2bM68cpIYjRBhnzOsggB9NJhplJmnEJGZUeKGTpItLCItYcEKnSRmg5DgtmtK4LrBC/xHYAURcw1cgnQDCx4FLkmFdnDqnQvXe8GAGsorMwAAAABJRU5ErkJggg=="))
    byte_url = "data://byte.png"
    byte_property = 0x100000 + 1
    
    def __init__(self):
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.lexer = TextLexer()

        self.textedit = QTextEdit()
        doc = self.textedit.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        font.setPointSize(10)
        doc.setDefaultFont(font)
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
        f = cursor.charFormat()
        f.setProperty(HextEditor.byte_property, b+1)
        f.setBackground(QColor('red'))
        cursor.insertText("?", f)
        cursor.setCharFormat(QTextCursor().charFormat())
        
    def clear(self):
        # cursor = QTextCursor(self.textedit.document())
        # cursor.beginEditBlock()
        # cursor.setPosition(0)
        # cursor.setPosition(self.textedit.document().characterCount()-1,
        #                    QTextCursor.KeepAnchor)
        # cursor.removeSelectedText()
        # cursor.endEditBlock()
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
        #self.textedit.setTextCursor(cursor)

        for chunk in chunks:
            if chr(chunk[0]) in qtprintable:
                cursor.insertText(chunk.decode())
            else:
                for b in chunk:
                    self._insert_byte(cursor, b)
        cursor.endEditBlock()

    def set_bytes_highlighted(self, bs, lexer=None):
        self.textedit.setUndoRedoEnabled(False)
        self.textedit.setUpdatesEnabled(False)
        self.pretty_mode = True
        self.clear()
        self.data = bs
        if lexer:
            self.lexer = lexer
        cursor = QTextCursor(self.textedit.document())
        printable = printable_data(bs)
        css_style = ("font-size: 10pt; "
                     "font-family: monospace; "
        )
        highlighted = highlight(printable, self.lexer, HtmlFormatter(noclasses=True,
        style=get_style_by_name("colorful"), cssstyles=css_style))
        self.textedit.setHtml(highlighted)
        self.textedit.setUndoRedoEnabled(True)
        self.textedit.setUpdatesEnabled(True)
    
    def get_bytes(self):
        if not self.pretty_mode:
            self.data = self._get_bytes()
        return self.data
        
    def _get_bytes(self):
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
                    bs.append(byte-1)
                else:
                    text = f.text()
                    bs += text.encode()
                it+=1
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
        start = self.row_size*row
        end = start + self.row_size
        data = self.data[start:end]
        print_data = printable_data(data, include_newline=False)
        item = QTableWidgetItem(print_data)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.datatable.setItem(row, self.str_col, item)
        
    def redraw_table(self, length=None):
        self.datatable.setUpdatesEnabled(False)
        oldsig = self.datatable.blockSignals(True)
        self.row_size = length or self.row_size
        self.datatable.setColumnCount(self.row_size+1)
        self.datatable.setRowCount(0)
        self.str_col = self.row_size

        self.datatable.horizontalHeader().hide()
        self.datatable.verticalHeader().hide()
        
        rows = int(len(self.data)/self.row_size)
        if len(self.data) % self.row_size > 0:
            rows += 1
        self.datatable.setRowCount(rows)
        
        for i in range(rows*self.row_size):
            row = i / self.row_size
            col = i % self.row_size
            if i < len(self.data):
                dataval = "%02x"%self.data[i]
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
        self.datatable.setUpdatesEnabled(True)
            
    @classmethod
    def _format_hex(cls, n):
        return ("%02x"%n).upper()
            
    @pyqtSlot(int, int)
    def _cell_changed(self, row, col):
        oldsig = self.datatable.blockSignals(True)
        if col == self.str_col:
            return
        if len(self.data) == 0:
            return

        data_ind = self.row_size*row + col
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
    def __init__(self):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.data = b''

        self.tabWidget = QTabWidget()
        self.hexteditor = HextEditor()
        self.hexeditor = HexEditor()
        
        self.hexteditor_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.hexteditor, "Text")
        self.hexeditor_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.hexeditor, "Hex")
        self.tabWidget.currentChanged.connect(self._tab_changed)
        self.hext_selected = True

        self.layout().addWidget(self.tabWidget)
        
    @pyqtSlot(int)
    def _tab_changed(self, i):
        if i == self.hexteditor_ind:
            self.hext_selected = True
            self.data = self.hexeditor.get_bytes()
            if self.hexteditor.pretty_mode:
                self.hexteditor.set_bytes_highlighted(self.data)
            else:
                self.hexteditor.set_bytes(self.data)
        if i == self.hexeditor_ind:
            self.hext_selected = False
            self.data = self.hexteditor.get_bytes()
            self.hexeditor.set_bytes(self.data)
        
    @pyqtSlot(bytes)
    def set_bytes(self, bs):
        self.data = bs
        if self.hext_selected:
            self.hexteditor.set_bytes(bs)
        else:
            self.hexeditor.set_bytes(bs)
            
    @pyqtSlot(bytes)
    def set_bytes_highlighted(self, bs, lexer=None):
        self.data = bs
        self.hexteditor.set_bytes_highlighted(bs, lexer=lexer)

    def get_bytes(self):
        if self.hext_selected:
            self.data = self.hexteditor.get_bytes()
        else:
            self.data = self.hexeditor.get_bytes()
        return self.data
    
    def setReadOnly(self, ro):
        self.hexteditor.setReadOnly(ro)
        self.hexeditor.setReadOnly(ro)
