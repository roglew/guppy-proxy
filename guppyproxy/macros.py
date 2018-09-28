import glob
import imp
import os
import random
import re
import stat
import traceback

from .proxy import InterceptMacro, HTTPRequest, ProxyThread
from .util import display_error_box

from collections import namedtuple
from itertools import count
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QHeaderView, QAbstractItemView, QVBoxLayout, QHBoxLayout, QComboBox, QTabWidget, QPushButton, QLineEdit, QStackedLayout, QToolButton, QCheckBox, QLabel, QTableView, QPlainTextEdit, QFileDialog, QFormLayout, QSizePolicy, QDialog
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject, QVariant, Qt, QAbstractTableModel, QModelIndex, QItemSelection, QSortFilterProxyModel


errwins = set()

class MacroException(Exception):
    pass

class MacroClient(QObject):
    # A wrapper around proxy.ProxyClient that provides a simplified interface
    # to a macro to prevent it from accidentally making the proxy unstable.
    # Will add to it as needed/requested

    _macroOutput = pyqtSignal(str)
    _requestOutput = pyqtSignal(HTTPRequest)
    _ded = False

    def __init__(self, client):
        QObject.__init__(self)
        self._client = client

    def check_dead(self):
        """
        Raises an exception if the program is trying to close. Use this in your loops so that your macro doesn't keep the program from quitting
        """
        if self._ded:
            raise Exception("program over=very yes")
        
    def submit(self, req, save=False):
        """
        Submit a request. If save == True, it will be saved to history
        """
        self.check_dead()
        self._client.submit(req, save=save)

    def save(self, req):
        """
        Manually save a request to history. This can be used to perform a request and only save
        requests with interesting responses
        """
        self.check_dead()
        self._client.save_new(req)

    def output(self, s):
        """
        Write text to the "output" tab
        """
        self.check_dead()
        self._macroOutput.emit(str(s)+"\n")

    def output_req(self, req):
        """
        Add a request/response to the list of outputted requests
        """
        self.check_dead()
        self._requestOutput.emit(req)

    def new_request(self, method="GET", path="/", proto_major=1, proto_minor=1,
                    headers=None, body=bytes(), dest_host="", dest_port=80,
                    use_tls=False, tags=None):
        """
        Manually create a request object that can be submitted with client.submit()
        """
        self.check_dead()
        return HTTPRequest(method=method, path=path, proto_major=proto_major, proto_minor=proto_minor,
                           headers=headers, body=body, dest_host=dest_host, dest_port=dest_port,
                           use_tls=use_tls, tags=tags)

class FileInterceptMacro(InterceptMacro, QObject):
    """
    An intercepting macro that loads a macro from a file.
    """
    macroError = pyqtSignal(str)
    
    def __init__(self, parent, client, filename):
        InterceptMacro.__init__(self)
        QObject.__init__(self)
        self.fname = filename or None # name from the file
        self.source = None
        self.client = client
        self.parent = parent
        self.mclient = MacroClient(self.client)
        self.cached_args = {}
        self.used_args = {}

        if filename:
            self.load(filename)

    def __repr__(self):
        s = self.fname or "(No loaded macro)"
        return "<InterceptingMacro %s>" % s

    def load(self, fname):
        if fname:
            self.fname = fname
            # yes there's a race condition here, but it's better than nothing
            st = os.stat(self.fname)
            if (st.st_mode & stat.S_IWOTH):
                raise MacroException("Refusing to load world-writable macro: %s" % self.fname)
            module_name = os.path.basename(self.fname)
            try:
                self.source = imp.load_source('%s'%module_name, self.fname)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
        else:
            self.fname = None
            self.source = None

        # Update what we can do
        if self.source and hasattr(self.source, 'mangle_request'):
           self.intercept_requests = True
        else:
           self.intercept_requests = False

        if self.source and hasattr(self.source, 'mangle_response'):
            self.intercept_responses = True
        else:
            self.intercept_responses = False

        if self.source and hasattr(self.source, 'mangle_websocket'):
            self.intercept_ws = True
        else:
            self.intercept_ws = False

    def prompt_args(self):
        if not hasattr(self.source, "get_args"):
            self.used_args = {}
            return True
        try:
            spec = self.source.get_args()
        except Exception as e:
            self.macroError.emit(make_err_str(self, e))
            return False
        args = get_macro_args(self.parent, spec, cached=self.cached_args)
        if args is None:
            return False
        self.cached_args = args
        self.used_args = args
        return True

    def init(self, args):
        if hasattr(self.source, 'init'):
            try:
                self.source.init(self.mclient, args)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
                return False
        return True

    def mangle_request(self, request):
        if hasattr(self.source, 'mangle_request'):
            try:
                return self.source.mangle_request(self.mclient, self.used_args, request)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
        return request

    def mangle_response(self, request, response):
        if hasattr(self.source, 'mangle_response'):
            try:
                return self.source.mangle_response(self.mclient, self.used_args, request, response)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
        return response

    def mangle_websocket(self, request, response, message):
        if hasattr(self.source, 'mangle_websocket'):
            try:
                return self.source.mangle_websocket(self.mclient, self.used_args, request, response, message)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
        return message

class FileMacro(QObject):
    macroError = pyqtSignal(str)
    requestOutput = pyqtSignal(HTTPRequest)
    macroOutput = pyqtSignal(str)

    def __init__(self, parent, filename='', resultSlot=None):
        QObject.__init__(self)
        self.fname = filename or None # filename we load from
        self.source = None
        self.parent = parent
        self.cached_args = {}

        if self.fname:
            self.load()

    def load(self):
        if self.fname:
            st = os.stat(self.fname)
            if (st.st_mode & stat.S_IWOTH):
                raise MacroException("Refusing to load world-writable macro: %s" % self.fname)
            module_name = os.path.basename(os.path.splitext(self.fname)[0])
            try:
                self.source = imp.load_source('%s'%module_name, self.fname)
            except Exception as e:
                self.macroError.emit(make_err_str(self, e))
        else:
            self.source = None

    def execute(self, client, reqs):
        # Execute the macro
        if self.source:
            args = None
            if hasattr(self.source, "get_args"):
                try:
                    spec = self.source.get_args()
                except Exception as e:
                    self.macroError.emit(make_err_str(self, e))
                    return
                args = get_macro_args(self.parent, spec, cached=self.cached_args)
                if args is None:
                    return
                self.cached_args = args
            def perform_macro():
                mclient = MacroClient(client)
                mclient._macroOutput.connect(self.macroOutput)
                mclient._requestOutput.connect(self.requestOutput)
                try:
                    self.source.run_macro(mclient, args, reqs)
                except Exception as e:
                    self.macroError.emit(make_err_str(self, e))
            ProxyThread(target=perform_macro).start()

class MacroWidget(QWidget):
    # Tabs containing both int and active macros

    def __init__(self, client, *args, **kwargs):
        self.client = client
        QWidget.__init__(self, *args, **kwargs)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.tab_widg = QTabWidget()

        self.warning_widg = QLabel("<h1>Warning! Macros may cause instability</h1><p>Macros load and run python files into the Guppy process. If you're not careful when you write them you may cause Guppy to crash. If an active macro ends up in an infinite loop you may need to force kill the application when you quit.</p><p><b>PROCEED WITH CAUTION</b></p>")
        self.warning_widg.setWordWrap(True)
        self.int_widg = IntMacroWidget(client)
        self.active_widg = ActiveMacroWidget(client)
        self.tab_widg.addTab(self.active_widg, "Active")
        self.tab_widg.addTab(self.int_widg, "Intercepting")
        self.tab_widg.addTab(self.warning_widg, "Warning")

        self.layout().addWidget(self.tab_widg)
    
    def add_requests(self, reqs):
        # Add requests to active macro inputw
        self.active_widg.add_requests(reqs)
    
class IntMacroListModel(QAbstractTableModel):
    err_window = None
    
    def __init__(self, parent, client, *args, **kwargs):
        self.client = client
        QAbstractTableModel.__init__(self, *args, **kwargs)
        self.macros = []
        self.int_conns = {}
        self.conn_ids = count()
        self.parent = parent
        self.headers = ["On", "Path"]

    def _emit_all_data(self):
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.columnCount(None), self.rowCount(None)))

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return QVariant()

    def rowCount(self, parent):
        return len(self.macros)

    def columnCount(self, parent):
        return len(self.headers)
        
    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 1:
                rowdata = self.macros[index.row()]
                macro = rowdata[index.column()]
                return macro.fname
        if role == Qt.CheckStateRole:
            if index.column() == 0:
                if self.macros[index.row()][0]:
                    return 2
                return 0
        return QVariant()
    
    def flags(self, index):
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            f = f | Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        return f

    def setData(self, index, value, role):
        if role == Qt.CheckStateRole and index.column() == 0:
            if value:
                self.enable_macro(index.row())
            else:
                self.disable_macro(index.row())
            return True
        return False

    # Non model functions

    @pyqtSlot(str)
    def add_macro_exception(self, estr):
        if not self.err_window:
            self.err_window = MacroErrWindow()
        self.err_window.add_error(estr)
    
    def add_macro(self, macro_path):
        self.beginResetModel()
        macro = FileInterceptMacro(self.parent, self.client, macro_path)
        macro.macroError.connect(self.add_macro_exception)
        self.macros.append([False, macro, -1])
        self._emit_all_data()
        self.endResetModel()
        

    def remove_macro(self, ind):
        self.beginResetModel()
        self.disable_macro(ind)
        self.macros = self.macros[:ind] + self.macros[ind+1:]
        self._emit_all_data()
        self.endResetModel()


    def enable_macro(self, ind):
        self.beginResetModel()
        macro = self.macros[ind][1]
        if not macro.init(None):
            return
        try:
            macro.load(macro.fname)
        except MacroException as e:
            display_error_box("Macro could not be loaded: %s", e)
            return
        except Exception as e:
            self.add_macro_exception(make_err_str(macro, e))
            return
        if not (macro.intercept_requests or macro.intercept_responses or macro.intercept_ws):
            display_error_box("Macro must implement mangle_request or mangle_response")
            return
        if not macro.prompt_args():
            return
        conn = self.client.new_conn()
        conn_id = next(self.conn_ids)
        self.macros[ind][2] = conn_id
        self.int_conns[conn_id] = conn
        conn.intercept(macro)
        self.macros[ind][0] = True
        self._emit_all_data()
        self.endResetModel()

    def disable_macro(self, ind):
        self.beginResetModel()
        conn_id = self.macros[ind][2]
        if conn_id >= 0:
            conn = self.int_conns[conn_id]
            conn.close()
            del self.int_conns[conn_id]
        self.macros[ind][2] = -1
        self.macros[ind][0] = False
        self._emit_all_data()
        self.endResetModel()

class IntMacroWidget(QWidget):
    # Lets the user enable/disable int. macros

    def __init__(self, client, *args, **kwargs):
        self.client = client
        self.macros = []
        QWidget.__init__(self, *args, **kwargs)
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        buttonLayout = QHBoxLayout()
        add_button = QPushButton("Add...")
        remove_button = QPushButton("Remove")
        add_button.clicked.connect(self.browse_macro)
        remove_button.clicked.connect(self.remove_selected)
        
        # Set up table
        self.macroListModel = IntMacroListModel(self, self.client)
        self.macroListView = QTableView()
        self.macroListView.setModel(self.macroListModel)

        self.macroListView.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.macroListView.verticalHeader().hide()
        self.macroListView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.macroListView.horizontalHeader().hide()
        self.macroListView.horizontalHeader().setStretchLastSection(True)

        self.macroListView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.macroListView.setSelectionMode(QAbstractItemView.SingleSelection)
        
        buttonLayout.addWidget(add_button)
        buttonLayout.addWidget(remove_button)
        buttonLayout.addStretch()
        self.layout().addWidget(self.macroListView)
        self.layout().addLayout(buttonLayout)
        
    def add_macro(self, fname):
        self.macroListModel.add_macro(fname)
    
    def reload_macros(self):
        self.macroListModel.reload_macros()
        
    def browse_macro(self):
        fname, ftype = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "Python File (*.py)")
        if not fname:
            return
        self.add_macro(fname)

    def remove_selected(self):
        rows = self.macroListView.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        for idx in rows:
            row = idx.row()
            self.macroListModel.remove_macro(row)
            return
        
class ActiveMacroModel(QAbstractTableModel):
    err_window = None
    requestOutput = pyqtSignal(HTTPRequest)
    macroOutput = pyqtSignal(str)

    def __init__(self, parent, client, *args, **kwargs):
        QAbstractTableModel.__init__(self, *args, **kwargs)
        self.client = client
        self.parent = parent
        self.headers = ["Path"]
        self.macros = []

    def _emit_all_data(self):
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.columnCount(None), self.rowCount(None)))
        
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return QVariant()

    def rowCount(self, parent):
        return len(self.macros)

    def columnCount(self, parent):
        return len(self.headers)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.macros[index.row()][0]
        return QVariant()

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def add_macro(self, path):
        self.beginResetModel()
        self._emit_all_data()
        fileMacro = FileMacro(self.parent, filename=path)
        fileMacro.macroOutput.connect(self.macroOutput)
        fileMacro.macroError.connect(self.add_macro_exception)
        fileMacro.requestOutput.connect(self.requestOutput)
        self.macros.append((path, fileMacro))
        self.endResetModel()

    def run_macro(self, ind, reqs=None):
        path, macro = self.macros[ind]
        reqs = reqs or []
        macro.load()
        macro.execute(self.client, reqs)

    def remove_macro(self, ind):
        self.beginResetModel()
        self._emit_all_data()
        self.macros = self.macros[:ind] + self.macros[ind+1:]
        self.endResetModel()

    @pyqtSlot(str)
    def add_macro_exception(self, estr):
        if not self.err_window:
            self.err_window = MacroErrWindow()
        self.err_window.add_error(estr)

class ActiveMacroWidget(QWidget):
    # Provides an interface to send a set of requests to python scripts
    
    def __init__(self, client, *args, **kwargs):
        from .reqlist import ReqTableWidget, ReqBrowser

        QWidget.__init__(self, *args, **kwargs)
        self.client = client
        self.setLayout(QVBoxLayout())
        tab_widg = QTabWidget()

        # Input
        inputLayout = QVBoxLayout()
        inputLayout.setContentsMargins(0, 0, 0, 0)
        inputLayout.addWidget(QLabel("Input"))
        inputLayout.setSpacing(8)
        self.reqlist = ReqTableWidget(self.client)
        butlayout = QHBoxLayout()
        delButton = QPushButton("Remove")
        clearButton = QPushButton("Clear")
        importAllButton = QPushButton("Import Currently Filtered Requests")
        delButton.clicked.connect(self.reqlist.delete_selected)
        clearButton.clicked.connect(self.reqlist.clear)
        importAllButton.clicked.connect(self.import_all_reqs)
        butlayout.addWidget(delButton)
        butlayout.addWidget(clearButton)
        butlayout.addWidget(importAllButton)
        butlayout.addStretch()
        inputLayout.addWidget(self.reqlist)
        inputLayout.addLayout(butlayout)

        # Macro selection
        listLayout = QVBoxLayout()
        listLayout.addWidget(QLabel("Macros"))
        listLayout.setContentsMargins(0, 0, 0, 0)
        listLayout.setSpacing(8)
        self.tableModel = ActiveMacroModel(self, self.client)
        self.tableModel.macroOutput.connect(self.add_macro_output)
        self.tableView = QTableView()
        self.tableModel.requestOutput.connect(self.add_request_output)
        self.tableView.setModel(self.tableModel)
        self.tableView.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableView.verticalHeader().hide()
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.horizontalHeader().hide()
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        butlayout2 = QHBoxLayout()
        addButton2 = QPushButton("Add...")
        addButton2.clicked.connect(self.browse_macro)
        delButton2 = QPushButton("Remove")
        delButton2.clicked.connect(self.remove_selected)
        runButton2 = QPushButton("Run")
        runButton2.clicked.connect(self.run_selected_macro)
        butlayout2.addWidget(addButton2)
        butlayout2.addWidget(delButton2)
        butlayout2.addWidget(runButton2)
        butlayout2.addStretch()
        listLayout.addWidget(self.tableView)
        listLayout.addLayout(butlayout2)

        # Output
        outputLayout = QVBoxLayout()
        outputLayout.setContentsMargins(0, 0, 0, 0)
        outputLayout.setSpacing(8)
        self.outreqlist = ReqBrowser(self.client, reload_reqs=False, filter_tab=False)
        self.outreqlist.listWidg.allow_save = True
        outbutlayout = QHBoxLayout()
        delButton = QPushButton("Clear")
        delButton.clicked.connect(self.clear_output)
        outbutlayout.addWidget(delButton)
        outbutlayout.addStretch()
        outputLayout.addWidget(self.outreqlist)
        outputLayout.addLayout(outbutlayout)

        text_out_layout = QVBoxLayout()
        text_out_layout.setContentsMargins(0, 0, 0, 0)
        self.macro_text_out = QPlainTextEdit()
        text_out_layout.addWidget(self.macro_text_out)
        text_out_butlayout = QHBoxLayout()
        clearBut = QPushButton("Clear")
        clearBut.clicked.connect(self.clear_text_output)
        text_out_butlayout.addWidget(clearBut)
        text_out_butlayout.addStretch()
        text_out_layout.addLayout(text_out_butlayout)

        # Tabs
        intab = QWidget()
        intabLayout = QVBoxLayout()
        intabLayout.setContentsMargins(0, 0, 0, 0)
        intabLayout.addLayout(listLayout)
        intabLayout.addLayout(inputLayout)
        intab.setLayout(intabLayout)
        tab_widg.addTab(intab, "Input")

        reqOutputWidg = QWidget()
        reqOutputWidg.setLayout(outputLayout)
        tab_widg.addTab(reqOutputWidg, "Req. Output")

        textOutputWidg = QWidget()
        textOutputWidg.setLayout(text_out_layout)
        tab_widg.addTab(textOutputWidg, "Text Output")

        self.layout().addWidget(tab_widg)

    @pyqtSlot(list)
    def add_requests(self, reqs):
        # Add requests to active macro input
        for req in reqs:
            self.reqlist.add_request(req)
            
    @pyqtSlot()
    def browse_macro(self):
        fname, ftype = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "Python File (*.py)")
        if not fname:
            return
        self.tableModel.add_macro(fname)
    
    @pyqtSlot()
    def remove_selected(self):
        rows = self.tableView.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        for idx in rows:
            row = idx.row()
            self.tableModel.remove_macro(row)
            return

    @pyqtSlot()
    def run_selected_macro(self):
        rows = self.tableView.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        for idx in rows:
            row = idx.row()
            reqs = self.reqlist.get_all_requests()
            self.tableModel.run_macro(row, reqs)
            return

    @pyqtSlot(HTTPRequest)
    def add_request_output(self, req):
        self.outreqlist.listWidg.add_request(req)

    @pyqtSlot()
    def clear_output(self):
        self.outreqlist.set_requests([])

    @pyqtSlot()
    def clear_text_output(self):
        self.macro_text_out.setPlainText("")

    @pyqtSlot(str)
    def add_macro_output(self, s):
        t = self.macro_text_out.toPlainText()
        t += s
        self.macro_text_out.setPlainText(t)
        
    @pyqtSlot()
    def import_all_reqs(self):
        reqs = self.client.in_context_requests(headers_only=True)
        self.add_requests(reqs)
        

class MacroErrWindow(QWidget):

    def __init__(self, *args, **kwargs):
        QObject.__init__(self, *args, **kwargs)
        self.msg = ""
        self.setLayout(QVBoxLayout())
        self.msgwidg = QPlainTextEdit()
        self.layout().addWidget(self.msgwidg)
    
    def add_error(self, msg):
        self.msg += msg + "\n\n"
        self.msgwidg.setPlainText(self.msg)
        self.show()
        
    def closeEvent(self, event):
        self.msgwidg.setPlainText("")
        IntMacroListModel.err_window = None
        ActiveMacroModel.err_window = None
        
def make_err_str(macro, e):
    estr = "Exception in macro %s:\n" % macro.fname
    estr += str(e) + '\n'
    estr += str(traceback.format_exc())
    return estr

class ArgWindow(QDialog):
    def __init__(self, parent, argspec, cached=None):
        QDialog.__init__(self, parent)
        winLayout = QVBoxLayout()
        formLayout = QFormLayout()
        self.shownargs = []
        self.canceled = False
        argnames = set()
        for spec in argspec:
            name = None
            argtype = None
            argval = None
            if isinstance(spec, str):
                name = spec
                argtype = "str"
            else:
                if len(spec) > 0:
                    name = spec[0]
                if len(spec) > 1:
                    argtype = spec[1]
                if len(spec) > 2:
                    argval = spec[2]
                if not name:
                    continue
                if not argtype:
                    continue

            if name in argnames:
                continue

            widg = None
            if argtype.lower() in ("str", "string"):
                argtype = "str"
                widg = QLineEdit()
                if name in cached:
                    widg.setText(cached[name])
            else:
                return
            formLayout.addRow(QLabel(name), widg)
            self.shownargs.append(((name, argtype, argval), widg))
            argnames.add(name)
        butlayout = QHBoxLayout()
        okbut = QPushButton("Ok")
        okbut.clicked.connect(self.accept)
        cancelbut = QPushButton("Cancel")
        cancelbut.clicked.connect(self.reject)
        self.rejected.connect(self._set_canceled)
        butlayout.addWidget(okbut)
        butlayout.addWidget(cancelbut)
        butlayout.addStretch()
        winLayout.addLayout(formLayout)
        winLayout.addLayout(butlayout)

        self.setLayout(winLayout)

    @pyqtSlot()
    def _set_canceled(self):
        self.canceled = True

    def get_args(self):
        if self.canceled:
            return None
        retargs = {}
        for shownarg in self.shownargs:
            spec, widg = shownarg
            name, argtype, typeargs = spec
            if argtype == "str":
                retargs[name] = widg.text()
        return retargs

def get_macro_args(parent, argspec, cached=None):
    if not isinstance(argspec, list):
        return

    argwin = ArgWindow(parent, argspec, cached=cached)
    argwin.exec_()
    return argwin.get_args()

