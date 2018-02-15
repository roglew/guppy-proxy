import random

from .reqlist import ReqBrowser
from .repeater import RepeaterWidget
from .interceptor import InterceptorWidget
from .decoder import DecoderWidget
from .settings import SettingsWidget
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from PyQt5.QtCore import Qt


class GuppyWindow(QWidget):
    titles = (
        "Guppy Proxy",
        "Super Hacker Proxy 3000",
        "Proxicado",
        "Proxy Attack Proxy ProxY",
        "Slurp Bruite",
        "Pappy",
        "Sports.exe",
        "Gappy",
        "Mickosoft Accel",
        "Microsoft Word '98",
    )

    def __init__(self, client):
        QWidget.__init__(self)
        self.client = client
        self.initUi()

    def initUi(self):
        self.setFocusPolicy(Qt.StrongFocus)
        tabWidget = QTabWidget()
        repeaterWidget = RepeaterWidget(self.client)
        self.interceptorWidget = InterceptorWidget(self.client)
        historyWidget = ReqBrowser(self.client, repeater_widget=repeaterWidget)
        decoderWidget = DecoderWidget()
        settingsWidget = SettingsWidget(self.client)
        settingsWidget.datafileLoaded.connect(historyWidget.reset_to_scope)

        tabWidget.addTab(historyWidget, "History")
        tabWidget.addTab(repeaterWidget, "Repeater")
        tabWidget.addTab(self.interceptorWidget, "Interceptor")
        tabWidget.addTab(decoderWidget, "Decoder")
        tabWidget.addTab(settingsWidget, "Settings")

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(tabWidget)

        self.setWindowTitle(random.choice(GuppyWindow.titles))
        self.show()

    def close(self):
        self.interceptorWidget.close()
