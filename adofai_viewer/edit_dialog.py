from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, QDoubleSpinBox, QDialogButtonBox
)
from .constants import MISSING

class EditLevelDialog(QDialog):
    def __init__(self, level, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'编辑谱面信息 - {level.level_name}')
        self.level = level

        layout = QFormLayout(self)

        self.song_edit = QLineEdit(level.song if level.song != MISSING else '')
        self.author_edit = QLineEdit(level.author if level.author != MISSING else '')
        self.artist_edit = QLineEdit(level.artist if level.artist != MISSING else '')

        self.difficulty_spin = QDoubleSpinBox()
        self.difficulty_spin.setRange(0.0, 99.9)
        self.difficulty_spin.setSingleStep(0.1)
        self.difficulty_spin.setDecimals(1)
        try:
            diff_val = float(level.difficulty) if level.difficulty != MISSING else 0.0
        except ValueError:
            diff_val = 0.0
        self.difficulty_spin.setValue(diff_val)

        self.desc_edit = QTextEdit()
        desc_text = level.level_desc if level.level_desc != MISSING else ''
        self.desc_edit.setPlainText(desc_text)

        layout.addRow('歌曲名称：', self.song_edit)
        layout.addRow('关卡作者：', self.author_edit)
        layout.addRow('艺术家：', self.artist_edit)
        layout.addRow('难度：', self.difficulty_spin)
        layout.addRow('描述：', self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        return {
            'song': self.song_edit.text().strip() or MISSING,
            'author': self.author_edit.text().strip() or MISSING,
            'artist': self.artist_edit.text().strip() or MISSING,
            'difficulty': self.difficulty_spin.value(),
            'levelDesc': self.desc_edit.toPlainText().strip() or MISSING,
        }