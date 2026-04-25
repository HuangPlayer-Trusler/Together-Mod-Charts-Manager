MISSING = '---'

COLUMNS = [
    ('关卡名 (ZIP)', 'level_name', 150),
    ('歌曲名称',     'song',       150),
    ('音乐文件名',   'song_filename', 160),
    ('关卡作者',     'author',     120),
    ('艺术家',       'artist',     130),
    ('BPM',          'bpm',         60),
    ('难度',         'difficulty',  55),
    ('标签',         'level_tags', 120),
    ('描述',         'level_desc', 200),
]

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    border: 1px solid #313244;
    gridline-color: #313244;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}
QHeaderView::section {
    background-color: #313244;
    color: #cdd6f4;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #45475a;
    font-weight: bold;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
}
QPushButton:hover   { background-color: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background-color: #585b70; }
QPushButton:disabled { color: #585b70; border-color: #313244; }
QPushButton#exportBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#exportBtn:hover    { background-color: #b4d0fe; }
QPushButton#exportBtn:disabled { background-color: #45475a; color: #7f849c; }
QPushButton#playBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
    min-width: 72px;
}
QPushButton#playBtn:hover    { background-color: #c4f0c0; }
QPushButton#playBtn:disabled { background-color: #45475a; color: #7f849c; }
QPushButton#stopBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
    min-width: 56px;
}
QPushButton#stopBtn:hover    { background-color: #f5a8bb; }
QPushButton#stopBtn:disabled { background-color: #45475a; color: #7f849c; }
QLineEdit, QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 5px 8px;
    color: #cdd6f4;
}
QLineEdit:focus, QComboBox:focus { border-color: #89b4fa; }
QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 6px;
    color: #a6adc8;
    font-size: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QTextEdit {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 5px;
    color: #cdd6f4;
    font-family: "Consolas", monospace;
    font-size: 12px;
}
QSlider::groove:horizontal {
    height: 4px; background: #45475a; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #89b4fa; width: 12px; height: 12px;
    margin: -4px 0; border-radius: 6px;
}
QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 2px; }
QLabel#titleLabel  { color: #89b4fa; font-size: 18px; font-weight: bold; }
QLabel#pathLabel   { color: #a6adc8; font-size: 11px; }
QLabel#statusLabel { color: #a6e3a1; font-size: 12px; }
QLabel#countLabel  { color: #f9e2af; font-size: 12px; }
QLabel#playerLabel { color: #cdd6f4; font-size: 11px; min-width: 70px; }
QProgressDialog    { background-color: #1e1e2e; color: #cdd6f4; }
QScrollBar:vertical { background: #181825; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical {
    background: #45475a; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""