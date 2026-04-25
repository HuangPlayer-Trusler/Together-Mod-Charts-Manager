# level_info.py
import os
import re
from .utils import strip_color_tags, safe_str
from .constants import MISSING

class LevelInfo:
    """
    存储单个关卡的全部信息，并提供导出名称、编辑支持等功能。
    """

    def __init__(self, zip_path: str, extracted_path: str, adofai_path: str, settings: dict):
        self.zip_path = zip_path
        self.extracted_path = extracted_path
        self.adofai_path = adofai_path
        self.settings = settings
        self.edited = {}  # 用户编辑 {field: new_value}

        # 关卡名取自 ZIP 文件名（去除扩展名）
        self.level_name = os.path.splitext(os.path.basename(zip_path))[0]

        # 保留原始值（含颜色标签）供详情 HTML 渲染
        self._song_raw   = safe_str(settings.get('song'))
        self._author_raw = safe_str(settings.get('author'))
        self._artist_raw = safe_str(settings.get('artist'))

        # 去除颜色标签后的纯文本，用于表格、搜索、文件命名
        self.song   = strip_color_tags(self._song_raw)
        self.author = strip_color_tags(self._author_raw)
        self.artist = strip_color_tags(self._artist_raw)

        # 供 TUF 查找等需要无标签纯文本的场景
        self.song_pure   = self.song if self.song != MISSING else ''
        self.author_pure = self.author if self.author != MISSING else ''
        self.artist_pure = self.artist if self.artist != MISSING else ''

        self.bpm            = safe_str(settings.get('bpm'))
        self.difficulty     = safe_str(settings.get('difficulty'))
        self.level_tags     = strip_color_tags(safe_str(settings.get('levelTags')))
        self.level_desc     = strip_color_tags(safe_str(settings.get('levelDesc')))
        self.song_filename  = safe_str(settings.get('songFilename'))

        self.music_path = self._resolve_music_path()

    def _resolve_music_path(self) -> str:
        """在解压后的目录中查找音乐文件。"""
        if self.song_filename == MISSING:
            return ''
        level_dir = os.path.dirname(self.adofai_path)
        full = os.path.join(level_dir, self.song_filename)
        if os.path.isfile(full):
            return full
        # 大小写不敏感查找（Linux）
        try:
            lower = self.song_filename.lower()
            for f in os.listdir(level_dir):
                if f.lower() == lower:
                    return os.path.join(level_dir, f)
        except OSError:
            pass
        return ''

    @property
    def display_edited(self) -> bool:
        """关卡是否被编辑过。"""
        return bool(self.edited)

    def apply_edit(self, field: str, value):
        """应用一个编辑项，同时更新对应的显示属性。"""
        if field == 'song':
            self.song = value
            self._song_raw = value
        elif field == 'author':
            self.author = value
            self._author_raw = value
        elif field == 'artist':
            self.artist = value
            self._artist_raw = value
        elif field == 'difficulty':
            self.difficulty = str(value)
        elif field == 'levelDesc':
            self.level_desc = value
        self.edited[field] = value

    def export_folder_name(self) -> str:
        """生成导出文件夹名：歌曲名 - 作者 - ZIP名（尽量使用有效字段）。"""
        from .utils import sanitize_filename
        parts = []
        if self.song != MISSING:
            parts.append(self.song)
        if self.author != MISSING:
            parts.append(self.author)
        parts.append(self.level_name)
        return sanitize_filename('-'.join(parts)) if parts else sanitize_filename(self.level_name)

    @staticmethod
    def _split_creators(creator_string: str) -> list:
        """
        按 & 或 | 拆分作者字符串，返回纯文本列表。
        用于 TUF 查找时生成独立的 creator 查询条件。
        """
        if not creator_string or creator_string == MISSING:
            return []
        # 先去除可能残留的富文本标签
        clean = strip_color_tags(creator_string)
        # 按 & 或 | 拆分，并去除空白
        parts = re.split(r'\s*[&|]\s*', clean)
        return [p.strip() for p in parts if p.strip()]