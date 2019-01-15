from guppyproxy.proxy import HTTPRequest
from PyQt5.QtWidgets import QWidget, QTreeView, QVBoxLayout
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import pyqtSlot, Qt


def _include_req(req):
    if not req.response:
        return False
    if req.response.status_code == 404:
        return False
    return True


class PathNodeItem(QStandardItem):

    def __init__(self, text, *args, **kwargs):
        QStandardItem.__init__(self, *args, **kwargs)
        self.text = text
        self.children = {}

    def add_child(self, text):
        if text not in self.children:
            newitem = PathNodeItem(text, text)
            newitem.setFlags(newitem.flags() ^ Qt.ItemIsEditable)
            self.children[text] = newitem
            self.appendRow(newitem)

    def get_child(self, text):
        return self.children[text]

    def add_child_path(self, texts):
        if not texts:
            return
        childtext = texts[0]
        self.add_child(childtext)
        child = self.get_child(childtext)
        child.add_child_path(texts[1:])


class ReqTreeView(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.nodes = {}
        self.tree_view = QTreeView()
        self.tree_view.header().close()
        self.root = QStandardItemModel()
        self.tree_view.setModel(self.root)
        self.layout().addWidget(self.tree_view)

    @pyqtSlot(HTTPRequest)
    def add_request_item(self, req):
        path_parts = req.url.geturl(False).split("/")
        path_parts = path_parts[1:]
        path_parts = ["/" + p for p in path_parts]
        path_parts = [req.dest_host] + path_parts
        if path_parts[0] not in self.nodes:
            item = PathNodeItem(path_parts[0], path_parts[0])
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.nodes[path_parts[0]] = item
            self.root.appendRow(item)
        else:
            item = self.nodes[path_parts[0]]
        item.add_child_path(path_parts[1:])

    @pyqtSlot(list)
    def set_requests(self, reqs):
        self.clear()
        for req in reqs:
            if _include_req(req):
                self.add_request_item(req)
        self.tree_view.expandAll()

    def clear(self):
        self.nodes = {}
        self.root = QStandardItemModel()
        self.tree_view.setModel(self.root)
