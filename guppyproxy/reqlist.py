import threading
import shlex

from .util import printable_data, max_len_str, query_to_str, display_error_box, display_info_box
from .proxy import InterceptMacro, HTTPRequest, RequestContext, InvalidQuery, SocketClosed
from .reqview import ReqViewWidget
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QListWidget, QHeaderView, QAbstractItemView, QPlainTextEdit, QMenu, QVBoxLayout, QHBoxLayout, QComboBox, QTabWidget, QPushButton, QLineEdit, QSpacerItem, QStackedLayout, QSizePolicy, QFrame, QToolButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from itertools import groupby

def get_field_entry():
    dropdown = QComboBox()
    dropdown.addItem("Anywhere", "all")
    dropdown.addItem("Req. Body", "reqbody")
    dropdown.addItem("Rsp. Body", "rspbody")
    dropdown.addItem("Any Body", "body")
    #dropdown.addItem("WSMessage", "wsmessage")

    dropdown.addItem("Req. Header", "reqheader")
    dropdown.addItem("Rsp. Header", "rspheader")
    dropdown.addItem("Any Header", "header")

    dropdown.addItem("Method", "method")
    dropdown.addItem("Host", "host")
    dropdown.addItem("Path", "path")
    dropdown.addItem("URL", "url")
    dropdown.addItem("Status", "statuscode")
    dropdown.addItem("Tag", "tag")

    dropdown.addItem("Any Param", "param")
    dropdown.addItem("URL Param", "urlparam")
    dropdown.addItem("Post Param", "postparam")
    dropdown.addItem("Rsp. Cookie", "rspcookie")
    dropdown.addItem("Req. Cookie", "reqcookie")
    dropdown.addItem("Any Cookie", "cookie")

    #dropdown.addItem("After", "")
    #dropdown.addItem("Before", "")
    #dropdown.addItem("TimeRange", "")
    #dropdown.addItem("Id", "")
    return dropdown

def get_string_cmp_entry():
    dropdown = QComboBox()
    dropdown.addItem("cnt.", "contains")
    dropdown.addItem("cnt. (rgx)", "containsregexp")
    dropdown.addItem("is", "is")
    dropdown.addItem("len. >", "lengt")
    dropdown.addItem("len. <", "lenlt")
    dropdown.addItem("len. =", "leneq")
    return dropdown

class StringCmpWidget(QWidget):
    returnPressed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        layout = QHBoxLayout()
        self.cmp_entry = get_string_cmp_entry()
        self.text_entry = QLineEdit()
        self.text_entry.returnPressed.connect(self.returnPressed)
        layout.addWidget(self.cmp_entry)
        layout.addWidget(self.text_entry)
        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)
        
    def get_value(self):
        str_cmp = self.cmp_entry.itemData(self.cmp_entry.currentIndex())
        str_val = self.text_entry.text()
        return [str_cmp, str_val]
    
    def reset(self):
        self.cmp_entry.setCurrentIndex(0)
        self.text_entry.setText("")
    
class StringKVWidget(QWidget):
    returnPressed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.str2_shown = False
        self.str1 = StringCmpWidget()
        self.str2 = StringCmpWidget()
        self.str1.returnPressed.connect(self.returnPressed)
        self.str2.returnPressed.connect(self.returnPressed)
        self.toggle_button = QToolButton()
        self.toggle_button.setText("+")
        
        self.toggle_button.clicked.connect(self._show_hide_str2)

        layout = QHBoxLayout()
        layout.addWidget(self.str1)
        layout.addWidget(self.str2)
        layout.addWidget(self.toggle_button)

        self.str2.setVisible(self.str2_shown)
        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)
        
    @pyqtSlot()
    def _show_hide_str2(self):
        if self.str2_shown:
            self.toggle_button.setText("+")
            self.str2_shown = False
        else:
            self.toggle_button.setText("-")
            self.str2_shown = True
        self.str2.setVisible(self.str2_shown)
        
    def get_value(self):
        retval = self.str1.get_value()
        if self.str2_shown:
            retval += self.str2.get_value()
        return retval
    
    def reset(self):
        self.str1.reset()
        self.str2.reset()

class DropdownFilterEntry(QWidget):
    # a widget that lets you enter filters using ezpz dropdowns/text boxes
    filterEntered = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        layout= QHBoxLayout()
        confirm = QToolButton()
        confirm.setText("OK")
        confirm.setToolTip("Apply the entered filter")
        self.field_entry = get_field_entry()
        #self.inv_check = TKTK
        
        # stack containing widgets for string, k/v, date, daterange
        self.str_cmp_entry = StringCmpWidget()
        self.kv_cmp_entry = StringKVWidget()
        # date
        # daterange

        self.entry_layout = QStackedLayout()
        self.entry_layout.setContentsMargins(0, 0, 0, 0)
        self.current_entry = 0
        self.entry_layout.addWidget(self.str_cmp_entry) # 0
        self.entry_layout.addWidget(self.kv_cmp_entry)  # 1
        # add date # 2
        # add daterange # 3
        
        confirm.clicked.connect(self.confirm_entry)
        self.str_cmp_entry.returnPressed.connect(self.confirm_entry)
        self.kv_cmp_entry.returnPressed.connect(self.confirm_entry)
        self.field_entry.currentIndexChanged.connect(self._display_value_widget)
        
        layout.addWidget(confirm)
        layout.addWidget(self.field_entry)
        layout.addLayout(self.entry_layout)
        #self.setMaximumHeight(26)
        
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        self._display_value_widget()
        
    @pyqtSlot()
    def _display_value_widget(self):
        # show the correct value widget in the value stack layout
        field = self.field_entry.itemData(self.field_entry.currentIndex())
        self.current_entry = 0
        if field in ("all", "reqbody", "rspbody", "body", "wsmessage", "method",
                     "host", "path", "url", "statuscode", "tag"):
            self.current_entry = 0
        elif field in ("reqheader", "rspheader", "header", "param", "urlparam"
                       "postparam", "rspcookie", "reqcookie", "cookie"):
            self.current_entry = 1
        #elif for date
        #elif for daterange
        self.entry_layout.setCurrentIndex(self.current_entry)
        
    def get_value(self):
        val = []
        field = self.field_entry.itemData(self.field_entry.currentIndex())
        val.append(field)
        if self.current_entry == 0:
            val += self.str_cmp_entry.get_value()
        elif self.current_entry == 1:
            val += self.kv_cmp_entry.get_value()
        # elif for date
        # elif for daterange
        return [val] # no support for OR
    
    @pyqtSlot()
    def confirm_entry(self):
        phrases = self.get_value()
        self.filterEntered.emit(phrases)
        self.str_cmp_entry.reset()
        self.kv_cmp_entry.reset()
        # reset date
        # reset date range
        
class TextFilterEntry(QWidget):
    # a text box that can be used to enter filters
    filterEntered = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        layout = QHBoxLayout()
        self.textEntry = QLineEdit()
        self.textEntry.returnPressed.connect(self.confirm_entry)
        self.textEntry.setToolTip("Enter the filter here and press return to apply it")
        layout.addWidget(self.textEntry)
        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)
        
    @pyqtSlot()
    def confirm_entry(self):
        args = shlex.split(self.textEntry.text())
        phrases = [list(group) for k, group in groupby(args, lambda x: x == "OR") if not k]
        self.filterEntered.emit(phrases)
        self.textEntry.setText("")

class FilterEntry(QWidget):
    # a widget that lets you switch between filter entries
    filterEntered = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.current_entry = 0
        self.max_entries = 2
        text_entry = TextFilterEntry()
        dropdown_entry = DropdownFilterEntry()
        
        text_entry.filterEntered.connect(self.filterEntered)
        dropdown_entry.filterEntered.connect(self.filterEntered)

        self.entry_layout = QStackedLayout()
        self.entry_layout.addWidget(dropdown_entry)
        self.entry_layout.addWidget(text_entry)
        
        #swap_button = QPushButton(">")
        swap_button = QToolButton()
        swap_button.setText(">")
        swap_button.setToolTip("Switch between dropdown and text entry")
        swap_button.clicked.connect(self.next_entry)
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(swap_button)
        hlayout.addLayout(self.entry_layout)
        self.setLayout(hlayout)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
    
    @pyqtSlot()
    def next_entry(self):
        self.current_entry += 1
        self.current_entry = self.current_entry % self.max_entries
        self.entry_layout.setCurrentIndex(self.current_entry)

class FilterListWidget(QTableWidget):
    # list part of the filter tab
    def __init__(self, *args, **kwargs):
        #self.reqtable = kwargs.pop("reqtable")
        self.client = kwargs.pop("client")
        QTableWidget.__init__(self, *args, **kwargs)
        self.context = RequestContext(self.client)
        
        # Set up table
        self.setColumnCount(1)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
    def append_fstr(self, fstr):
        args = shlex.split(fstr)
        phrase = [list(group) for k, group in groupby(args, lambda x: x == "OR") if not k]
        self.context.apply_phrase(phrase)
        self._append_fstr_row(fstr)
        
    def set_query(self, query):
        self.context.set_query(query)
        self.redraw_table()
        
    def pop_phrase(self):
        self.context.pop_phrase()
        self.redraw_table()
        
    def clear_phrases(self):
        self.context.set_query([])
        self.redraw_table()
        
    def _append_fstr_row(self, fstr):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(fstr))
        
    def redraw_table(self):
        self.setRowCount(0)
        query = self.context.query
        for p in query:
            condstrs = [' '.join(l) for l in p]
            fstr = ' OR '.join(condstrs)
            self._append_fstr_row(fstr)
            
    def get_query(self):
        return self.context.query
    


class FilterEditor(QWidget):
    # a widget containing a list of filters and the ability to edit the filters in the list
    filtersEdited = pyqtSignal(list)
    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop("client")
        QWidget.__init__(self, *args, **kwargs)
        layout = QVBoxLayout()

        # Manage bar
        manage_bar = QHBoxLayout()
        pop_button = QPushButton("Pop")
        pop_button.setToolTip("Remove the most recently applied filter")
        clear_button = QPushButton("Clear")
        clear_button.setToolTip("Remove all active filters")
        scope_reset_button = QPushButton("Scope")
        scope_reset_button.setToolTip("Set the active filters to the current scope")
        scope_save_button = QPushButton("Save Scope")
        scope_save_button.setToolTip("Set the scope to the current filters. Any messages that don't match the active filters will be ignored by the proxy.")
        manage_bar.addWidget(clear_button)
        manage_bar.addWidget(pop_button)
        manage_bar.addWidget(scope_reset_button)
        manage_bar.addWidget(scope_save_button)
        manage_bar.addStretch()
        mbar_widget = QWidget()
        mbar_widget.setLayout(manage_bar)
        pop_button.clicked.connect(self.pop_phrase)
        clear_button.clicked.connect(self.clear_phrases)
        scope_reset_button.clicked.connect(self.reset_to_scope)
        scope_save_button.clicked.connect(self.save_scope)
        
        # Filter list
        self.filter_list = FilterListWidget(client=self.client)
        
        # Filter entry
        self.entry = FilterEntry()
        self.entry.setMaximumHeight(self.entry.sizeHint().height())
        self.entry.filterEntered.connect(self.apply_phrase)

        layout.addWidget(mbar_widget)
        layout.addWidget(self.filter_list)
        layout.addWidget(self.entry)
        self.setLayout(layout)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        
    @pyqtSlot()
    def save_scope(self):
        query = self.filter_list.get_query()
        self.client.set_scope(query)
        display_info_box("Scope updated")
        
    @pyqtSlot()
    def reset_to_scope(self):
        query = self.client.get_scope().filter
        self.filter_list.set_query(query)
        self.filtersEdited.emit(self.filter_list.get_query())
        
    @pyqtSlot()
    def clear_phrases(self):
        self.filter_list.clear_phrases()
        self.filtersEdited.emit(self.filter_list.get_query())

    @pyqtSlot()
    def pop_phrase(self):
        self.filter_list.pop_phrase()
        self.filtersEdited.emit(self.filter_list.get_query())
        
    @pyqtSlot(list)
    def apply_phrase(self, phrase):
        fstr = query_to_str([phrase])
        try:
            self.filter_list.append_fstr(fstr)
        except InvalidQuery as e:
            display_error_box("Could not add filter:\n\n%s" % e)
            return
        self.filtersEdited.emit(self.filter_list.get_query())


class ReqBrowser(QWidget):
    # Widget containing request viewer, tabs to view list of reqs, filters, and (evevntually) site map
    # automatically updated with requests as they're saved
    def __init__(self, client, repeater_widget=None):
        QWidget.__init__(self)
        self.client = client
        self.filters = []

        self.mylayout = QGridLayout()
        self.mylayout.setSpacing(0)
        
        #reqtable updater
        self.updater = ReqListUpdater(self.client)
        
        # reqtable/search
        listWidg = QWidget(self)
        self.table_layout = QVBoxLayout(listWidg)
        self.table_layout.setSpacing(0)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        self.reqtable = ReqTableWidget(client=client, repeater_widget=repeater_widget)
        self.updater.add_reqlist_widget(self.reqtable)
        self.table_layout.addWidget(self.reqtable)
        self.reqtable.requestSelected.connect(self.update_viewer)

        # Filter widget
        filterWidg = FilterEditor(client=self.client)
        filterWidg.filtersEdited.connect(self.reqtable.set_filter)
        filterWidg.reset_to_scope()
        
        # add tabs
        self.listTabs = QTabWidget()
        self.listTabs.addTab(listWidg, "List")
        self.listTabs.addTab(filterWidg, "Filters")
        self.mylayout.addWidget(self.listTabs, 0, 0, 3, 1)
        
        # reqview
        self.reqview = ReqViewWidget()
        self.mylayout.addWidget(self.reqview, 4, 0, 2, 1)
        self.setLayout(self.mylayout)

    @pyqtSlot(list)
    def update_viewer(self, reqs):
        self.reqview.set_request(None)
        if len(reqs) > 0:
            reqh = reqs[0]
            req = self.client.req_by_id(reqh.db_id)
            self.reqview.set_request(req)

    @pyqtSlot(list)
    def update_filters(self, query):
        self.filters = query

class ReqListUpdater(QObject):
    
    newRequest = pyqtSignal(HTTPRequest)
    requestUpdated = pyqtSignal(HTTPRequest)
    requestDeleted = pyqtSignal(str)

    def __init__(self, client):
        QObject.__init__(self)
        self.mtx = threading.Lock()
        self.client = client
        self.reqlist_widgets = []
        t = threading.Thread(target=self.run_updater)
        t.start()
        
    def add_reqlist_widget(self, widget):
        self.mtx.acquire()
        try:
            self.requestUpdated.connect(widget.add_request_item)
            self.reqlist_widgets.append(widget)
        finally:
            self.mtx.release()
    
    def run_updater(self):
        conn = self.client.new_conn()
        try:
            try:
                for msg in conn.watch_storage():
                    self.mtx.acquire()
                    try:
                        if msg["Action"] == "NewRequest":
                            self.newRequest.emit(msg["Request"])
                        elif msg["Action"] == "RequestUpdated":
                            self.requestUpdated.emit(msg["Request"])
                        elif msg["Action"] == "RequestDeleted":
                            self.requestDeleted.emit(msg["MessageId"])
                    finally:
                        self.mtx.release()
            except SocketClosed:
                pass
        finally:
            conn.close()
            
    def stop(self):
        self.conn.close()
        
class ReqTableWidget(QTableWidget):

    requestSelected = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        self.repeater_widget = kwargs.pop("repeater_widget", None)
        self.client = kwargs.pop("client", None)
        QWidget.__init__(self, *args, **kwargs)
        self.reqs = {}
        self.query = []
        self.select_update_func = None
        self.itemSelectionChanged.connect(self.on_select_change)
        self.sort_key = lambda r: r.time_start
        self.sort_reverse = False
        self.selected_req = None
        self.requestSelected.connect(self._updated_selected_request)
        self.init_table()
        self.set_filter(self.query)

    def init_table(self):
        self.table_headers = ['id', 'verb', 'host', 'path', 's-code', 'req len', 'rsp len', 'time', 'mngl']
        self.setColumnCount(len(self.table_headers))
        self.setHorizontalHeaderLabels(self.table_headers)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
    def _get_row_ind(self, reqid):
        row_count = self.rowCount()
        for i in row_count:
            if self.item(i, 0).text() == reqid:
                return i
        return -1
    
    def _fill_req_row(self, row, req):
        MAX_PATH_LEN = 75
        #self.table_headers = ['id', 'verb', 'host', 'path', 's-code', 'req len', 'rsp len', 'time', 'mngl']
        self.setItem(row, 0, QTableWidgetItem(req.db_id))
        self.setItem(row, 1, QTableWidgetItem(req.method))
        self.setItem(row, 2, QTableWidgetItem(req.dest_host))
        self.setItem(row, 3, QTableWidgetItem(max_len_str(req.url.path, MAX_PATH_LEN)))
        self.setItem(row, 5, QTableWidgetItem(str(req.content_length)))

        time_str = '--'
        if req.time_start and req.time_end:
            time_delt = req.time_end - req.time_start
            time_str = "%.2f" % time_delt.total_seconds()
        self.setItem(row, 7, QTableWidgetItem(time_str))

        if req.response:
            response_code = str(req.response.status_code) + \
                            ' ' + req.response.reason
            self.setItem(row, 4, QTableWidgetItem(response_code))
            self.setItem(row, 6, QTableWidgetItem(str(req.response.content_length)))
        else:
            self.setItem(row, 4, QTableWidgetItem("--"))
            self.setItem(row, 6, QTableWidgetItem("--"))

        self.setItem(row, 8, QTableWidgetItem("N/A"))
        
    # TODO: add delete_response and delete_wsmessage handlers
        
    @pyqtSlot()
    def redraw_rows(self):
        self.setRowCount(0)
        reqs = sorted([r for _, r in self.reqs.items()], key=self.sort_key,
                      reverse=self.sort_reverse)
        for req in reqs:
            self.add_request_row(req)

    @pyqtSlot()
    def clear(self):
        self.setRowCount(0)
        self.reqs = {}
            
    @pyqtSlot(list)
    def set_requests(self, reqs, check_filter=True):
        self.clear()
        if check_filter:
            for req in reqs:
                self.add_request_item(req)
        else:
            for req in reqs:
                self.add_request_row(req)
        self.redraw_rows()

    @pyqtSlot(HTTPRequest)
    def add_request_item(self, req):
        if req.db_id != "":
            if self.client.check_request(self.query, reqid=req.db_id):
                self.add_request_row(req)
        else:
            if self.client.check_request(self.query, req=req):
                self.add_request_row(req)

    def add_request_row(self, req):
        self.reqs[req.db_id] = req
        self.insertRow(0)
        self._fill_req_row(0, req)
        
    @pyqtSlot(HTTPRequest)
    def update_request_item(self, req):
        self.reqs[req.db_id] = req
        row = self._get_row_ind(req.db_id)
        self._fill_req_row(row, req)
    
    @pyqtSlot()
    def delete_request_item(self, db_id):
        del self.reqs[db_id]
        row = self._get_row_ind(req.db_id)
        self.removeRow(row)
        
    @pyqtSlot(list)
    def set_filter(self, query):
        self.query = query
        reqs = self.client.query_storage(self.query, headers_only=True)
        self.set_requests(reqs)

    @pyqtSlot(list)
    def _updated_selected_request(self, reqs):
        if len(reqs) > 0:
            self.selected_req = reqs[0]
        else:
            self.selected_req = None
            
    def on_select_change(self):
        rows = self.selectionModel().selectedRows()
        reqs = []
        for idx in rows:
            reqid = self.item(idx.row(), 0).text()
            reqs.append(self.reqs[reqid])
        self.requestSelected.emit(reqs)
        
    def get_selected_request(self):
        req = self.client.req_by_id(self.selected_req.db_id)
        return req

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        repeaterAction = menu.addAction("Send to repeater")
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == repeaterAction:
            req = self.get_selected_request()
            if self.repeater_widget:
                self.repeater_widget.set_request(req)
            
