import random

from guppyproxy.reqlist import ReqBrowser, ReqListModel
from guppyproxy.repeater import RepeaterWidget
from guppyproxy.interceptor import InterceptorWidget
from guppyproxy.decoder import DecoderWidget
from guppyproxy.settings import SettingsWidget
from guppyproxy.shortcuts import GuppyShortcuts
from guppyproxy.macros import MacroWidget
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QTableView
from PyQt5.QtCore import Qt


class GuppyWindow(QWidget):
    titles = (
        "Guppy Proxy",
    )

    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        self.initUi()

    def initUi(self):
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

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.addWidget(self.tabWidget)

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

    def close(self):
        self.interceptorWidget.close()
        
