"""
test_data_layer_access.py — Unit tests verifying all operational tools use all 3 data layers.

Tests are structured in two groups:
  A. data_context module — get_data_layers, resolve_file, list_files
  B. Per-tool layer access — each tool's path resolution path tested with mock Flask g
"""
import os
import sys
import csv
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from io import BytesIO

# Make sure sajhamcpserver packages are importable
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)


# ─────────────── helpers ─────────────────────────────────────────────────────

def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _flask_g_ctx(domain_data_path='', my_data_path='', common_data_path=''):
    """Return a mock Flask g that exposes worker_ctx + flat attributes."""
    g = MagicMock()
    g.worker_ctx = {
        'domain_data_path': domain_data_path,
        'my_data_path':     my_data_path,
        'common_data_path': common_data_path,
    }
    g.worker_data_root    = domain_data_path
    g.worker_my_data_root = my_data_path
    g.worker_common_root  = common_data_path
    g.user_id             = 'test_user'
    return g


# ═════════════════════════════════════════════════════════════════════════════
# A. data_context
# ═════════════════════════════════════════════════════════════════════════════

class TestDataContext(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)
        # place test files in each layer
        _write_csv(os.path.join(self.domain, 'domain_file.csv'), [{'a': 1}])
        _write_csv(os.path.join(self.mydata,  'user_file.csv'),  [{'b': 2}])
        _write_csv(os.path.join(self.common,  'shared_file.csv'), [{'c': 3}])

    def _run_with_ctx(self, fn):
        """Run fn inside a mocked Flask request context."""
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        with patch('flask.g', g):
            return fn()

    def test_get_data_layers_all(self):
        from sajha.data_context import get_data_layers
        layers = self._run_with_ctx(lambda: get_data_layers('all'))
        names = [n for n, _ in layers]
        self.assertIn('my_data',     names, "my_data layer missing")
        self.assertIn('domain_data', names, "domain_data layer missing")
        self.assertIn('common',      names, "common layer missing")

    def test_get_data_layers_single_section(self):
        from sajha.data_context import get_data_layers
        layers = self._run_with_ctx(lambda: get_data_layers('domain_data'))
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0][0], 'domain_data')

    def test_resolve_file_domain(self):
        from sajha.data_context import resolve_file
        path, layer = self._run_with_ctx(lambda: resolve_file('domain_file.csv'))
        self.assertEqual(layer, 'domain_data')
        self.assertTrue(os.path.exists(path))

    def test_resolve_file_my_data(self):
        from sajha.data_context import resolve_file
        path, layer = self._run_with_ctx(lambda: resolve_file('user_file.csv'))
        self.assertEqual(layer, 'my_data')

    def test_resolve_file_common(self):
        from sajha.data_context import resolve_file
        path, layer = self._run_with_ctx(lambda: resolve_file('shared_file.csv'))
        self.assertEqual(layer, 'common')

    def test_resolve_file_not_found(self):
        from sajha.data_context import resolve_file
        with self.assertRaises(FileNotFoundError):
            self._run_with_ctx(lambda: resolve_file('nonexistent.csv'))

    def test_list_files_all(self):
        from sajha.data_context import list_files
        files = self._run_with_ctx(lambda: list_files(extensions={'csv'}))
        names = {f['name'] for f in files}
        self.assertIn('domain_file.csv', names)
        self.assertIn('user_file.csv',   names)
        self.assertIn('shared_file.csv', names)

    def test_resolve_file_strips_layer_prefix(self):
        from sajha.data_context import resolve_file
        # Passing "domain_data/domain_file.csv" should strip the prefix
        path, layer = self._run_with_ctx(lambda: resolve_file('domain_data/domain_file.csv'))
        self.assertEqual(layer, 'domain_data')


# ═════════════════════════════════════════════════════════════════════════════
# B. Tool layer access
# ═════════════════════════════════════════════════════════════════════════════

class TestDuckDBOLAPToolLayerAccess(unittest.TestCase):
    """DuckDbBaseTool._scan_data_files must return files from all 3 layers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)
        _write_csv(os.path.join(self.domain, 'dom.csv'),    [{'x': 1}])
        _write_csv(os.path.join(self.mydata,  'mine.csv'),  [{'y': 2}])
        _write_csv(os.path.join(self.common,  'shared.csv'), [{'z': 3}])

    def test_scan_finds_all_three_layers(self):
        from sajha.tools.impl.duckdb_olap_tools_refactored import DuckDbListFilesTool
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        with patch('flask.g', g):
            # DuckDbListFilesTool __init__ calls _initialize_views_from_files;
            # we mock get_data_layers to return our test dirs
            from sajha.data_context import get_data_layers as _real_gdl
            with patch('sajha.tools.impl.duckdb_olap_tools_refactored.get_data_layers',
                       side_effect=_real_gdl):
                tool = DuckDbListFilesTool()
            # Now call _scan_data_files with our test directories pre-set
            tool.data_directories = [
                ('domain_data', self.domain),
                ('my_data', self.mydata),
                ('common', self.common),
            ]
            files = tool._scan_data_files.__func__(tool)  # type: ignore
            sections = {f['section'] for f in files}
            self.assertIn('domain_data', sections, f"domain_data not in {sections}")
            self.assertIn('my_data',     sections, f"my_data not in {sections}")
            self.assertIn('common',      sections, f"common not in {sections}")


class TestSqlSelectLayerAccess(unittest.TestCase):
    """_ensure_worker_sources must register files from all 3 layers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)
        _write_csv(os.path.join(self.domain, 'dom.csv'),    [{'x': 1}])
        _write_csv(os.path.join(self.mydata,  'mine.csv'),  [{'y': 2}])
        _write_csv(os.path.join(self.common,  'shared.csv'), [{'z': 3}])

    def test_sources_registered_for_all_layers(self):
        import duckdb
        from sajha.tools.impl.sqlselect_tool_refactored import SqlSelectListSourcesTool

        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        g.worker_data_root = self.domain

        with patch('flask.g', g):
            from sajha.data_context import get_data_layers as _real_gdl
            with patch('sajha.tools.impl.sqlselect_tool_refactored.get_data_layers',
                       side_effect=_real_gdl):
                tool = SqlSelectListSourcesTool()

            tool._loaded_data_dir = ''  # reset cache so _ensure_worker_sources re-runs
            tool._ensure_worker_sources()

            # Column name differs across DuckDB versions: try view_name, fallback to name
            try:
                views = {row[0] for row in tool.connection.execute(
                    "SELECT view_name FROM duckdb_views()").fetchall()}
            except Exception:
                views = {row[0] for row in tool.connection.execute(
                    "SELECT name FROM duckdb_views()").fetchall()}
            self.assertTrue(any('dom' in v for v in views),    f"domain view missing. Views: {views}")
            self.assertTrue(any('mine' in v for v in views),   f"my_data view missing. Views: {views}")
            self.assertTrue(any('shared' in v for v in views), f"common view missing. Views: {views}")


class TestIrisCCRLayerAccess(unittest.TestCase):
    """IrisBaseTool._iris_csv_path must find iris_combined.csv in any data layer."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)

    def _run_iris_path(self, g):
        from sajha.tools.impl import iris_ccr_tools
        iris_ccr_tools.IrisBaseTool._df = None  # reset class-level cache
        with patch('flask.g', g):
            return iris_ccr_tools.IrisBaseTool._iris_csv_path()

    def test_finds_in_domain_data(self):
        path = os.path.join(self.domain, 'iris', 'iris_combined.csv')
        _write_csv(path, [{'Date': '2024-01-01', 'CP': 'A', 'Exposure': 100}])
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        result = self._run_iris_path(g)
        self.assertTrue(result.endswith('iris_combined.csv'))

    def test_finds_in_my_data(self):
        path = os.path.join(self.mydata, 'iris', 'iris_combined.csv')
        _write_csv(path, [{'Date': '2024-01-01', 'CP': 'B', 'Exposure': 200}])
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        result = self._run_iris_path(g)
        self.assertTrue(result.endswith('iris_combined.csv'))

    def test_finds_in_common(self):
        path = os.path.join(self.common, 'iris', 'iris_combined.csv')
        _write_csv(path, [{'Date': '2024-01-01', 'CP': 'C', 'Exposure': 300}])
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        result = self._run_iris_path(g)
        self.assertTrue(result.endswith('iris_combined.csv'))


class TestOperationalToolsLayerAccess(unittest.TestCase):
    """pdf_read, md_to_docx, search_files must accept paths from all 3 layers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)

    def test_pdf_read_accepts_all_layers(self):
        """_safe_path in pdf_read must validate paths in each layer."""
        import sajha.tools.impl.operational_tools as op_mod
        from pathlib import Path

        for layer_dir in [self.domain, self.mydata, self.common]:
            fp = os.path.join(layer_dir, 'doc.pdf')
            with open(fp, 'wb') as f:
                f.write(b'%PDF-1.4')

        # Use resolved paths to avoid macOS /var → /private/var symlink mismatch
        dom_r = Path(self.domain).resolve()
        my_r  = Path(self.mydata).resolve()
        com_r = Path(self.common).resolve()

        for layer_dir in [self.domain, self.mydata, self.common]:
            fp = str(Path(os.path.join(layer_dir, 'doc.pdf')).resolve())
            result = op_mod._safe_path(fp, dom_r, my_r, com_r)
            self.assertIsNotNone(result, f"_safe_path returned None for {layer_dir}")


class TestDataTransformLayerAccess(unittest.TestCase):
    """_safe_path in data_transform_tools must accept paths from all 3 layers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)

    def test_safe_path_all_layers(self):
        import sajha.tools.impl.data_transform_tools as dt_mod
        from pathlib import Path

        for layer_dir in [self.domain, self.mydata, self.common]:
            fp = os.path.join(layer_dir, 'data.csv')
            _write_csv(fp, [{'col': 1}])

        # Use resolved paths to avoid macOS /var → /private/var symlink mismatch
        dom_r = Path(self.domain).resolve()
        my_r  = Path(self.mydata).resolve()
        com_r = Path(self.common).resolve()

        with patch.object(dt_mod, '_domain_root', return_value=dom_r), \
             patch.object(dt_mod, '_my_data_root', return_value=my_r), \
             patch.object(dt_mod, '_common_root',  return_value=com_r):

            for layer_dir in [self.domain, self.mydata, self.common]:
                fp = str(Path(os.path.join(layer_dir, 'data.csv')).resolve())
                result = dt_mod._safe_path(fp)
                self.assertIsNotNone(result, f"_safe_path rejected valid path in {layer_dir}")


class TestMsDocLayerAccess(unittest.TestCase):
    """MsDocBaseTool._get_file_path must search all 3 layers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.domain = os.path.join(self.tmpdir, 'domain')
        self.mydata  = os.path.join(self.tmpdir, 'my_data')
        self.common  = os.path.join(self.tmpdir, 'common')
        for d in [self.domain, self.mydata, self.common]:
            os.makedirs(d, exist_ok=True)

    def _make_tool(self, g):
        from sajha.tools.impl.msdoc_tools_tool_refactored import MsDocListFilesTool
        tool = MsDocListFilesTool.__new__(MsDocListFilesTool)
        tool.docs_directory = self.domain
        tool.config = {}
        tool.logger = MagicMock()
        return tool

    def _run_get_file_path(self, filename, layer_dir):
        g = _flask_g_ctx(self.domain, self.mydata, self.common)
        # Write file in specified layer
        fp = os.path.join(layer_dir, filename)
        with open(fp, 'w') as f:
            f.write('dummy')
        with patch('flask.g', g):
            tool = self._make_tool(g)
            result = tool._get_file_path(filename)
        return result

    def test_finds_in_domain_data(self):
        result = self._run_get_file_path('report_domain.docx', self.domain)
        self.assertIn('report_domain.docx', result)

    def test_finds_in_my_data(self):
        result = self._run_get_file_path('report_mine.docx', self.mydata)
        self.assertIn('report_mine.docx', result)

    def test_finds_in_common(self):
        result = self._run_get_file_path('report_shared.docx', self.common)
        self.assertIn('report_shared.docx', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
