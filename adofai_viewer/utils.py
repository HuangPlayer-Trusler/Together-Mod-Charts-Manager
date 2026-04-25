import re
from .constants import MISSING

# 颜色标签处理
_ANY_RICH_TAG_RE = re.compile(r'</?(?:color|b|i|u|size|material|quad)[^>]*>', re.IGNORECASE)
_COLOR_OPEN_RE = re.compile(r'<color\s*=\s*([^>]+)>', re.IGNORECASE)
_COLOR_CLOSE_RE = re.compile(r'</color>', re.IGNORECASE)
_OTHER_RICH_RE = re.compile(r'</?(?:b|i|u|size|material|quad)[^>]*>', re.IGNORECASE)

def strip_color_tags(text: str) -> str:
    if not text or text == MISSING:
        return text
    return _ANY_RICH_TAG_RE.sub('', text)

def color_tags_to_html(text: str) -> str:
    if not text or text == MISSING:
        return text
    def replace_open(m):
        color = m.group(1).strip()
        return f'<span style="color:{color}">'
    result = _COLOR_OPEN_RE.sub(replace_open, text)
    result = _COLOR_CLOSE_RE.sub('</span>', result)
    result = _OTHER_RICH_RE.sub('', result)
    return result

def safe_str(val, default=MISSING) -> str:
    if val is None or val == '' or val == [] or val == {}:
        return default
    s = str(val).strip()
    return s if s else default

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip('. ')
    return name[:200] if name else 'unnamed'