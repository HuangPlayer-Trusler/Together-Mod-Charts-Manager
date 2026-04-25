import re
import json

def strip_js_comments(text: str) -> str:
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text

def parse_adofai_settings(filepath: str) -> dict:
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'latin-1']
    content = None
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc, errors='replace') as f:
                content = f.read()
            break
        except Exception:
            continue

    if content is None:
        return {}

    m = re.search(r'"settings"\s*:', content)
    if not m:
        return {}

    start_brace = content.find('{', m.end())
    if start_brace == -1:
        return {}

    depth = 0
    end_brace = -1
    for i, ch in enumerate(content[start_brace:], start=start_brace):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end_brace = i
                break

    if end_brace == -1:
        return {}

    raw_block = content[start_brace: end_brace + 1]
    cleaned = strip_js_comments(raw_block)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    fallback = {}
    key_patterns = {
        'song':         r'"song"\s*:\s*"([^"]*)"',
        'author':       r'"author"\s*:\s*"([^"]*)"',
        'artist':       r'"artist"\s*:\s*"([^"]*)"',
        'difficulty':   r'"difficulty"\s*:\s*([0-9.]+)',
        'bpm':          r'"bpm"\s*:\s*([0-9.]+)',
        'levelTags':    r'(?:"levelTags"\s*:\s*"([^"]*)"|"levelTags"\s*:\s*(\[[^\]]*\]))',
        'levelDesc':    r'"levelDesc"\s*:\s*"([^"]*)"',
        'songFilename': r'"songFilename"\s*:\s*"([^"]*)"',
        'bgImage':      r'"bgImage"\s*:\s*"([^"]*)"',
        'previewImage': r'"previewImage"\s*:\s*"([^"]*)"',
        'artistLinks':  r'"artistLinks"\s*:\s*"([^"]*)"',
    }
    for key, pattern in key_patterns.items():
        mm = re.search(pattern, raw_block)
        if not mm:
            continue
        if key == 'levelTags':
            val = mm.group(1) or mm.group(2)
            if val is None:
                continue
            if val.startswith('['):
                try:
                    val = ', '.join(json.loads(val))
                except json.JSONDecodeError:
                    pass
            else:
                val = val.strip('"')
        else:
            val = mm.group(1).strip()
            if key in ('difficulty', 'bpm'):
                try:
                    val = float(val) if '.' in val else int(val)
                except ValueError:
                    pass
        fallback[key] = val
    return fallback