from guppyproxy.util import list_remove, display_error_box
from guppyproxy.proxy import MessageError
from guppyproxy.config import ProxyConfig
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFormLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QSizePolicy, QToolButton, QCheckBox, QLabel, QFileDialog
from PyQt5.QtCore import pyqtSlot, pyqtSignal
import os
import copy


class ListenerList(QTableWidget):
    listenersUpdated = pyqtSignal(list)

    # list part of the listener tab
    def __init__(self, *args, **kwargs):
        QTableWidget.__init__(self, *args, **kwargs)
        self.listeners = []

        # Set up table
        self.setColumnCount(1)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def _add_listener(self, interface, port):
        self.listeners.append((interface, port))

    def add_listener(self, interface, port):
        self.listeners.append((interface, port))
        self.redraw_table()
        self.listenersUpdated.emit(self.listeners[:])

    def set_listeners(self, listeners):
        self.listeners = []
        for interface, port in listeners:
            self._add_listener(interface, port)
        self.redraw_table()
        self.listenersUpdated.emit(copy.deepcopy(self.listeners))

    def _append_row(self, interface, port):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem("%s:%s" % (interface, port)))

    def redraw_table(self):
        self.setRowCount(0)
        for interface, port in self.listeners:
            self._append_row(interface, port)

    @pyqtSlot()
    def delete_selected(self):
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        rownums = [idx.row() for idx in rows]
        self.listeners = list_remove(self.listeners, rownums)
        self.redraw_table()
        self.listenersUpdated.emit(self.listeners[:])

    def clear(self):
        self.listeners = []
        self.redraw_table()
        self.listenersUpdated.emit(self.listeners[:])

    def get_listeners(self):
        return self.listeners[:]


class ListenerWidget(QWidget):
    listenersUpdated = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.listenerlist = ListenerList()
        self.listenerlist.listenersUpdated.connect(self.listenersUpdated)
        self.layout().addWidget(self.listenerlist)

        self.hostinput = QLineEdit()
        self.hostinput.setText("127.0.0.1")
        self.hostinput.returnPressed.connect(self.add_listener)
        self.portinput = QLineEdit()
        self.portinput.setMaxLength(5)
        self.portinput.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.portinput.returnPressed.connect(self.add_listener)
        self.addbutton = QToolButton()
        self.addbutton.setText("+")
        self.removebutton = QToolButton()
        self.removebutton.setText("-")
        editbar = QHBoxLayout()
        editbar.addWidget(self.addbutton)
        editbar.addWidget(self.removebutton)
        editbar.addWidget(QLabel("Interface:"))
        editbar.addWidget(self.hostinput)
        editbar.addWidget(QLabel("Port:"))
        editbar.addWidget(self.portinput)

        self.removebutton.clicked.connect(self.listenerlist.delete_selected)
        self.addbutton.clicked.connect(self.add_listener)

        self.layout().addLayout(editbar)

    @pyqtSlot()
    def add_listener(self):
        host = self.hostinput.text()
        port = self.portinput.text()
        if host == "":
            return
        if port == "":
            return
        try:
            port = int(port)
        except Exception:
            return
        self.listenerlist.add_listener(host, port)
        self.hostinput.setText("127.0.0.1")
        self.portinput.setText("")

    def set_listeners(self, listeners):
        self.listenerlist.set_listeners(listeners)


class DatafileWidget(QWidget):
    datafileLoaded = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.datapath = QLineEdit()
        newbutton = QPushButton("New")
        newbutton.clicked.connect(self.new_datafile)
        browsebutton = QPushButton("Open")
        browsebutton.clicked.connect(self.open_datafile)
        confirmbutton = QPushButton("Go!")
        confirmbutton.clicked.connect(self._load_datafile)
        self.layout().addWidget(self.datapath)
        self.layout().addWidget(newbutton)
        self.layout().addWidget(browsebutton)
        self.layout().addWidget(confirmbutton)

    @pyqtSlot()
    def _load_datafile(self):
        path = self.datapath.text()
        self.datafileLoaded.emit(path)

    @pyqtSlot()
    def new_datafile(self):
        fname, ftype = QFileDialog.getSaveFileName(self, "Save File", os.getcwd(), "Database File (*.gpy)")
        if not fname:
            return
        if len(fname) < 4 and fname[:-4] != ".gpy":
            fname += ".gpy"
        self.datapath.setText(fname)
        self._load_datafile()

    @pyqtSlot()
    def open_datafile(self):
        fname, ftype = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "Any File (*.*)")
        if not fname:
            return
        self.datapath.setText(fname)
        self._load_datafile()


class ProxyInfoWidget(QWidget):
    proxyInfoUpdated = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QFormLayout())

        self.enablebox = QCheckBox()
        self.enablebox.stateChanged.connect(self._enable_cb_statechange)
        self.hostinput = QLineEdit()
        self.portinput = QLineEdit()
        self.credsbox = QCheckBox()
        self.credsbox.stateChanged.connect(self._login_cb_statechange)
        self.credsbox.setCheckState(0)
        self.usernameinput = QLineEdit()
        self.passwordinput = QLineEdit()
        self.passwordinput.setEchoMode(QLineEdit.Password)
        self.socksbox = QCheckBox()
        self.confirmbutton = QPushButton("Confirm")
        self.confirmbutton.clicked.connect(self._confirm_entry)

        self.layout().addRow(QLabel("Use Proxy"), self.enablebox)
        self.layout().addRow(QLabel("Host"), self.hostinput)
        self.layout().addRow(QLabel("Port"), self.portinput)
        self.layout().addRow(QLabel("Use Login"), self.credsbox)
        self.layout().addRow(QLabel("Username"), self.usernameinput)
        self.layout().addRow(QLabel("Password"), self.passwordinput)
        self.layout().addRow(QLabel("Use SOCKS"), self.socksbox)
        self.layout().addRow(QLabel(""), self.confirmbutton)

        self._set_enabled(False)
        self._set_login_enabled(False)

    @pyqtSlot(int)
    def _login_cb_statechange(self, state):
        if state == 0:
            self._set_login_enabled(False)
        else:
            self._set_login_enabled(True)

    @pyqtSlot(int)
    def _enable_cb_statechange(self, state):
        if state == 0:
            self._set_enabled(False)
        else:
            self._set_enabled(True)

    def _set_enabled(self, enabled):
        self.all_enabled = enabled
        self.hostinput.setEnabled(enabled)
        self.portinput.setEnabled(enabled)
        self.credsbox.setEnabled(enabled)
        self.socksbox.setEnabled(enabled)
        if enabled:
            self._set_login_enabled(self.loginenabled)
        else:
            self._set_login_enabled(False)

    def _set_login_enabled(self, enabled):
        self.loginenabled = enabled
        self.usernameinput.setEnabled(enabled)
        self.passwordinput.setEnabled(enabled)

    def _fill_form(self, enabled, host, port, need_creds, username, password, use_socks):
        if enabled:
            self.enablebox.setCheckState(2)
        else:
            self.enablebox.setCheckState(0)
        self.hostinput.setText(host)
        if port == 0:
            self.portinput.setText("")
        else:
            self.portinput.setText(str(port))
        if need_creds:
            self.credsbox.setCheckState(2)
        else:
            self.credsbox.setCheckState(0)
        self.usernameinput.setText(username)
        self.passwordinput.setText(password)
        if use_socks:
            self.socksbox.setCheckState(2)
        else:
            self.socksbox.setCheckState(0)

    def _confirm_entry(self):
        use_proxy = not (self.enablebox.checkState() == 0)
        if use_proxy:
            host = self.hostinput.text()
            port = self.portinput.text()
            try:
                port = int(port)
            except Exception:
                return
            is_socks = not (self.socksbox.checkState() == 0)
            if self.credsbox.checkState() == 0:
                username = ""
                password = ""
            else:
                username = self.usernameinput.text()
                password = self.passwordinput.text()
            entry = {"use_proxy": use_proxy, "host": host, "port": port,
                     "is_socks": is_socks, "username": username, "password": password}
        else:
            entry = {"use_proxy": False, "host": "", "port": 0,
                     "is_socks": False, "username": "", "password": ""}
        self.proxyInfoUpdated.emit(entry)


class SettingsWidget(QWidget):
    datafileLoaded = pyqtSignal()

    def __init__(self, client, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.client = client
        self.setLayout(QFormLayout())

        # Datafile
        self.datafilewidg = DatafileWidget()
        self.datafilewidg.datafileLoaded.connect(self._load_datafile)
        self.layout().addRow(QLabel("Datafile"), self.datafilewidg)

        # Listeners
        self.listenerwidg = ListenerWidget()
        self.listenerwidg.listenersUpdated.connect(self._listeners_updated)
        self.layout().addRow(QLabel("Listeners"), self.listenerwidg)

        # Proxy settings
        self.proxywidg = ProxyInfoWidget()
        self.proxywidg.proxyInfoUpdated.connect(self._set_proxy_settings)
        self.layout().addRow(QLabel("Proxy Settings"), self.proxywidg)

        self.load_config()

    def load_config(self):
        # Load config
        self.config = ProxyConfig()
        try:
            configs = self.client.get_plugin_value(ProxyConfig.PLUGIN_KEY)
        except MessageError:
            configs = self.config.dumps()
            self.client.set_plugin_value(ProxyConfig.PLUGIN_KEY, configs)
        self.config.loads(configs)

        new_listeners = [(vals[0], vals[1]) for vals in self.config.listeners]
        self.listenerwidg.set_listeners(new_listeners)
        # fill proxy
        self.proxywidg._fill_form(self.config.use_proxy,
                                  self.config.proxy_host,
                                  self.config.proxy_port,
                                  not (self.config.proxy_username == "" and self.config.proxy_password == ""),
                                  self.config.proxy_username,
                                  self.config.proxy_password,
                                  self.config.is_socks_proxy)
        self.reload_listeners()

    @pyqtSlot(str)
    def _load_datafile(self, path):
        old_storage = self.client.proxy_storage
        try:
            storage = self.client.add_sqlite_storage(path, "tmpprefix")
        except MessageError as e:
            display_error_box("Could not load datafile:\n%s" % e)
            return
        self.client.close_storage(old_storage)
        self.client.set_storage_prefix(storage.storage_id, "")
        self.client.set_proxy_storage(storage.storage_id)
        self.client.disk_storage = storage
        self.load_config()
        self.datafileLoaded.emit()

    @pyqtSlot(list)
    def _listeners_updated(self, new_listeners):
        old_listensers = self.client.get_listeners()
        parsedold = {}
        for lid, addr in old_listensers:
            iface, port = addr.rsplit(':', 1)
            port = int(port)
            parsedold[(iface, port)] = lid
        oldset = set(parsedold.keys())
        newset = set(new_listeners)
        hosts_to_remove = oldset.difference(new_listeners)
        ids_to_remove = [parsedold[i] for i in hosts_to_remove]
        hosts_to_add = newset.difference(oldset)

        failed_listeners = []
        for i in ids_to_remove:
            self.client.remove_listener(i)
        for iface, port in hosts_to_add:
            try:
                self.client.add_listener(iface, port)
            except MessageError as e:
                err = "%s:%s: %s" % (iface, port, e)
                failed_listeners.append(err)
        if failed_listeners:
            errmsg = "Failed to create listener(s):\n\n%s" % ('\n'.join(failed_listeners))
            display_error_box(errmsg)
        self.config.set_listeners([(host, port, None) for host, port in new_listeners])  # ignore transparent
        self.save_config()

    @pyqtSlot(dict)
    def _set_proxy_settings(self, proxy_data):
        self.config.proxy = proxy_data
        use_creds = (self.config.proxy_username != "" or self.config.proxy_password != "")
        self.client.set_proxy(self.config.use_proxy,
                              self.config.proxy_host,
                              self.config.proxy_port,
                              use_creds,
                              self.config.proxy_username,
                              self.config.proxy_password,
                              self.config.is_socks_proxy)
        self.save_config()

    def reload_listeners(self):
        hosts = self.client.get_listeners()
        pairs = []
        for lid, iface in hosts:
            host, port = iface.rsplit(":", 1)
            pairs.append((host, port))
        self.listenerwidg.blockSignals(True)
        self.listenerwidg.set_listeners(pairs)
        self.listenerwidg.blockSignals(False)

    def save_config(self):
        self.client.set_plugin_value(ProxyConfig.PLUGIN_KEY, self.config.dumps())
