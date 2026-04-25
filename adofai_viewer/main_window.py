import sys
import os
import time
import re
import shutil
import tempfile

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QProgressDialog, QAbstractItemView,
    QLineEdit, QComboBox, QSplitter, QTextEdit, QGroupBox,
    QSlider, QSizePolicy, QDialog, QApplication   # ← 添加 QDialog, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QPalette

import pygame

from .constants import COLUMNS, DARK_STYLE, MISSING
from .load_thread import LoadThread
from .level_info import LevelInfo
from .edit_dialog import EditLevelDialog
from .utils import color_tags_to_html, sanitize_filename
from .settings_parser import parse_adofai_settings
from .tuf_searcher import TufSearchThread, TufResultDialog, build_query

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Together Mod Charts Manager')
        self.setMinimumSize(1100, 700)
        self.resize(1300, 820)

        # 临时解压路径设置在程序所在目录
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = os.path.join(app_dir, 'adofai_viewer_cache')
        os.makedirs(self.temp_dir, exist_ok=True)

        self.levels: list[LevelInfo] = []
        self._load_thread = None
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filter)

        # pygame 音频系统（延迟初始化）
        self._mixer_ready = False
        self._music_loaded = False
        self._music_state = 'stopped'
        self._music_duration_ms = 0
        self._seek_pos_ms = 0
        self._play_start_time = 0.0
        self._play_start_offset = 0.0
        self._pause_pos_sec = 0.0
        self._slider_dragging = False

        self._progress_timer = QTimer()
        self._progress_timer.timeout.connect(self._on_progress_timer)
        self._progress_timer.start(200)

        self.setStyleSheet(DARK_STYLE)
        self._build_ui()

    def _ensure_mixer(self) -> bool:
        if self._mixer_ready:
            return True
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            self._mixer_ready = True
            return True
        except pygame.error as e:
            QMessageBox.warning(self, '音频错误', f'无法初始化音频设备：{e}')
            return False

    # ── UI 构建 ──
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(14, 12, 14, 8)

        # 标题行
        title_row = QHBoxLayout()
        title_lbl = QLabel('Together Mod Charts Manager')
        title_lbl.setObjectName('titleLabel')
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        ver_lbl = QLabel('Trusler & Gemini Pro - v1.01')
        ver_lbl.setObjectName('pathLabel')
        title_row.addWidget(ver_lbl)
        root.addLayout(title_row)

        # 路径配置
        path_group = QGroupBox('路径配置')
        path_layout = QVBoxLayout(path_group)
        path_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('关卡文件夹：'))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText('选择包含 .zip 关卡包的文件夹...')
        self.folder_edit.setReadOnly(True)
        row1.addWidget(self.folder_edit, 1)
        btn_folder = QPushButton('浏览')
        btn_folder.clicked.connect(self.select_folder)
        row1.addWidget(btn_folder)
        path_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('临时解压路径：'))
        self.temp_edit = QLineEdit(self.temp_dir)
        self.temp_edit.setReadOnly(True)
        row2.addWidget(self.temp_edit, 1)
        btn_temp = QPushButton('浏览')
        btn_temp.clicked.connect(self.select_temp_dir)
        row2.addWidget(btn_temp)
        btn_clean = QPushButton('清理缓存')
        btn_clean.clicked.connect(self.clean_temp)
        row2.addWidget(btn_clean)
        path_layout.addLayout(row2)

        root.addWidget(path_group)

        # 搜索行
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel('搜索：'))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('关卡名、歌曲、作者、艺术家...')
        self.search_edit.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(QLabel('列：'))
        self.filter_col = QComboBox()
        self.filter_col.addItems(['全部', '关卡名', '歌曲名称', '关卡作者', '艺术家', '标签'])
        self.filter_col.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_col)
        btn_clr = QPushButton('X')
        btn_clr.setFixedWidth(32)
        btn_clr.clicked.connect(lambda: self.search_edit.clear())
        filter_row.addWidget(btn_clr)
        root.addLayout(filter_row)

        # 表格 + 详情
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            self.table.setColumnWidth(i, w)
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_table_double_click)
        splitter.addWidget(self.table)

        detail_widget = QWidget()
        detail_widget.setMinimumWidth(260)
        detail_widget.setMaximumWidth(340)
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_group = QGroupBox('关卡详情')
        detail_inner = QVBoxLayout(detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText('在左侧选择一个关卡以查看详情...')
        detail_inner.addWidget(self.detail_text)
        detail_layout.addWidget(detail_group)
        splitter.addWidget(detail_widget)
        splitter.setSizes([860, 300])
        root.addWidget(splitter, 1)

        # 音乐播放条
        player_group = QGroupBox('音乐播放')
        player_inner = QVBoxLayout(player_group)
        player_inner.setSpacing(4)
        player_inner.setContentsMargins(8, 4, 8, 6)

        self.player_file_label = QLabel('未选择音乐文件')
        self.player_file_label.setObjectName('pathLabel')
        self.player_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        player_inner.addWidget(self.player_file_label)

        ctrl_row = QHBoxLayout()
        self.play_btn = QPushButton('播放')
        self.play_btn.setObjectName('playBtn')
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton('停止')
        self.stop_btn.setObjectName('stopBtn')
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_music)
        ctrl_row.addWidget(self.stop_btn)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, '_slider_dragging', True))
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        ctrl_row.addWidget(self.seek_slider, 1)

        self.time_label = QLabel('0:00 / 0:00')
        self.time_label.setObjectName('playerLabel')
        ctrl_row.addWidget(self.time_label)

        player_inner.addLayout(ctrl_row)
        root.addWidget(player_group)

        # 底部操作栏
        bottom = QHBoxLayout()
        self.total_label = QLabel('共 0 个关卡')
        self.total_label.setObjectName('statusLabel')
        bottom.addWidget(self.total_label)
        bottom.addSpacing(12)
        self.filtered_label = QLabel('')
        self.filtered_label.setObjectName('pathLabel')
        bottom.addWidget(self.filtered_label)
        bottom.addStretch()
        self.edit_btn = QPushButton('编辑信息')
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_selected_level)
        bottom.addWidget(self.edit_btn)
        bottom.addSpacing(12)
        # 编辑信息按钮
        self.edit_btn = QPushButton('编辑信息')
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_selected_level)
        bottom.addWidget(self.edit_btn)

        # 新增：TUF 查找按钮
        self.tuf_btn = QPushButton('TUF 查找')
        self.tuf_btn.setEnabled(False)
        self.tuf_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ddbcfc; }
            QPushButton:disabled { background-color: #45475a; color: #7f849c; }
        """)
        self.tuf_btn.clicked.connect(self.tuf_search)
        bottom.addWidget(self.tuf_btn)

        bottom.addSpacing(12)
        self.count_label = QLabel('已选择：0 个')
        self.count_label = QLabel('已选择：0 个')
        self.count_label.setObjectName('countLabel')
        bottom.addWidget(self.count_label)
        btn_all = QPushButton('全选')
        btn_all.setFixedWidth(60)
        btn_all.clicked.connect(self.table.selectAll)
        bottom.addWidget(btn_all)
        btn_none = QPushButton('取消')
        btn_none.setFixedWidth(60)
        btn_none.clicked.connect(self.table.clearSelection)
        bottom.addWidget(btn_none)
        bottom.addSpacing(8)
        self.export_btn = QPushButton('导出选中关卡')
        self.export_btn.setObjectName('exportBtn')
        self.export_btn.setMinimumWidth(120)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_levels)
        bottom.addWidget(self.export_btn)
        root.addLayout(bottom)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet('color: #a6adc8; font-size: 12px;')
        self.status_bar.showMessage('就绪 — 请选择包含 .zip 关卡包的文件夹')

    # ── 路径操作 ──
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择 ADOFAI 关卡文件夹')
        if not folder:
            return
        self.folder_edit.setText(folder)
        self._load_levels(folder)

    def select_temp_dir(self):
        path = QFileDialog.getExistingDirectory(self, '选择临时解压路径', self.temp_dir)
        if path:
            self.temp_dir = path
            self.temp_edit.setText(path)
            os.makedirs(path, exist_ok=True)

    def clean_temp(self):
        reply = QMessageBox.question(
            self, '清理缓存',
            f'将删除临时解压目录中的所有内容：\n{self.temp_dir}\n\n确定继续吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
                self.status_bar.showMessage('缓存已清理')
            except Exception as e:
                QMessageBox.warning(self, '清理失败', str(e))

    # ── 加载关卡 ──
    def _load_levels(self, folder: str):
        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.cancel()
            self._load_thread.wait()

        zip_files = [f for f in os.listdir(folder) if f.lower().endswith('.zip')]
        if not zip_files:
            QMessageBox.information(self, '提示', f'所选文件夹中未找到 .zip 文件：\n{folder}')
            return

        self.stop_music()
        self.table.setRowCount(0)
        self.levels.clear()
        self.total_label.setText('正在加载...')
        self.export_btn.setEnabled(False)

        self._progress = QProgressDialog('正在读取关卡...', '取消', 0, len(zip_files), self)
        self._progress.setWindowTitle('加载中')
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setMinimumDuration(300)

        self._load_thread = LoadThread(folder, self.temp_dir)
        self._load_thread.progress.connect(self._on_load_progress)
        self._load_thread.level_loaded.connect(self._on_level_loaded)
        self._load_thread.finished_signal.connect(self._on_load_finished)
        self._progress.canceled.connect(self._load_thread.cancel)
        self._load_thread.start()

    def _on_load_progress(self, current, total, msg):
        self._progress.setValue(current)
        self._progress.setLabelText(msg)
        self.status_bar.showMessage(msg)

    def _on_level_loaded(self, level: LevelInfo):
        self.levels.append(level)
        self._add_table_row(level)
        self.total_label.setText(f'共 {len(self.levels)} 个关卡')

    def _on_load_finished(self, loaded, total):
        self._progress.close()
        self.total_label.setText(f'共 {loaded} 个关卡（{total} 个 ZIP）')
        self.status_bar.showMessage(f'加载完成：{loaded}/{total} 个关卡成功读取')
        self.table.setSortingEnabled(True)
        self._apply_filter()

    def _add_table_row(self, level: LevelInfo):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            level.level_name, level.song, level.song_filename,
            level.author, level.artist, level.bpm,
            level.difficulty, level.level_tags, level.level_desc
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setToolTip(val)
            if col == 0:
                item.setData(Qt.UserRole, len(self.levels) - 1)
            if val == MISSING:
                item.setForeground(QColor('#585b70'))
            self.table.setItem(row, col, item)

    # ── 搜索 & 筛选 ──
    def _on_search_changed(self):
        self._search_timer.start(250)

    def _apply_filter(self):
        keyword = self.search_edit.text().strip().lower()
        col_idx = self.filter_col.currentIndex()
        # 列映射：关卡名0，歌曲名称1，关卡作者3，艺术家4，标签7
        col_map = {1: 0, 2: 1, 3: 3, 4: 4, 5: 7}
        visible = 0
        for row in range(self.table.rowCount()):
            if not keyword:
                self.table.setRowHidden(row, False)
                visible += 1
                continue
            if col_idx == 0:
                match = any(
                    self.table.item(row, c) and keyword in self.table.item(row, c).text().lower()
                    for c in range(self.table.columnCount())
                )
            else:
                target = col_map.get(col_idx, 0)
                item = self.table.item(row, target)
                match = bool(item and keyword in item.text().lower())
            self.table.setRowHidden(row, not match)
            if match:
                visible += 1
        self.filtered_label.setText(f'（筛选后：{visible} 个）' if keyword else '')

    # ── 选择 & 详情 ──
    def _on_selection_changed(self):
        rows = self._selected_rows()
        self.count_label.setText(f'已选择：{len(rows)} 个')
        self.export_btn.setEnabled(len(rows) > 0)
        self.edit_btn.setEnabled(len(rows) == 1)
        self.tuf_btn.setEnabled(len(rows) == 1)

        if len(rows) == 1:
            idx = self._row_to_level_index(rows[0])
            if idx is not None:
                level = self.levels[idx]
                self._show_level_detail(level)
                self._load_music(level)
        else:
            self.detail_text.clear()
            self.stop_music()

    def _selected_rows(self):
        return list(set(
            idx.row() for idx in self.table.selectedIndexes()
            if not self.table.isRowHidden(idx.row())
        ))

    def _row_to_level_index(self, row):
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_table_double_click(self, index):
        idx = self._row_to_level_index(index.row())
        if idx is not None:
            self._show_level_detail(self.levels[idx])

    def _show_level_detail(self, level: LevelInfo):
        def field_html(label: str, raw: str) -> str:
            if raw == MISSING:
                val_html = '<span style="color:#585b70">---</span>'
            else:
                val_html = color_tags_to_html(raw)
            return f'<p style="margin:5px 0"><b style="color:#89b4fa">{label}</b><br>{val_html}</p>'

        music_info = (
            os.path.basename(level.music_path)
            if level.music_path
            else f'<span style="color:#f38ba8">未找到：{level.song_filename}</span>'
        )

        sections = [
            field_html('关卡名 (ZIP)', level.level_name),
            field_html('歌曲名称', level._song_raw),
            field_html('关卡作者', level._author_raw),
            field_html('艺术家', level._artist_raw),
            f'<p style="margin:5px 0"><b style="color:#89b4fa">BPM</b><br>{level.bpm}</p>',
            f'<p style="margin:5px 0"><b style="color:#89b4fa">难度</b><br>{level.difficulty}</p>',
            field_html('标签', level.level_tags),
            field_html('描述', level.level_desc),
            (f'<p style="margin:5px 0"><b style="color:#a6adc8">音乐文件</b><br>'
             f'<span style="color:#a6e3a1;font-size:11px">{music_info}</span></p>'),
            (f'<p style="margin:5px 0"><b style="color:#a6adc8">导出文件夹名</b><br>'
             f'<span style="color:#f9e2af">{level.export_folder_name()}</span></p>'),
            (f'<p style="margin:5px 0">'
             f'<span style="color:#585b70;font-size:10px">ZIP: {os.path.basename(level.zip_path)}</span><br>'
             f'<span style="color:#585b70;font-size:10px">解压: {level.extracted_path}</span></p>'),
        ]
        sep = '<hr style="border:none;border-top:1px solid #313244;margin:2px 0">'
        html = '<div style="line-height:1.5;padding:4px;font-size:12px">' + sep.join(sections) + '</div>'
        self.detail_text.setHtml(html)

    # ── 编辑关卡 ──
    def edit_selected_level(self):
        rows = self._selected_rows()
        if len(rows) != 1:
            return
        idx = self._row_to_level_index(rows[0])
        if idx is None:
            return
        level = self.levels[idx]
        dialog = EditLevelDialog(level, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        new_vals = dialog.get_values()
        for field, value in new_vals.items():
            level.apply_edit(field, value)

        row = rows[0]
        self._update_table_row(row, level)
        self._show_level_detail(level)

    def _update_table_row(self, row: int, level: LevelInfo):
        values = [
            level.level_name, level.song, level.song_filename,
            level.author, level.artist, level.bpm,
            level.difficulty, level.level_tags, level.level_desc
        ]
        for col, val in enumerate(values):
            item = self.table.item(row, col)
            if item:
                item.setText(val)
                if val == MISSING:
                    item.setForeground(QColor('#585b70'))
                else:
                    item.setForeground(QColor('#cdd6f4'))

        name_item = self.table.item(row, 0)
        if name_item:
            txt = level.level_name
            if level.display_edited:
                if not txt.startswith('*'):
                    txt = '*' + txt
            else:
                txt = txt.lstrip('*')
            name_item.setText(txt)

    # ── 音乐播放 ──
    def _load_music(self, level: LevelInfo):
        if not self._ensure_mixer():
            return
        self.stop_music()
        self._playing_level = level

        if not level.music_path:
            fname = level.song_filename if level.song_filename != MISSING else '无音乐文件'
            self.player_file_label.setText(f'未找到：{fname}')
            self.play_btn.setEnabled(False)
            self.seek_slider.setRange(0, 0)
            self._music_loaded = False
            return

        try:
            pygame.mixer.music.load(level.music_path)
            self._music_loaded = True
            self._music_state = 'stopped'
            self._seek_pos_ms = 0
            self._play_start_time = 0.0
            self._play_start_offset = 0.0
            self._pause_pos_sec = 0.0
            self.player_file_label.setText(os.path.basename(level.music_path))
            self.play_btn.setEnabled(True)
            sound = pygame.mixer.Sound(level.music_path)
            self._music_duration_ms = int(sound.get_length() * 1000)
            self.seek_slider.setRange(0, self._music_duration_ms)
            self.time_label.setText(f'0:00 / {self._fmt_ms(self._music_duration_ms)}')
        except pygame.error as e:
            self.player_file_label.setText(f'无法加载：{e}')
            self.play_btn.setEnabled(False)
            self._music_loaded = False

    def toggle_play(self):
        if not self._music_loaded:
            return
        if self._music_state == 'playing':
            pygame.mixer.music.pause()
            self._music_state = 'paused'
            elapsed = time.time() - self._play_start_time
            self._pause_pos_sec = self._play_start_offset + elapsed
        elif self._music_state == 'paused':
            start_sec = self._pause_pos_sec
            pygame.mixer.music.play(start=start_sec)
            self._play_start_time = time.time()
            self._play_start_offset = start_sec
            self._music_state = 'playing'
        else:  # stopped
            start_sec = self._seek_pos_ms / 1000.0
            pygame.mixer.music.play(start=start_sec)
            self._play_start_time = time.time()
            self._play_start_offset = start_sec
            self._music_state = 'playing'
            self._seek_pos_ms = 0

    def stop_music(self):
        if self._mixer_ready:
            pygame.mixer.music.stop()
        # 保留 _music_loaded = True，允许再次点击播放
        self._playing_level = None          # 仅清除引用，不影响播放器状态
        self._music_state = 'stopped'
        self._seek_pos_ms = 0
        self._play_start_time = 0.0
        self._play_start_offset = 0.0
        self._pause_pos_sec = 0.0
        self.play_btn.setText('播放')
        self.stop_btn.setEnabled(False)
        self.seek_slider.setValue(0)
        # 保留时长范围，便于查看总时长
        self.time_label.setText(f'0:00 / {self._fmt_ms(self._music_duration_ms)}')

    def _on_progress_timer(self):
        if not self._music_loaded:
            return
        # 检测播放结束
        if self._music_state == 'playing' and not pygame.mixer.music.get_busy():
            self.stop_music()
            return

        if self._music_state == 'playing':
            elapsed = time.time() - self._play_start_time
            pos_sec = self._play_start_offset + elapsed
            pos_ms = int(pos_sec * 1000)
            if not self._slider_dragging:
                self.seek_slider.setValue(pos_ms)
            self.time_label.setText(f'{self._fmt_ms(pos_ms)} / {self._fmt_ms(self._music_duration_ms)}')
            self.play_btn.setText('暂停')
            self.stop_btn.setEnabled(True)
        elif self._music_state == 'paused':
            self.play_btn.setText('继续')
            self.stop_btn.setEnabled(True)
        else:
            self.play_btn.setText('播放')
            self.stop_btn.setEnabled(False)

    def _on_slider_released(self):
        self._slider_dragging = False
        if not self._music_loaded:
            return
        pos_ms = self.seek_slider.value()
        pos_s = pos_ms / 1000.0
        if self._music_state == 'playing':
            pygame.mixer.music.play(start=pos_s)
            self._play_start_time = time.time()
            self._play_start_offset = pos_s
        elif self._music_state == 'paused':
            pygame.mixer.music.play(start=pos_s)
            pygame.mixer.music.pause()
            self._pause_pos_sec = pos_s
            self._play_start_time = time.time()
            self._play_start_offset = pos_s
        else:  # stopped
            self._seek_pos_ms = pos_ms
            self.seek_slider.setValue(pos_ms)
            self.time_label.setText(f'{self._fmt_ms(pos_ms)} / {self._fmt_ms(self._music_duration_ms)}')

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        s = ms // 1000
        return f'{s // 60}:{s % 60:02d}'

    # ── 导出（应用编辑） ──
    def export_levels(self):
        rows = self._selected_rows()
        if not rows:
            return

        export_dir = QFileDialog.getExistingDirectory(self, '选择导出目标文件夹')
        if not export_dir:
            return

        to_export: list[LevelInfo] = []
        for row in rows:
            idx = self._row_to_level_index(row)
            if idx is not None:
                to_export.append(self.levels[idx])

        progress = QProgressDialog('正在导出...', '取消', 0, len(to_export), self)
        progress.setWindowTitle('导出中')
        progress.setWindowModality(Qt.WindowModal)

        exported, errors = [], []
        for i, level in enumerate(to_export):
            progress.setValue(i)
            if progress.wasCanceled():
                break

            folder_name = level.export_folder_name()
            dest = os.path.join(export_dir, folder_name)
            if os.path.exists(dest):
                base, n = dest, 1
                while os.path.exists(dest):
                    dest = f'{base}_{n}'
                    n += 1

            progress.setLabelText(f'正在导出：{folder_name}')
            QApplication.processEvents()

            try:
                shutil.copytree(level.extracted_path, dest)

                if level.display_edited:
                    self._apply_edits_to_adofai(dest, level)

                exported.append(folder_name)
            except Exception as e:
                errors.append(f'{folder_name}：{e}')

        progress.setValue(len(to_export))

        msg = f'成功导出 {len(exported)} 个关卡到：\n{export_dir}\n'
        if exported:
            preview = exported[:8]
            msg += '\n导出列表（前8个）：\n' + '\n'.join(f'  - {n}' for n in preview)
            if len(exported) > 8:
                msg += f'\n  ... 共 {len(exported)} 个'
        if errors:
            msg += f'\n\n失败 {len(errors)} 个：\n' + '\n'.join(f'  - {e}' for e in errors[:5])

        box = QMessageBox(self)
        box.setWindowTitle('导出完成')
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Open)
        box.button(QMessageBox.Open).setText('打开导出文件夹')
        if box.exec_() == QMessageBox.Open:
            import subprocess
            if sys.platform.startswith('win'):
                os.startfile(export_dir)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', export_dir])
            else:
                subprocess.Popen(['xdg-open', export_dir])

    def _apply_edits_to_adofai(self, export_folder: str, level: LevelInfo):
        adofai_file = None
        for root, dirs, files in os.walk(export_folder):
            for f in files:
                if f.lower().endswith('.adofai'):
                    adofai_file = os.path.join(root, f)
                    break
            if adofai_file:
                break

        if not adofai_file:
            return

        with open(adofai_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        for field, new_val in level.edited.items():
            if field == 'difficulty':
                pattern = rf'("difficulty"\s*:\s*)\d+\.?\d*'
                repl = rf'\g<1>{new_val}'
                content = re.sub(pattern, repl, content)
            else:
                pattern = rf'("{field}"\s*:\s*)"[^"]*"'
                repl = rf'\g<1>"{new_val}"'
                content = re.sub(pattern, repl, content)

        with open(adofai_file, 'w', encoding='utf-8-sig') as f:
            f.write(content)

        # ── TUF 查找功能 ──
    def tuf_search(self):
        """执行 TUF 在线搜索。"""
        rows = self._selected_rows()
        if len(rows) != 1:
            return

        idx = self._row_to_level_index(rows[0])
        if idx is None:
            return
        level = self.levels[idx]

        query_str = build_query(level)
        if not query_str:
            QMessageBox.information(self, "TUF 查找", "当前关卡没有足够的信息用于搜索。")
            return

        self.status_bar.showMessage("正在搜索 TUF 数据库...")
        self.tuf_btn.setEnabled(False)

        self._tuf_thread = TufSearchThread(query_str, self)
        self._tuf_thread.finished.connect(lambda results: self._on_tuf_finished(results, level))
        self._tuf_thread.error.connect(self._on_tuf_error)
        self._tuf_thread.start()

    def _on_tuf_finished(self, results: list, level):
        """处理 TUF 搜索返回结果。"""
        self.tuf_btn.setEnabled(True)

        if len(results) == 0:
            self.status_bar.showMessage("TUF 未找到匹配的关卡")
            QMessageBox.information(
                self, "TUF 查找",
                f"未在 TUF 数据库中找到与 \"{level.song}\" 匹配的关卡。\n"
                "可能原因：\n"
                "• 谱面尚未上传到 TUF\n"
                "• 歌曲名/作者名有出入\n\n"
                "建议尝试编辑信息后（去掉颜色标签等）重新搜索。"
            )
        elif len(results) == 1:
            r = results[0]
            lid = r.get("id")
            song = r.get("song", "???")
            artist = r.get("artist", "???")
            creator = r.get("creator", "???")

            reply = QMessageBox.question(
                self, "TUF 查找 - 找到匹配",
                f"找到唯一匹配关卡：\n\n"
                f"  歌曲：{song}\n"
                f"  艺术家：{artist}\n"
                f"  作者：{creator}\n\n"
                f"是否在浏览器中打开？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open(f"https://tuforums.com/levels/{lid}")
                self.status_bar.showMessage(f"已打开 TUF 关卡详情页 (ID: {lid})")
            else:
                self.status_bar.showMessage("就绪")
        else:
            # 多个结果
            dialog = TufResultDialog(results, level.song, self)
            dialog.exec_()
            self.status_bar.showMessage("就绪")

    def _on_tuf_error(self, err: str):
        """处理 TUF 搜索错误。"""
        self.tuf_btn.setEnabled(True)
        self.status_bar.showMessage(f"TUF 搜索失败: {err}")
        QMessageBox.warning(self, "TUF 查找错误", f"网络请求失败：\n{err}")
    def closeEvent(self, event):
        self.stop_music()
        if self._mixer_ready:
            pygame.mixer.quit()
        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.cancel()
            self._load_thread.wait()
        event.accept()