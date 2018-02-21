from .util import display_info_box, paste_clipboard
from PyQt5.QtCore import pyqtSlot, QObject, Qt
from PyQt5.QtWidgets import QShortcut 
from PyQt5.QtGui import QKeySequence

class GuppyShortcuts(QObject):
    
    ACT_NAV_FILTER_TEXT = 0
    ACT_NAV_FILTER_DROPDOWN = 1
    ACT_NAV_HISTORY = 2
    ACT_NAV_TREE = 3
    ACT_NAV_REPEATER = 4
    ACT_NAV_INTERCEPTOR = 5
    ACT_NAV_DECODER = 6
    ACT_NAV_DECODER_PASTE = 7
    ACT_NAV_FILTER_POP = 8
    ACT_OPEN = 9
    ACT_NEW = 10

    def __init__(self, guppy_window):
        QObject.__init__(self)
        self.guppy_window = guppy_window
        self.combos = {}

        self.add_shortcut(self.ACT_NAV_FILTER_TEXT,
                          "Navigate to filter text input",
                          self.nav_to_filter_text,
                          QKeySequence(Qt.CTRL+Qt.Key_U))

        self.add_shortcut(self.ACT_NAV_FILTER_DROPDOWN,
                          "Navigate to filter dropdown input",
                          self.nav_to_filter_dropdown,
                          QKeySequence(Qt.CTRL+Qt.Key_I))

        self.add_shortcut(self.ACT_NAV_FILTER_POP,
                          "Navigate to filters and pop most recent filter",
                          self.nav_to_filter_pop,
                          QKeySequence(Qt.CTRL+Qt.Key_P))

        self.add_shortcut(self.ACT_NAV_HISTORY,
                          "Navigate to request list",
                          self.nav_to_history,
                          QKeySequence(Qt.CTRL+Qt.Key_J))

        self.add_shortcut(self.ACT_NAV_TREE,
                          "Navigate to tree view",
                          self.nav_to_tree,
                          QKeySequence(Qt.CTRL+Qt.Key_T))

        self.add_shortcut(self.ACT_NAV_REPEATER,
                          "Navigate to repeater",
                          self.nav_to_repeater,
                          QKeySequence(Qt.CTRL+Qt.Key_R))

        self.add_shortcut(self.ACT_NAV_INTERCEPTOR,
                          "Navigate to interceptor",
                          self.nav_to_interceptor,
                          QKeySequence(Qt.CTRL+Qt.Key_E))

        self.add_shortcut(self.ACT_NAV_DECODER,
                          "Navigate to decoder",
                          self.nav_to_decoder,
                          QKeySequence(Qt.CTRL+Qt.Key_D))

        self.add_shortcut(self.ACT_NAV_DECODER_PASTE,
                          "Navigate to decoder and fill with clipboard",
                          self.nav_to_decoder_and_paste,
                          QKeySequence(Qt.CTRL+Qt.SHIFT+Qt.Key_D))

        self.add_shortcut(self.ACT_OPEN,
                          "Open datafile",
                          self.open_datafile,
                          QKeySequence(Qt.CTRL+Qt.SHIFT+Qt.Key_O))

        self.add_shortcut(self.ACT_NEW,
                          "New datafile",
                          self.new_datafile,
                          QKeySequence(Qt.CTRL+Qt.SHIFT+Qt.Key_N))


    def add_shortcut(self, action, desc, func, key=None):
        sc = QShortcut(self.guppy_window)
        self.combos[action] = (sc, desc)
        sc.activated.connect(func)
        if key:
            sc.setKey(key)

    def set_key(self, action, key):
        sc = self.combos[action][0]
        sc.setKey(key)

    def get_desc(self, action):
        return self.combos[action][1]
        
    @pyqtSlot()
    def nav_to_filter_text(self):
        self.guppy_window.show_hist_tab()
        self.guppy_window.historyWidget.show_filters()
        self.guppy_window.historyWidget.set_filter_is_text(True)
        self.guppy_window.historyWidget.filterWidg.entry.text_entry.textEntry.setFocus()

    @pyqtSlot()
    def nav_to_filter_dropdown(self):
        self.guppy_window.show_hist_tab()
        self.guppy_window.historyWidget.show_filters()
        self.guppy_window.historyWidget.set_filter_is_text(False)

    @pyqtSlot()
    def nav_to_filter_pop(self):
        self.guppy_window.show_hist_tab()
        self.guppy_window.historyWidget.show_filters()
        self.guppy_window.historyWidget.filterWidg.pop_phrase()

    @pyqtSlot()
    def nav_to_history(self):
        self.guppy_window.show_hist_tab()
        self.guppy_window.historyWidget.show_history()

    @pyqtSlot()
    def nav_to_tree(self):
        self.guppy_window.show_hist_tab()
        self.guppy_window.historyWidget.show_tree()

    @pyqtSlot()
    def nav_to_repeater(self):
        self.guppy_window.show_repeater_tab()

    @pyqtSlot()
    def nav_to_interceptor(self):
        self.guppy_window.show_interceptor_tab()

    @pyqtSlot()
    def nav_to_decoder(self):
        self.guppy_window.show_decoder_tab()

    @pyqtSlot()
    def nav_to_decoder_and_paste(self):
        self.guppy_window.show_decoder_tab()
        text = paste_clipboard()
        self.guppy_window.decoderWidget.decoder_input.editor.set_bytes(text.encode())

    @pyqtSlot()
    def open_datafile(self):
        self.guppy_window.settingsWidget.datafilewidg.open_datafile()
        
    @pyqtSlot()
    def new_datafile(self):
        self.guppy_window.settingsWidget.datafilewidg.new_datafile()
