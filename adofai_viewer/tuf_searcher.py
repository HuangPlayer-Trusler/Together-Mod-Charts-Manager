# tuf_searcher.py
import sys
import urllib.parse
from PyQt5.QtCore import QThread, pyqtSignal, QEventLoop, QUrl
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest


TUF_SEARCH_URL = "https://api.tuforums.com/v2/database/levels"
TUF_LEVEL_URL  = "https://tuforums.com/levels/{}"


def build_query(level) -> str:
    """
    根据关卡信息构建 TUF 搜索 query 字符串。
    - 使用 song_pure, artist_pure 纯文本
    - 将作者字段按 & 或 | 拆分为多个 creator 条件
    """
    # 延迟导入，避免循环依赖
    from .level_info import LevelInfo

    parts = []
    song = level.song_pure
    artist = level.artist_pure
    author_str = level.author_pure

    if song:
        parts.append(f"song:{song}")
    if artist:
        parts.append(f"artist:{artist}")
    if author_str:
        creators = LevelInfo._split_creators(author_str)
        for c in creators:
            parts.append(f"creator:{c}")

    return ",".join(parts) if parts else ""


class TufSearchThread(QThread):
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        # 保留 : 和 , 不被编码
        encoded = urllib.parse.quote(self.query, safe=':,')
        url = f"{TUF_SEARCH_URL}?query={encoded}"
        print(f"TUF 查询链接：{url}")

        self._nam = QNetworkAccessManager()
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json")

        reply = self._nam.get(request)
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()

        if reply.error() != 0:
            self.error.emit(reply.errorString())
            return

        data = reply.readAll().data().decode('utf-8')
        try:
            import json
            obj = json.loads(data)
            results = obj.get("results", [])
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class TufResultDialog(QDialog):
    """展示多个 TUF 搜索结果，用户可选择跳转。"""

    def __init__(self, results: list, song_name: str, parent=None):
        super().__init__(parent)
        self.selected_id = None
        self.setWindowTitle(f"TUF 搜索结果 - {song_name}")
        self.setMinimumSize(600, 400)
        self.setObjectName("tufResultDialog")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"找到 {len(results)} 个匹配关卡，请选择："))
        layout.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("tufScroll")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignTop)

        for r in results:
            card = self._build_card(r)
            scroll_layout.addWidget(card)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _build_card(self, result: dict) -> QWidget:
        card = QWidget()
        card.setObjectName("tufCard")
        card.setMaximumHeight(90)

        hbox = QHBoxLayout(card)
        hbox.setContentsMargins(8, 6, 8, 6)
        hbox.setSpacing(10)

        # 难度图标
        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setScaledContents(True)
        diff = result.get("difficulty", {})
        icon_url = diff.get("icon", "") if diff else ""
        if icon_url:
            self._load_icon(icon_url, icon_label)
        else:
            icon_label.setText("?")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size:20px; color:#585b70;")
        hbox.addWidget(icon_label)

        # 文字信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        song = result.get("song", "???")
        artist = result.get("artist", "???")
        creator = result.get("creator", "???")
        bpm = result.get("bpm", "?")
        tiles = result.get("tilecount", "?")
        diff_name = diff.get("name", "?") if diff else "?"

        info_layout.addWidget(QLabel(f"<b style='color:#89b4fa'>{song}</b>"))
        info_layout.addWidget(QLabel(f"艺术家: {artist}  |  作者: {creator}"))
        info_layout.addWidget(QLabel(f"BPM: {bpm}  |  方块: {tiles}  |  难度: {diff_name}"))

        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        hbox.addWidget(info_widget, 1)

        level_id = result.get("id")
        btn = QPushButton("跳转")
        btn.setFixedWidth(50)
        btn.clicked.connect(lambda _, lid=level_id: self._open_level(lid))
        hbox.addWidget(btn)

        return card

    @staticmethod
    def _load_icon(url: str, label: QLabel):
        import urllib.request
        import threading

        def download():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=10).read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    label.setPixmap(pixmap)
            except Exception:
                pass

        threading.Thread(target=download, daemon=True).start()

    def _open_level(self, level_id: int):
        import webbrowser
        webbrowser.open(TUF_LEVEL_URL.format(level_id))
        self.accept()