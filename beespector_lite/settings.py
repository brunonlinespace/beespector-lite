from __future__ import annotations
import json, os
from pathlib import Path
from . import ORGANISATION, APP_ID


def config_path() -> Path:
    if os.name == 'nt':
        root = Path(os.environ.get('APPDATA', Path.home()/'AppData'/'Roaming'))
        return root / ORGANISATION / APP_ID / 'beespector-lite.json'
    root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
    return root / ORGANISATION / APP_ID / 'beespector-lite.json'


def defaults() -> dict:
    return {
        'bytes_per_row': 16,
        'show_ascii': True,
        'show_offset': True,
        'show_column_identifiers': True,
        'offset_mode': 'hex',
        'font_family': '',
        'font_size': 11,
        'font_weight': 400,
        'font_italic': False,
        'canvas_scheme': 'dark',
        'text_colour_mode': 'detected_strings',
        'status_bar_visible': True,
        'shortcut_toolbar_visible': True,
        'find_bar_visible': True,
        'shortcut_toolbar_shortcuts': [],
        'library_layout': 'floating',
        'library_visible': False,
        'library_sidebar_width': 320,
        'drop_behavior': 'active',
        'window_geometry': '',
    }


def load_settings() -> dict:
    base = defaults()
    try:
        raw = json.loads(config_path().read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        raw = {}
    if not isinstance(raw, dict): raw = {}
    data = {key: raw.get(key, value) for key, value in base.items()}

    # Migrate older Lite toolbar keys into exp5's fixed Main Toolbar + optional
    # Shortcut Toolbar model.  Main Toolbar visibility is intentionally not stored.
    if 'shortcut_toolbar_visible' not in raw:
        data['shortcut_toolbar_visible'] = True
    if 'find_bar_visible' not in raw:
        data['find_bar_visible'] = bool(raw.get('find_toolbar_visible', True))
    if 'shortcut_toolbar_shortcuts' not in raw:
        data['shortcut_toolbar_shortcuts'] = raw.get('global_toolbar_shortcuts', [])

    try: data['bytes_per_row'] = max(1, min(64, int(data.get('bytes_per_row',16))))
    except Exception: data['bytes_per_row'] = 16
    data['show_ascii'] = bool(data.get('show_ascii',True))
    data['show_offset'] = bool(data.get('show_offset',True))
    data['show_column_identifiers'] = bool(data.get('show_column_identifiers',True))
    if data.get('offset_mode') not in ('hex','decimal','both'): data['offset_mode']='hex'
    try: data['font_size'] = max(8,min(28,int(data.get('font_size',11))))
    except Exception: data['font_size']=11
    try: data['font_weight'] = int(data.get('font_weight',400))
    except Exception: data['font_weight']=400
    data['font_italic'] = bool(data.get('font_italic',False))
    data['font_family'] = str(data.get('font_family','') or '')[:256]
    if data.get('canvas_scheme') not in ('dark','light'): data['canvas_scheme']='dark'
    if data.get('text_colour_mode') not in ('off','character_classes','detected_strings'): data['text_colour_mode']='detected_strings'
    data['status_bar_visible'] = bool(data.get('status_bar_visible',True))
    data['shortcut_toolbar_visible'] = bool(data.get('shortcut_toolbar_visible',True))
    data['find_bar_visible'] = bool(data.get('find_bar_visible',True))

    raw_shortcuts = data.get('shortcut_toolbar_shortcuts',[])
    if not isinstance(raw_shortcuts,list): raw_shortcuts=[]
    seen=set(); clean=[]
    for value in raw_shortcuts:
        value=str(value)[:128]
        if value and value not in seen: clean.append(value); seen.add(value)
        if len(clean)>=128: break
    data['shortcut_toolbar_shortcuts']=clean

    if data.get('library_layout') not in ('floating','left','right'): data['library_layout']='floating'
    if 'library_visible' not in raw:
        data['library_visible'] = raw.get('library_layout') in ('left','right')
    else:
        data['library_visible'] = bool(data.get('library_visible',False))
    try: data['library_sidebar_width'] = max(240,min(420,int(data.get('library_sidebar_width',320))))
    except Exception: data['library_sidebar_width']=320

    if data.get('drop_behavior') not in ('active','new'): data['drop_behavior']='active'
    value=data.get('window_geometry','')
    data['window_geometry'] = value if isinstance(value,str) and len(value)<500_000 else ''
    return data


def save_settings(data: dict) -> None:
    allowed=defaults(); clean={key:data.get(key,default) for key,default in allowed.items()}
    p=config_path(); p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(clean,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,p)
