import threading
import shlex

from guppyproxy.util import max_len_str, query_to_str, display_error_box, display_info_box, display_req_context, display_multi_req_context, hostport, method_color, sc_color, DisableUpdates, host_color
from guppyproxy.proxy import HTTPRequest, RequestContext, InvalidQuery, SocketClosed, time_to_nsecs, ProxyThread
from guppyproxy.reqview import ReqViewWidget
from guppyproxy.reqtree import ReqTreeView
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QGridLayout, QHeaderView, QAbstractItemView, QVBoxLayout, QHBoxLayout, QComboBox, QTabWidget, QPushButton, QLineEdit, QStackedLayout, QToolButton, QCheckBox, QLabel, QTableView, QMenu
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject, QVariant, Qt, QAbstractTableModel, QModelIndex, QItemSelection, QSortFilterProxyModel
from itertools import groupby, count

def get_field_entry():
    dropdown = QComboBox()
    dropdown.addItem("Anywhere", "all")
    dropdown.addItem("Req. Body", "reqbody")
    dropdown.addItem("Rsp. Body", "rspbody")
    dropdown.addItem("Any Body", "body")
    # dropdown.addItem("WSMessage", "wsmessage")

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

    # dropdown.addItem("After", "")
    # dropdown.addItem("Before", "")
    # dropdown.addItem("TimeRange", "")
    # dropdown.addItem("Id", "")
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


def dt_sort_key(r):
    if r.time_start:
        return time_to_nsecs(r.time_start)
    return 0


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
        layout = QHBoxLayout()
        confirm = QToolButton()
        confirm.setText("OK")
        confirm.setToolTip("Apply the entered filter")
        self.field_entry = get_field_entry()

        # stack containing widgets for string, k/v, date, daterange
        self.str_cmp_entry = StringCmpWidget()
        self.kv_cmp_entry = StringKVWidget()
        self.inv_entry = QCheckBox("inv")
        # date
        # daterange

        self.entry_layout = QStackedLayout()
        self.entry_layout.setContentsMargins(0, 0, 0, 0)
        self.current_entry = 0
        self.entry_layout.addWidget(self.str_cmp_entry)
        self.entry_layout.addWidget(self.kv_cmp_entry)
        # add date # 2
        # add daterange # 3

        confirm.clicked.connect(self.confirm_entry)
        self.str_cmp_entry.returnPressed.connect(self.confirm_entry)
        self.kv_cmp_entry.returnPressed.connect(self.confirm_entry)
        self.field_entry.currentIndexChanged.connect(self._display_value_widget)

        layout.addWidget(confirm)
        layout.addWidget(self.inv_entry)
        layout.addWidget(self.field_entry)
        layout.addLayout(self.entry_layout)

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
        # elif for date
        # elif for daterange
        self.entry_layout.setCurrentIndex(self.current_entry)

    def get_value(self):
        val = []
        if self.inv_entry.isChecked():
            val.append("inv")
        field = self.field_entry.itemData(self.field_entry.currentIndex())
        val.append(field)
        if self.current_entry == 0:
            val += self.str_cmp_entry.get_value()
        elif self.current_entry == 1:
            val += self.kv_cmp_entry.get_value()
        # elif for date
        # elif for daterange
        return [val]  # no support for OR

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
        self.text_entry = TextFilterEntry()
        dropdown_entry = DropdownFilterEntry()

        self.text_entry.filterEntered.connect(self.filterEntered)
        dropdown_entry.filterEntered.connect(self.filterEntered)

        self.entry_layout = QStackedLayout()
        self.entry_layout.addWidget(dropdown_entry)
        self.entry_layout.addWidget(self.text_entry)

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

    def set_entry(self, entry):
        self.current_entry = entry
        self.current_entry = self.current_entry % self.max_entries
        self.entry_layout.setCurrentIndex(self.current_entry)


class FilterListWidget(QTableWidget):
    # list part of the filter tab
    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop("client")
        QTableWidget.__init__(self, *args, **kwargs)
        self.context = RequestContext(self.client)

        # Set up table
        self.setColumnCount(1)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        #self.setSelectionMode(QAbstractItemView.NoSelection)
        #self.setEditTriggers(QAbstractItemView.NoEditTriggers)

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

    builtin_filters = (
        ('No Images', ['inv', 'path', 'containsregexp', r'(\.png$|\.jpg$|\.jpeg$|\.gif$|\.ico$|\.bmp$|\.svg$)']),
        ('No JavaScript/CSS/Fonts', ['inv', 'path', 'containsregexp', r'(\.js$|\.css$|\.woff$)']),
    )

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

        self.builtin_combo = QComboBox()
        self.builtin_combo.addItem("Apply a built-in filter", None)
        for desc, filt in FilterEditor.builtin_filters:
            self.builtin_combo.addItem(desc, filt)
        self.builtin_combo.currentIndexChanged.connect(self._apply_builtin_filter)

        manage_bar.addWidget(clear_button)
        manage_bar.addWidget(pop_button)
        manage_bar.addWidget(scope_reset_button)
        manage_bar.addWidget(scope_save_button)
        manage_bar.addWidget(self.builtin_combo)
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

    @pyqtSlot(int)
    def _apply_builtin_filter(self, ind):
        phrase = self.builtin_combo.itemData(ind)
        if phrase:
            self.apply_phrase([phrase])
        self.builtin_combo.setCurrentIndex(0)
        
    def set_is_text(self, is_text):
        if is_text:
            self.entry.set_entry(1)
        else:
            self.entry.set_entry(0)
        

class ReqListModel(QAbstractTableModel):
    requestsLoading = pyqtSignal()
    requestsLoaded = pyqtSignal()
    
    HD_ID = 0
    HD_VERB = 1
    HD_HOST = 2
    HD_PATH = 3
    HD_SCODE = 4
    HD_REQLEN = 5
    HD_RSPLEN = 6
    HD_TIME = 7
    HD_TAGS = 8
    HD_MNGL = 9

    def __init__(self, client, *args, **kwargs):
        QAbstractTableModel.__init__(self, *args, **kwargs)
        self.client = client
        self.header_order = [
            self.HD_ID,
            self.HD_VERB,
            self.HD_HOST,
            self.HD_PATH,
            self.HD_SCODE,
            self.HD_REQLEN,
            self.HD_RSPLEN,
            self.HD_TIME,
            self.HD_TAGS,
            self.HD_MNGL,
        ]
        self.table_headers = {
            self.HD_ID: "ID",
            self.HD_VERB: "Method",
            self.HD_HOST: "Host",
            self.HD_PATH: "Path",
            self.HD_SCODE: "S-Code",
            self.HD_REQLEN: "Req Len",
            self.HD_RSPLEN: "Rsp Len",
            self.HD_TIME: "Time",
            self.HD_TAGS: "Tags",
            self.HD_MNGL: "Mngl",
        }
        self.reqs = []
        self.sort_enabled = False
        self.header_count = len(self.header_order)
        self.reqs_loaded = 0
            
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            hd = self.header_order[section]
            return self.table_headers[hd]
        return QVariant()
            
    def rowCount(self, parent):
        return self.reqs_loaded
    
    def columnCount(self, parent):
        return self.header_count
    
    def _gen_req_row(self, req):
        MAX_PATH_LEN = 60
        MAX_TAG_LEN = 40
        reqid = self.client.get_reqid(req)
        method = req.method
        host = hostport(req)
        path = max_len_str(req.url.path, MAX_PATH_LEN)
        reqlen = str(req.content_length)
        tags = max_len_str(', '.join(sorted(req.tags)), MAX_TAG_LEN)
        
        if req.response:
            scode = str(req.response.status_code) + ' ' + req.response.reason
            rsplen = str(req.response.content_length)
        else:
            scode = "--"
            rsplen = "--"

        if req.time_start and req.time_end:
            time_delt = req.time_end - req.time_start
            reqtime = ("%.2f" % time_delt.total_seconds())
        else:
            reqtime = "--"
        if req.unmangled and req.response and req.response.unmangled:
            manglestr = "q/s"
        elif req.unmangled:
            manglestr = "q"
        elif req.response and req.response.unmangled:
            manglestr = "s"
        else:
            manglestr = "N/A"
        return (req, reqid, method, host, path, scode, reqlen, rsplen, reqtime, tags, manglestr)
        
    
    def data(self, index, role):
        if role == Qt.BackgroundColorRole:
           req = self.reqs[index.row()][0]
           if index.column() == 2:
               return host_color(hostport(req))
           elif index.column() == 4:
               if req.response:
                   return sc_color(str(req.response.status_code))
           elif index.column() == 1:
               return method_color(req.method)
           return QVariant()
        elif role == Qt.DisplayRole:
           rowdata = self.reqs[index.row()]
           return rowdata[index.column()+1]
        return QVariant()
    
    def canFetchMore(self, parent):
        if parent.isValid():
            return False
        return (self.reqs_loaded < len(self.reqs))
    
    def fetchMore(self, parent):
        if parent.isValid():
            return
        if self.reqs_loaded == len(self.reqs):
            return
        n_to_fetch = 50
        if self.reqs_loaded + n_to_fetch > len(self.reqs):
            n_to_fetch = len(self.reqs) - self.reqs_loaded
        self.beginInsertRows(QModelIndex(), self.reqs_loaded, self.reqs_loaded + n_to_fetch)
        self.reqs_loaded += n_to_fetch
        self.endInsertRows()

    def _sort_reqs(self):
        def skey(rowdata):
            return dt_sort_key(rowdata[0])
        if self.sort_enabled:
            self.reqs = sorted(self.reqs, key=skey, reverse=True)
        
    def _req_ind(self, req=None, reqid=None):
        if not reqid:
            reqid = self.client.get_reqid(req)
        for ind, rowdata in zip(count(), self.reqs):
            req = rowdata[0]
            if self.client.get_reqid(req) == reqid:
                return ind
        return -1
    
    def _emit_all_data(self):
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(None), self.columnCount(None)))
        
    def _set_requests(self, reqs):
        self.reqs = [self._gen_req_row(req) for req in reqs]
        self.reqs_loaded = 0
    
    def set_requests(self, reqs):
        self.beginResetModel()
        self._set_requests(reqs)
        self._sort_reqs()
        self._emit_all_data()
        self.endResetModel()
    
    def clear(self):
        self.beginResetModel()
        self.reqs = []
        self.reqs_loaded = 0
        self._emit_all_data()
        self.endResetModel()

    def add_request_head(self, req):
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.reqs = [self._gen_req_row(req)] + self.reqs
        self.reqs_loaded += 1
        self.endInsertRows()
    
    def add_request(self, req):
        self.beginResetModel()
        self.reqs.append(self._gen_req_row(req))
        self.reqs_loaded = 0
        self._sort_reqs()
        self._emit_all_data()
        self.endResetModel()
        
    def add_requests(self, reqs):
        self.beginResetModel()
        for req in reqs:
            self.reqs.append(self._gen_req_row(req))
        self.reqs_loaded = 0
        self._sort_reqs()
        self._emit_all_data()
        self.endResetModel()
    
    def update_request(self, req):
        ind = self._req_ind(req)
        if ind < 0:
            return
        self.reqs[ind] = self._gen_req_row(req)
        self.dataChanged.emit(self.createIndex(ind, 0), self.createIndex(ind, self.rowCount(None)))

    def delete_request(self, req=None, reqid=None):
        ind = self._req_ind(req, reqid)
        if ind < 0:
            return
        self.beginRemoveRows(QModelIndex(), ind, ind)
        self.reqs_loaded -= 1
        self.reqs = self.reqs[:ind] + self.reqs[(ind+1):]
        self.endRemoveRows()
        
    def has_request(self, req=None, reqid=None):
        if self._req_ind(req, reqid) < 0:
            return False
        return True
    
    def get_requests(self):
        return [row[0] for row in self.reqs]
    
    def disable_sort(self):
        self.sort_enabled = False

    def enable_sort(self):
        self.sort_enabled = True
        self._sort_reqs()
        
    def req_by_ind(self, ind):
        return self.reqs[ind][0]

    
class ReqBrowser(QWidget):
    # Widget containing request viewer, tabs to view list of reqs, filters, and (evevntually) site map
    # automatically updated with requests as they're saved
    def __init__(self, client, repeater_widget=None, macro_widget=None, reload_reqs=True, update=False, filter_tab=True, is_client_context=False):
        QWidget.__init__(self)
        self.client = client
        self.filters = []
        self.reload_reqs = reload_reqs

        self.mylayout = QGridLayout()
        self.mylayout.setSpacing(0)
        self.mylayout.setContentsMargins(0, 0, 0, 0)

        # reqtable updater
        if update:
            self.updater = ReqListUpdater(self.client)
        else:
            self.updater = None

        # reqtable/search
        self.listWidg = ReqTableWidget(client, repeater_widget=repeater_widget, macro_widget=macro_widget)
        if self.updater:
            self.updater.add_reqlist_widget(self.listWidg)
        self.listWidg.requestsSelected.connect(self.update_viewer)
        self.listLayout = QVBoxLayout()
        self.listLayout.setContentsMargins(0, 0, 0, 0)
        self.listLayout.setSpacing(0)
        self.listButtonLayout = QHBoxLayout()
        self.listButtonLayout.setContentsMargins(0, 0, 0, 0)
        clearSelectionBut = QPushButton("Clear Selection")
        clearSelectionBut.clicked.connect(self.listWidg.clear_selection)
        self.listButtonLayout.addWidget(clearSelectionBut)
        self.listButtonLayout.addStretch()
        self.listLayout.addWidget(self.listWidg)
        self.listLayout.addLayout(self.listButtonLayout)

        # Filter widget
        self.filterWidg = FilterEditor(client=self.client)
        self.filterWidg.filtersEdited.connect(self.listWidg.set_filter)
        if is_client_context:
            self.filterWidg.filtersEdited.connect(self.set_client_context)
        self.filterWidg.reset_to_scope()

        # Tree widget
        self.treeWidg = ReqTreeView()

        # add tabs
        self.listTabs = QTabWidget()
        lwidg = QWidget()
        lwidg.setLayout(self.listLayout)
        self.listTabs.addTab(lwidg, "List")
        self.tree_ind = self.listTabs.count()
        self.listTabs.addTab(self.treeWidg, "Tree")
        if filter_tab:
            self.listTabs.addTab(self.filterWidg, "Filters")
        self.listTabs.currentChanged.connect(self._tab_changed)

        # reqview
        self.reqview = ReqViewWidget(info_tab=True, param_tab=True, tag_tab=True)
        self.reqview.set_tags_read_only(False)
        self.reqview.tag_widg.tagsUpdated.connect(self._tags_updated)
        self.listWidg.req_view_widget = self.reqview

        self.mylayout.addWidget(self.reqview, 0, 0, 3, 1)
        self.mylayout.addWidget(self.listTabs, 4, 0, 2, 1)

        self.setLayout(self.mylayout)
        
    def show_filters(self):
        self.listTabs.setCurrentIndex(2)

    def show_history(self):
        self.listTabs.setCurrentIndex(0)

    def show_tree(self):
        self.listTabs.setCurrentIndex(1)

    @pyqtSlot(list)
    def set_client_context(self, query):
        self.client.context.set_query(query)
        
    @pyqtSlot()
    def reset_to_scope(self):
        self.filterWidg.reset_to_scope()

    @pyqtSlot(list)
    def update_viewer(self, reqs):
        self.reqview.set_request(None)
        if len(reqs) > 0:
            if self.reload_reqs:
                reqh = reqs[0]
                req = self.client.req_by_id(reqh.db_id)
            else:
                req = reqs[0]
            self.reqview.set_request(req)

    @pyqtSlot(list)
    def update_filters(self, query):
        self.filters = query

    @pyqtSlot(HTTPRequest)
    def add_request_item(self, req):
        self.listWidg.add_request_item(req)
        self.treeWidg.add_request_item(req)

    @pyqtSlot(list)
    def set_requests(self, reqs):
        self.listWidg.set_requests(reqs)
        self.treeWidg.set_requests(reqs)

    @pyqtSlot(int)
    def _tab_changed(self, i):
        if i == self.tree_ind:
            self.treeWidg.set_requests(self.listWidg.get_requests())

    @pyqtSlot(set)
    def _tags_updated(self, tags):
        req = self.reqview.req
        req.tags = tags
        if req.db_id:
            reqid = self.client.get_reqid(req)
            self.client.clear_tag(reqid)
            for tag in tags:
                self.client.add_tag(reqid, tag)
        
    def set_filter_is_text(self, is_text):
        self.filterWidg.set_is_text(is_text)
                

class ReqListUpdater(QObject):

    newRequest = pyqtSignal(HTTPRequest)
    requestUpdated = pyqtSignal(HTTPRequest)
    requestDeleted = pyqtSignal(str)

    def __init__(self, client):
        QObject.__init__(self)
        self.mtx = threading.Lock()
        self.client = client
        self.reqlist_widgets = []
        self.t = ProxyThread(target=self.run_updater)
        self.t.start()

    def add_reqlist_widget(self, widget):
        self.mtx.acquire()
        try:
            self.newRequest.connect(widget.add_request)
            self.requestUpdated.connect(widget.update_request)
            self.requestDeleted.connect(widget.delete_request)
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
                return
        finally:
            conn.close()

    def stop(self):
        self.conn.close()


class ReqTableWidget(QWidget):
    requestsChanged = pyqtSignal(list)
    requestsSelected = pyqtSignal(list)

    def __init__(self, client, repeater_widget=None, macro_widget=None, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.allow_save = False

        self.client = client
        self.repeater_widget = repeater_widget
        self.macro_widget = macro_widget
        self.query = []
        self.req_view_widget = None

        self.setLayout(QStackedLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.tableModel = ReqListModel(self.client)
        self.tableView = QTableView()
        self.tableView.setModel(self.tableModel)

        self.tableView.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableView.verticalHeader().hide()
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        
        self.tableView.selectionModel().selectionChanged.connect(self.on_select_change)
        self.tableModel.dataChanged.connect(self._paint_view)
        self.tableModel.rowsInserted.connect(self._on_rows_inserted)
        self.requestsChanged.connect(self.set_requests)
        self.requestsSelected.connect(self._updated_selected_request)
        
        self.selected_reqs = []
        
        self.layout().addWidget(self.tableView)
        self.layout().addWidget(QLabel("<b>Loading requests from data file...</b>"))
        
    @pyqtSlot(HTTPRequest)
    def add_request(self, req):
        with DisableUpdates(self.tableView):
            if req.db_id != "":
                reqid = self.client.get_reqid(req)
                if self.client.check_request(self.query, reqid=reqid):
                    self.tableModel.add_request_head(req)
                if req.unmangled and req.unmangled.db_id != "" and self.tableModel.has_request(req.unmangled):
                    self.tableModel.delete_request(req.unmangled)
            else:
                if self.client.check_request(self.query, req=req):
                    self.tableModel.add_request_head(req)
                    
    @pyqtSlot()
    def clear(self):
        self.tableModel.clear()
        
    def get_requests(self):
        return self.tableModel.get_requests()

    @pyqtSlot(list)
    def set_requests(self, reqs, check_filter=False):
        to_add = []
        if not check_filter:
            to_add = reqs
        else:
            for req in reqs:
                if req.db_id != "":
                    reqid = self.client.get_reqid(req)
                    if self.client.check_request(self.query, reqid=reqid):
                        to_add.append(req)
                else:
                    if self.client.check_request(self.query, req=req):
                        to_add.append(req)
        with DisableUpdates(self.tableView):
            self.clear()
            self.tableModel.disable_sort()
            self.tableModel.add_requests(to_add)
            self.tableModel.enable_sort()
            self.set_is_not_loading()

    @pyqtSlot(HTTPRequest)
    def update_request(self, req):
        with DisableUpdates(self.tableView):
            self.tableModel.update_request(req)
            if req.db_id != "":
                if req.unmangled and req.unmangled.db_id != "":
                    self.tableModel.delete_request(reqid=self.client.get_reqid(req.unmangled))

    @pyqtSlot(str)
    def delete_request(self, reqid):
        with DisableUpdates(self.tableView):
            self.tableModel.delete_request(reqid=reqid)

    @pyqtSlot(list)
    def set_filter(self, query):
        self.query = query
        self.set_is_loading()
        self.client.query_storage_async(self.requestsChanged, self.query, headers_only=True)

    @pyqtSlot(list)
    def _updated_selected_request(self, reqs):
        if len(reqs) > 0:
            self.selected_reqs = reqs
        else:
            self.selected_reqs = []
            
    @pyqtSlot(QModelIndex, int, int)
    def _on_rows_inserted(self, parent, first, last):
        rows = self.tableView.selectionModel().selectedRows()
        if len(rows) > 0:
            row = rows[0].row()
            idx = self.tableModel.index(row, 0, QModelIndex())
            self.tableView.scrollTo(idx)

    @pyqtSlot(QItemSelection, QItemSelection)
    def on_select_change(self, newSelection, oldSelection):
        reqs = []
        added = set()
        for rowidx in self.tableView.selectionModel().selectedRows():
            row = rowidx.row()
            if row not in added:
                reqs.append(self.tableModel.req_by_ind(row))
                added.add(row)
        self.requestsSelected.emit(reqs)

    @pyqtSlot()
    def clear_selection(self):
        self.tableView.clearSelection()
        
    def get_selected_request(self):
        # load the full request
        if len(self.selected_reqs) > 0:
            return self.client.load_by_reqheaders(self.selected_reqs[0])
        else:
            return None

    def get_selected_requests(self):
        ret = []
        for hreq in self.selected_reqs:
            ret.append(self.client.load_by_reqheaders(hreq))
        return ret

    def get_all_requests(self):
        return [self.client.req_by_id(self.client.get_reqid(req)) for req in self.tableModel.get_requests()]

    def contextMenuEvent(self, event):
        if len(self.selected_reqs) > 1:
            reqs = self.get_selected_requests()
            display_multi_req_context(self, self.client, reqs, event,
                                      macro_widget=self.macro_widget,
                                      save_option=self.allow_save)
        elif len(self.selected_reqs) == 1:
            req = self.get_selected_request()
            display_req_context(self, self.client, req, event,
                                repeater_widget=self.repeater_widget,
                                req_view_widget=self.req_view_widget,
                                macro_widget=self.macro_widget,
                                save_option=self.allow_save)

    def set_is_loading(self):
        self.set_loading(True)

    def set_is_not_loading(self):
        self.set_loading(False)

    def set_loading(self, is_loading):
        with DisableUpdates(self.tableView):
            if is_loading:
                self.layout().setCurrentIndex(1)
            else:
                self.layout().setCurrentIndex(0)
            
    @pyqtSlot(QModelIndex, QModelIndex)
    def _paint_view(self, indA, indB):
        self.tableView.repaint()
        
    @pyqtSlot()
    def delete_selected(self):
        with DisableUpdates(self.tableView):
            for req in self.selected_reqs:
                self.tableModel.delete_request(req=req)

