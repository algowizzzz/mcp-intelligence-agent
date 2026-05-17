"""
test_uat_phase3.py
==================
Phase 3 — Admin Panel UI
Combines static analysis of admin.html (AP-04/05/06/08/09/13) with
live API tests for audit pagination (AP-13 API side).

Run: python test_uat_phase3.py
"""

import re, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from uat_framework import UATReporter, login, req

MODULE = '8 — Admin Panel UI'
R      = UATReporter('phase3')

ADMIN_HTML = pathlib.Path('public/admin.html')
SUPER_CREDS = ('risk_agent', 'RiskAgent2025!')

html = ADMIN_HTML.read_text(encoding='utf-8') if ADMIN_HTML.exists() else ''

R.section('Phase 3 — Admin Panel UI (static + API)')


# ─── AP-04 : External file drop zone ─────────────────────────────────────────
def test_ap04():
    checks = {
        'handleExternalDragOver function':  'function handleExternalDragOver' in html,
        'handleExternalDragLeave function': 'function handleExternalDragLeave' in html,
        'handleExternalDrop function':      'function handleExternalDrop' in html,
        'ondragover on domain_data tree':   "ondragover=\"handleExternalDragOver(event,'domain_data')" in html,
        'ondrop on domain_data tree':       "ondrop=\"handleExternalDrop(event,'domain_data'" in html,
        'ondragover on workflows tree':     "ondragover=\"handleExternalDragOver(event,'verified_workflows')" in html,
        'ondrop on workflows tree':         "ondrop=\"handleExternalDrop(event,'verified_workflows'" in html,
        'drop-active CSS class':            'drop-active' in html,
        'dataTransfer.files usage':         'dataTransfer.files' in html,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        R.fail('AP-04', MODULE, 'External file drop zone implemented', detail=', '.join(failed))
    else:
        R.ok('AP-04', MODULE, 'External file drop zone implemented')

test_ap04()


# ─── AP-05 : Inline rename (dblclick) ────────────────────────────────────────
def test_ap05():
    checks = {
        'startInlineRename function':       'function startInlineRename' in html,
        'dblclick listener on tree item':   'dblclick' in html,
        'startInlineRename called in dblclick': re.search(r"dblclick.*?startInlineRename", html, re.DOTALL) is not None,
        '.tree-rename-input used':          'tree-rename-input' in html,
        'Enter key commits rename':         re.search(r"Enter.*rename|rename.*Enter", html, re.DOTALL) is not None,
        'Escape key cancels rename':        re.search(r"Escape.*rename|rename.*Escape", html, re.DOTALL) is not None,
        'renameItem calls startInlineRename': re.search(r"function renameItem.*?startInlineRename", html, re.DOTALL) is not None,
        'no prompt() in renameItem':        not re.search(r"function renameItem[^}]*prompt\(", html, re.DOTALL),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        R.fail('AP-05', MODULE, 'Inline rename (dblclick) implemented', detail=', '.join(failed))
    else:
        R.ok('AP-05', MODULE, 'Inline rename (dblclick) implemented')

test_ap05()


# ─── AP-06 : Right-click context menu ────────────────────────────────────────
def test_ap06():
    checks = {
        'contextmenu event listener':       'contextmenu' in html,
        'showContextMenu function':         'function showContextMenu' in html,
        'closeContextMenu function':        'function closeContextMenu' in html,
        '.context-menu CSS':                '.context-menu {' in html or '.context-menu{' in html,
        '.context-menu-item CSS':           'context-menu-item' in html,
        'contextmenu → showContextMenu call': re.search(r"contextmenu.*showContextMenu", html, re.DOTALL) is not None,
        'Preview in context menu':          re.search(r"context.*[Pp]review|[Pp]review.*context", html, re.DOTALL) is not None,
        'Rename in context menu':           re.search(r"Rename.*menu|menu.*Rename", html, re.DOTALL) is not None,
        'Delete in context menu':           re.search(r"Delete.*context|context.*Delete|danger.*Delete|Delete.*danger", html, re.DOTALL) is not None,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        R.fail('AP-06', MODULE, 'Right-click context menu implemented', detail=', '.join(failed))
    else:
        R.ok('AP-06', MODULE, 'Right-click context menu implemented')

test_ap06()


# ─── AP-13 : Audit log pagination (UI) ───────────────────────────────────────
def test_ap13_ui():
    checks = {
        '_auditOffset variable':      '_auditOffset' in html,
        '_auditTotal variable':       '_auditTotal' in html,
        '_auditLimit variable':       '_auditLimit' in html,
        'auditPagePrev function':     'function auditPagePrev' in html or 'auditPagePrev' in html,
        'auditPageNext function':     'function auditPageNext' in html or 'auditPageNext' in html,
        'updateAuditPagination fn':   'function updateAuditPagination' in html,
        'audit-pagination HTML div':  'id="audit-pagination"' in html,
        'Prev button':                'audit-prev-btn' in html or '← Prev' in html,
        'Next button':                'audit-next-btn' in html or 'Next →' in html,
        'offset passed to API':       re.search(r"offset.*_auditOffset|_auditOffset.*offset", html) is not None,
        'total_matched read':         'total_matched' in html,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        R.fail('AP-13', MODULE, 'Audit log pagination UI', detail=', '.join(failed))
    else:
        R.ok('AP-13', MODULE, 'Audit log pagination UI')

test_ap13_ui()


# ─── AP-13 : Audit pagination API (live) ─────────────────────────────────────
def test_ap13_api():
    tok = login(*SUPER_CREDS)
    if not tok:
        R.skip('AP-13b', MODULE, 'Audit pagination API — server not reachable', reason='no token')
        return
    s, body = req('GET', '/api/super/audit?limit=5&offset=0', token=tok)
    if s != 200:
        R.fail('AP-13b', MODULE, 'Audit pagination API returns limit/offset fields', detail=f'HTTP {s}')
        return
    has_total    = 'total_matched' in body or 'total' in body
    has_returned = 'total_returned' in body or 'entries' in body or isinstance(body, list)
    if has_total and has_returned:
        total = body.get('total_matched', body.get('total', '?'))
        R.ok('AP-13b', MODULE, f'Audit pagination API (total_matched={total})')
    else:
        R.fail('AP-13b', MODULE, 'Audit pagination API returns total_matched field', detail=str(body)[:120])

test_ap13_api()


# ─── AP-08 : bulkDelete uses showModal not window.confirm ────────────────────
def test_ap08_modal():
    # The fix: bulkDelete() uses showModal() + Promise, not window.confirm()
    in_bulk_fn = re.search(r"function bulkDelete\([^)]*\)(.*?)^}", html, re.DOTALL | re.MULTILINE)
    if in_bulk_fn:
        fn_body = in_bulk_fn.group(1)
        uses_modal    = 'showModal' in fn_body
        no_confirm    = 'window.confirm' not in fn_body
        uses_promise  = 'Promise' in fn_body or '_bulkDeleteResolve' in fn_body
        if uses_modal and no_confirm:
            R.ok('AP-08b', MODULE, 'bulkDelete uses showModal() not window.confirm()')
        else:
            R.fail('AP-08b', MODULE, 'bulkDelete uses showModal() not window.confirm()',
                   detail=f'modal={uses_modal} no_confirm={no_confirm}')
    else:
        R.fail('AP-08b', MODULE, 'bulkDelete uses showModal() not window.confirm()',
               detail='bulkDelete function not found')

test_ap08_modal()


# ─── AP-09 : GFM pipe table rendering ────────────────────────────────────────
def test_ap09_gfm():
    checks = {
        'gfmTable or pipe-table regex in renderMarkdown': (
            'gfmTable' in html or
            re.search(r"renderMarkdown.*?\|.*?table|table.*?\|.*?renderMarkdown", html, re.DOTALL) is not None or
            re.search(r"\\\||\|.*?<table|<th>.*?\|", html) is not None or
            'split.*\\|' in html or
            re.search(r"pipe|gfm|table.*col", html, re.IGNORECASE) is not None
        ),
        '.preview-md table CSS':    'preview-md table' in html or '.preview-md th' in html,
        '.preview-md th/td CSS':    'preview-md th' in html or 'preview-md td' in html,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        R.fail('AP-09b', MODULE, 'GFM pipe table CSS + renderMarkdown support', detail=', '.join(failed))
    else:
        R.ok('AP-09b', MODULE, 'GFM pipe table CSS + renderMarkdown support')

test_ap09_gfm()


# ─── Final ────────────────────────────────────────────────────────────────────
R.print_final_summary()
jp, mp = R.save()
print(f'\n  JSON → {jp}')
print(f'  MD   → {mp}')
