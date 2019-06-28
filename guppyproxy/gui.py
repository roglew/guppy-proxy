import random

from guppyproxy.reqlist import ReqBrowser, ReqListModel
from guppyproxy.repeater import RepeaterWidget
from guppyproxy.interceptor import InterceptorWidget
from guppyproxy.decoder import DecoderWidget
from guppyproxy.settings import SettingsWidget
from guppyproxy.shortcuts import GuppyShortcuts
from guppyproxy.macros import MacroWidget
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QTableView
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSlot


class GuppyWindow(QWidget):
    titles = (
        "Guppy Proxy",
    )

    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        
        self.delayTimeout = 100
        self._resizeTimer = QTimer(self)
        self._resizeTimer.timeout.connect(self._delayedUpdate)
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.shortcuts = GuppyShortcuts(self)
        self.tabWidget = QTabWidget()
        self.repeaterWidget = RepeaterWidget(self.client)
        self.interceptorWidget = InterceptorWidget(self.client)
        self.macroWidget = MacroWidget(self.client)
        self.historyWidget = ReqBrowser(self.client,
                                        repeater_widget=self.repeaterWidget,
                                        macro_widget=self.macroWidget,
                                        is_client_context=True,
                                        update=True)
        self.decoderWidget = DecoderWidget()
        self.settingsWidget = SettingsWidget(self.client)

        self.settingsWidget.datafileLoaded.connect(self.historyWidget.reset_to_scope)
        
        self.history_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.historyWidget, "History")
        self.repeater_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.repeaterWidget, "Repeater")
        self.interceptor_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.interceptorWidget, "Interceptor")
        self.decoder_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.decoderWidget, "Decoder")
        self.macro_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.macroWidget, "Macros")
        self.settings_ind = self.tabWidget.count()
        self.tabWidget.addTab(self.settingsWidget, "Settings")

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.tabWidget)
        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.mainLayout)
        
        self.wrapperLayout = QVBoxLayout()
        self.wrapperLayout.addWidget(self.mainWidget)
        self.wrapperLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.wrapperLayout)

        self.setWindowTitle(random.choice(GuppyWindow.titles))
        self.show()
        
    def show_hist_tab(self):
        self.tabWidget.setCurrentIndex(self.history_ind)

    def show_repeater_tab(self):
        self.tabWidget.setCurrentIndex(self.repeater_ind)
        
    def show_interceptor_tab(self):
        self.tabWidget.setCurrentIndex(self.interceptor_ind)

    def show_decoder_tab(self):
        self.tabWidget.setCurrentIndex(self.decoder_ind)
        
    def show_active_macro_tab(self):
        self.tabWidget.setCurrentIndex(self.macro_ind)
        self.macroWidget.show_active()

    def show_int_macro_tab(self):
        self.tabWidget.setCurrentIndex(self.macro_ind)
        self.macroWidget.show_int()
        
    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        self._resizeTimer.stop()
        self._resizeTimer.start(self.delayTimeout)
        self.mainWidget.setVisible(False)

    @pyqtSlot()
    def _delayedUpdate(self):
        self._resizeTimer.stop()
        self.mainWidget.setVisible(True)

    def close(self):
        self.interceptorWidget.close()
        
