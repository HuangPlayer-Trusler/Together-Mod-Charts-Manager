import os
import zipfile
from PyQt5.QtCore import QThread, pyqtSignal
from .settings_parser import parse_adofai_settings
from .level_info import LevelInfo
from .utils import sanitize_filename

class LoadThread(QThread):
    progress        = pyqtSignal(int, int, str)
    level_loaded    = pyqtSignal(object)
    finished_signal = pyqtSignal(int, int)

    def __init__(self, folder: str, temp_dir: str):
        super().__init__()
        self.folder = folder
        self.temp_dir = temp_dir
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        zip_files = sorted(f for f in os.listdir(self.folder) if f.lower().endswith('.zip'))
        total = len(zip_files)
        loaded = 0

        for i, zip_name in enumerate(zip_files):
            if self._cancel:
                break

            self.progress.emit(i, total, f'正在处理：{zip_name}')
            zip_path = os.path.join(self.folder, zip_name)
            base_name = os.path.splitext(zip_name)[0]
            extract_path = os.path.join(self.temp_dir, sanitize_filename(base_name))

            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    names = zf.namelist()
                    top_entries = set()
                    for n in names:
                        top = n.split('/')[0]
                        if top:
                            top_entries.add(top)

                    if len(top_entries) == 1:
                        actual_folder = os.path.join(self.temp_dir, list(top_entries)[0])
                        if os.path.isdir(actual_folder):
                            extract_path = actual_folder
                        else:
                            os.makedirs(self.temp_dir, exist_ok=True)
                            zf.extractall(self.temp_dir)
                            if not os.path.isdir(actual_folder):
                                raise RuntimeError('解压后未找到顶层文件夹')
                            extract_path = actual_folder
                    else:
                        if not os.path.exists(extract_path):
                            os.makedirs(extract_path, exist_ok=True)
                            zf.extractall(extract_path)

                adofai_file = None
                for root, dirs, files in os.walk(extract_path):
                    for f in files:
                        if f.lower().endswith('.adofai'):
                            adofai_file = os.path.join(root, f)
                            break
                    if adofai_file:
                        break

                if not adofai_file:
                    self.progress.emit(i + 1, total, f'未找到 .adofai：{zip_name}')
                    continue

                settings = parse_adofai_settings(adofai_file)
                level = LevelInfo(zip_path, extract_path, adofai_file, settings)
                self.level_loaded.emit(level)
                loaded += 1

            except Exception as e:
                self.progress.emit(i + 1, total, f'错误 {zip_name}：{e}')

        self.finished_signal.emit(loaded, total)