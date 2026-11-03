import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from beespector_lite.settings import defaults, load_settings, config_path

class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        d=defaults(); self.assertTrue(d['shortcut_toolbar_visible']); self.assertTrue(d['find_bar_visible']); self.assertTrue(d['status_bar_visible']); self.assertFalse(d['library_visible']); self.assertEqual(d['library_sidebar_width'],320); self.assertEqual(d['drop_behavior'],'active'); self.assertNotIn('action_toolbar_visible',d); self.assertNotIn('main_toolbar_visible',d); self.assertNotIn('compare_index_limit',d); self.assertNotIn('recent_files',d)

    def test_old_visibility_keys_do_not_hide_main_toolbar(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'XDG_CONFIG_HOME': td}):
            p=config_path(); p.parent.mkdir(parents=True); p.write_text(json.dumps({'show_ascii':False,'action_toolbar_visible':False,'find_bar_visible':False,'main_toolbar_visible':False}),encoding='utf-8')
            data=load_settings(); self.assertFalse(data['show_ascii']); self.assertTrue(data['shortcut_toolbar_visible']); self.assertFalse(data['find_bar_visible']); self.assertNotIn('action_toolbar_visible',data); self.assertNotIn('main_toolbar_visible',data); self.assertNotIn('toolbar_position',data); self.assertNotIn('recent_files',data); self.assertNotIn('window_state',data); self.assertNotIn('compare_index_limit',data)

    def test_old_global_shortcuts_migrate_and_are_bounded(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'XDG_CONFIG_HOME': td}):
            p=config_path(); p.parent.mkdir(parents=True); p.write_text(json.dumps({'global_toolbar_shortcuts':['status_bar','status_bar']+[f'x{i}' for i in range(200)]}),encoding='utf-8')
            d=load_settings(); self.assertEqual(d['shortcut_toolbar_shortcuts'][0],'status_bar'); self.assertEqual(len(d['shortcut_toolbar_shortcuts']),128); self.assertEqual(len(set(d['shortcut_toolbar_shortcuts'])),128)

if __name__=='__main__': unittest.main()
