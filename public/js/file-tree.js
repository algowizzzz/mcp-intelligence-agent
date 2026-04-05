/**
 * BPulseFileTree — shared file tree library (REQ-01a)
 * Exports: BPulseFileTree, BPulseFilePreview
 *
 * Bugs fixed:
 *   BUG-FS-001: input.select() called immediately after input.value = oldName
 *   BUG-FS-003: XHR used for uploads (not fetch) so upload progress works
 */
(function (global) {
  'use strict';

  /* ============================================================
     Utilities
     ============================================================ */
  function esc(str) {
    if (typeof str !== 'string') str = String(str == null ? '' : str);
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  var _FOLDER_SVG = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#888888" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
  var _FILE_SVG   = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#aaaaaa" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
  var _CHEVRON_SVG = '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>';

  /* ============================================================
     BPulseFilePreview
     ============================================================ */
  /**
   * config: { containerId: string }
   */
  function BPulseFilePreview(config) {
    this._containerId = config.containerId;
  }

  /**
   * Render a file preview into the container.
   * @param {string} section
   * @param {string} path
   * @param {string} name
   * @param {string} apiPrefix  e.g. '/api/fs'
   * @param {function} tokenFn  () => string
   */
  BPulseFilePreview.prototype.render = function (section, path, name, apiPrefix, tokenFn) {
    var el = document.getElementById(this._containerId);
    if (!el) return;
    var ext = (name.split('.').pop() || '').toLowerCase();
    var url = apiPrefix + '/' + section + '/file?path=' + encodeURIComponent(path);
    var tok = tokenFn ? tokenFn() : '';
    var headers = { 'Content-Type': 'application/json' };
    if (tok) headers['Authorization'] = 'Bearer ' + tok;

    el.innerHTML = '<div style="padding:12px;font-size:12px;color:#aaa">Loading preview…</div>';

    // Binary formats — fetch as base64
    if (['pdf', 'docx', 'doc', 'xlsx', 'xls'].indexOf(ext) >= 0) {
      _fetchJson(url, headers, function (data) {
        if (!data) { el.innerHTML = '<div style="padding:12px;color:#aaa">Error loading file</div>'; return; }
        var content = data.content || '';
        function b64ToAb(b64) {
          var bin = atob(b64);
          var ab = new ArrayBuffer(bin.length);
          var u8 = new Uint8Array(ab);
          for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
          return ab;
        }
        var ab = b64ToAb(content);
        if (ext === 'pdf') {
          if (typeof pdfjsLib !== 'undefined') {
            el.innerHTML = '<canvas id="bpfp-pdf-canvas" style="max-width:100%"></canvas>';
            pdfjsLib.getDocument({ data: ab }).promise.then(function (doc) {
              doc.getPage(1).then(function (page) {
                var vp = page.getViewport({ scale: 1.2 });
                var canvas = el.querySelector('#bpfp-pdf-canvas');
                canvas.width = vp.width; canvas.height = vp.height;
                page.render({ canvasContext: canvas.getContext('2d'), viewport: vp });
              });
            });
          } else {
            var burl = URL.createObjectURL(new Blob([ab], { type: 'application/pdf' }));
            el.innerHTML = '<iframe src="' + burl + '" style="width:100%;height:100%;min-height:400px;border:none"></iframe>';
          }
        } else if (ext === 'xlsx' || ext === 'xls') {
          if (typeof XLSX !== 'undefined') {
            var wb = XLSX.read(ab, { type: 'array' });
            var ws = wb.Sheets[wb.SheetNames[0]];
            el.innerHTML = '<div style="overflow:auto">' + XLSX.utils.sheet_to_html(ws) + '</div>';
          } else {
            el.innerHTML = '<div style="padding:12px;color:#aaa">SheetJS not loaded — Excel preview unavailable</div>';
          }
        } else if (ext === 'docx' || ext === 'doc') {
          if (typeof mammoth !== 'undefined') {
            mammoth.convertToHtml({ arrayBuffer: ab })
              .then(function (result) {
                var html = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(result.value) : result.value;
                el.innerHTML = '<div style="font-size:12px;line-height:1.6;padding:12px">' + html + '</div>';
              })
              .catch(function () { el.innerHTML = '<div style="padding:12px;color:#aaa">Word preview failed</div>'; });
          } else {
            el.innerHTML = '<div style="padding:12px;color:#aaa">mammoth.js not loaded — Word preview unavailable</div>';
          }
        }
      });
      return;
    }

    // Parquet
    if (ext === 'parquet' || ext === 'pq') {
      el.innerHTML = '<div style="padding:12px;color:#aaa">Parquet binary file — use the agent to query this file.</div>';
      return;
    }

    // Text / structured formats
    _fetchJson(url, headers, function (data) {
      if (!data) { el.innerHTML = '<div style="padding:12px;color:#aaa">Error loading file</div>'; return; }
      var text = data.content || '';
      if (ext === 'md') {
        if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
          el.innerHTML = '<div style="padding:12px">' + DOMPurify.sanitize(marked.parse(text)) + '</div>';
        } else if (typeof marked !== 'undefined') {
          el.innerHTML = '<div style="padding:12px">' + marked.parse(text) + '</div>';
        } else {
          el.innerHTML = '<pre style="padding:12px;white-space:pre-wrap;font-size:12px">' + esc(text) + '</pre>';
        }
      } else if (ext === 'csv' || ext === 'tsv') {
        var sep = ext === 'tsv' ? '\t' : ',';
        var lines = text.split('\n').slice(0, 51).filter(Boolean);
        if (!lines.length) { el.innerHTML = '<pre style="padding:12px">(empty)</pre>'; return; }
        var rows = lines.map(function (l) { return l.split(sep); });
        var thead = rows[0].map(function (c) { return '<th style="padding:4px 8px;border:1px solid rgba(255,255,255,0.12)">' + esc(c) + '</th>'; }).join('');
        var tbody = rows.slice(1).map(function (r) {
          return '<tr>' + r.map(function (c) { return '<td style="padding:3px 8px;border:1px solid rgba(255,255,255,0.08);font-size:11px">' + esc(c) + '</td>'; }).join('') + '</tr>';
        }).join('');
        el.innerHTML = '<div style="overflow:auto;padding:8px"><table style="border-collapse:collapse;font-size:12px"><thead><tr>' + thead + '</tr></thead><tbody>' + tbody + '</tbody></table></div>';
      } else if (ext === 'html') {
        el.innerHTML = '<iframe srcdoc="' + esc(text) + '" sandbox="allow-scripts" style="width:100%;height:400px;border:none"></iframe>';
      } else if (ext === 'py') {
        if (typeof hljs !== 'undefined') {
          var result = hljs.highlight(text, { language: 'python' });
          el.innerHTML = '<pre style="padding:12px;font-size:11px;overflow:auto"><code class="hljs">' + result.value + '</code></pre>';
        } else {
          el.innerHTML = '<pre style="padding:12px;font-size:11px;overflow:auto;white-space:pre-wrap">' + esc(text) + '</pre>';
        }
      } else if (['txt', 'json', 'xml', 'yaml', 'yml'].indexOf(ext) >= 0) {
        if (ext === 'json') {
          try { text = JSON.stringify(JSON.parse(text), null, 2); } catch (e) {}
        }
        el.innerHTML = '<pre style="padding:12px;font-size:11px;overflow:auto;white-space:pre-wrap">' + esc(text) + '</pre>';
      } else {
        el.innerHTML = '<div style="padding:12px;color:#aaa">Preview not available for this file type.</div>';
      }
    });
  };

  BPulseFilePreview.prototype.clear = function () {
    var el = document.getElementById(this._containerId);
    if (el) el.innerHTML = '';
  };

  /* ============================================================
     Internal fetch helpers
     ============================================================ */
  function _fetchJson(url, headers, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    for (var k in headers) { if (Object.prototype.hasOwnProperty.call(headers, k)) xhr.setRequestHeader(k, headers[k]); }
    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { cb(JSON.parse(xhr.responseText)); } catch (e) { cb(null); }
      } else { cb(null); }
    };
    xhr.onerror = function () { cb(null); };
    xhr.send();
  }

  /* ============================================================
     BPulseFileTree constructor
     ============================================================ */
  /**
   * config:
   *   containerId      string
   *   section          string
   *   apiPrefix        string | getter
   *   writable         bool
   *   workflowSection  bool
   *   token            function() => string
   *   onFileClick      function(section, path, name)
   *   onWorkflowSelect function(section, path, name)
   *   onToast          function(msg, type)
   *   isFileActive     function(path) => bool
   *   isFileSelected   function(path) => bool
   */
  function BPulseFileTree(config) {
    this._containerId    = config.containerId;
    this._section        = config.section;
    this._apiPrefix      = config.apiPrefix;  // may be a getter
    this._writable       = !!config.writable;
    this._workflowSection = !!config.workflowSection;
    this._token          = config.token || function () { return ''; };
    this._onFileClick    = config.onFileClick || null;
    this._onWorkflowSelect = config.onWorkflowSelect || null;
    this._onToast        = config.onToast || null;
    this._isFileActive   = config.isFileActive || null;
    this._isFileSelected = config.isFileSelected || null;
    this._onLoad         = config.onLoad || null;   // UI-AGENT-002: callback after tree data arrives
    // BUG-009: configurable confirm — default uses native confirm; pages can override to avoid CDP/browser freeze
    this._confirmFn      = config.onConfirm || function (msg, cb) { if (window.confirm(msg)) cb(); };
    this._readOnly       = false;

    // Tree state
    this._tree     = null;  // { tree: [...] }
    this._expanded = {};    // { path: bool }

    // Bulk mode
    this._bulkMode     = false;
    this._bulkSelected = {};  // { path: bool }

    // Upload queue
    this._uploadQueue  = [];  // array of { file, destFolder, id, status, progress, error }
    this._uploading    = false;
    this._uploadXhr    = null;

    // Drag state
    this._drag = null;  // { path, isDir }

    // Search
    this._searchQuery = '';

    // Closed-over ref for event handlers
    var self = this;
    // Dismiss context menu on click outside
    document.addEventListener('click', function (e) {
      var menu = document.getElementById('bpft-ctx-' + self._containerId);
      if (menu && !menu.contains(e.target)) menu.remove();
    });
  }

  /* ------------------------------------------------------------
     API prefix helper (supports getter property or plain string)
     ------------------------------------------------------------ */
  Object.defineProperty(BPulseFileTree.prototype, '_prefix', {
    get: function () {
      // Support config.apiPrefix being a getter itself
      var cfg = this._apiPrefix;
      if (typeof cfg === 'function') return cfg();
      return cfg;
    }
  });

  /* ------------------------------------------------------------
     Auth headers
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._headers = function (json) {
    var h = {};
    if (json) h['Content-Type'] = 'application/json';
    var tok = this._token();
    if (tok) h['Authorization'] = 'Bearer ' + tok;
    return h;
  };

  /* ------------------------------------------------------------
     Toast
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._toast = function (msg, type) {
    if (this._onToast) this._onToast(msg, type || 'info');
  };

  /* ------------------------------------------------------------
     URL helpers
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._url = function (op) {
    return this._prefix + '/' + this._section + '/' + op;
  };

  /* ------------------------------------------------------------
     load — fetch tree and render
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.load = function () {
    var self = this;
    var el = document.getElementById(self._containerId);
    if (el) el.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:#888">Loading…</div>';
    var xhr = new XMLHttpRequest();
    xhr.open('GET', self._url('tree'));
    var h = self._headers(false);
    for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          self._tree = JSON.parse(xhr.responseText);
          self._render();
          // UI-AGENT-002: fire onLoad callback so callers can update badges
          if (self._onLoad) self._onLoad(self._tree, self._section);
        } catch (e) {
          if (el) el.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:#888">Error loading tree</div>';
        }
      } else {
        if (el) el.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:#888">Error loading tree</div>';
      }
    };
    xhr.onerror = function () {
      if (el) el.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:#888">Failed to load</div>';
    };
    xhr.send();
  };

  BPulseFileTree.prototype.refresh = function () {
    this.load();
  };

  /* ------------------------------------------------------------
     setReadOnly
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.setReadOnly = function (val) {
    this._readOnly = !!val;
    if (this._tree) this._render();
  };

  /* ------------------------------------------------------------
     _render — build DOM from tree data
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._render = function () {
    var el = document.getElementById(this._containerId);
    if (!el) return;
    if (!this._tree || !this._tree.tree || !this._tree.tree.length) {
      el.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:#888">Empty</div>';
    } else {
      el.innerHTML = this._renderNodes(this._tree.tree, 0);
    }
    this._bindDragDrop(el);
    this._bindExternalDrop(el);
  };

  BPulseFileTree.prototype._matchesSearch = function (node) {
    var q = this._searchQuery;
    if (!q) return true;
    if (node.type !== 'folder' && node.type !== 'directory') {
      return node.name.toLowerCase().indexOf(q) >= 0;
    }
    // Folder matches if any descendant matches
    var self = this;
    if (node.name.toLowerCase().indexOf(q) >= 0) return true;
    if (node.children) {
      for (var i = 0; i < node.children.length; i++) {
        if (self._matchesSearch(node.children[i])) return true;
      }
    }
    return false;
  };

  BPulseFileTree.prototype._renderNodes = function (nodes, depth) {
    if (!nodes || !nodes.length) return '';
    var self = this;
    var html = '';
    nodes.forEach(function (node) {
      if (self._searchQuery && !self._matchesSearch(node)) return;
      var indent = depth * 14;
      var isDir = node.type === 'folder' || node.type === 'directory';
      if (isDir) {
        var isOpen = !!self._expanded[node.path];
        var chevronCls = 'ft-row-chevron' + (isOpen ? ' open' : '');
        var isWritable = self._writable && !self._readOnly && !self._bulkMode;
        html += '<div class="ft-row bpft-item" data-path="' + esc(node.path) + '" data-type="folder" data-name="' + esc(node.name) + '"' +
          ' draggable="' + (isWritable ? 'true' : 'false') + '">' +
          '<div class="ft-indent" style="width:' + indent + 'px"></div>' +
          '<div class="' + chevronCls + '">' + _CHEVRON_SVG + '</div>' +
          '<span class="ft-icon">' + _FOLDER_SVG + '</span>' +
          '<span class="ft-row-name">' + esc(node.name) + '</span>';
        if (isWritable) {
          html += '<div class="ft-row-actions">' +
            '<button class="ft-action-btn" title="New File" aria-label="New file in ' + esc(node.name) + '" data-action="newfile" data-apath="' + esc(node.path) + '">' +
              '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>' +
            '</button>' +
            '<button class="ft-action-btn danger" title="Delete folder" aria-label="Delete folder ' + esc(node.name) + '" data-action="delfolder" data-apath="' + esc(node.path) + '" data-aname="' + esc(node.name) + '">' +
              '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14H6L5 6"></path></svg>' +
            '</button>' +
          '</div>';
        }
        html += '</div>';
        if (isOpen && node.children && node.children.length) {
          html += self._renderNodes(node.children, depth + 1);
        }
      } else {
        var isActive   = self._isFileActive   ? self._isFileActive(node.path)   : false;
        var isSelected = self._isFileSelected ? self._isFileSelected(node.path) : false;
        var inBulk = self._bulkMode && self._bulkSelected[node.path];
        var rowCls = 'ft-row bpft-item' + (isActive ? ' wf-active' : '') + (isSelected || inBulk ? ' selected' : '');
        var fileIndent = (depth + 1) * 14;
        var isWritable = self._writable && !self._readOnly && !self._bulkMode;
        html += '<div class="' + rowCls + '" data-path="' + esc(node.path) + '" data-type="file" data-name="' + esc(node.name) + '"' +
          ' draggable="' + (isWritable ? 'true' : 'false') + '">' +
          '<div class="ft-indent" style="width:' + fileIndent + 'px"></div>' +
          '<div class="ft-row-chevron"></div>' +
          '<span class="ft-icon">' + _FILE_SVG + '</span>';
        if (self._bulkMode) {
          html += '<input type="checkbox" class="bpft-bulk-cb" ' + (inBulk ? 'checked' : '') + ' style="margin-right:4px">';
        }
        html += '<span class="ft-row-name">' + esc(node.name) + '</span>';
        if (node.size_bytes != null) {
          var sizeStr = node.size_bytes > 1048576
            ? (node.size_bytes / 1048576).toFixed(1) + ' MB'
            : node.size_bytes > 1024
              ? Math.round(node.size_bytes / 1024) + ' KB'
              : node.size_bytes + ' B';
          html += ' <span class="ft-row-meta">' + sizeStr + '</span>';
        }
        if (isWritable) {
          html += '<div class="ft-row-actions">' +
            '<button class="ft-action-btn danger" title="Delete" aria-label="Delete ' + esc(node.name) + '" data-action="delfile" data-apath="' + esc(node.path) + '" data-aname="' + esc(node.name) + '">' +
              '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14H6L5 6"></path></svg>' +
            '</button>' +
          '</div>';
        }
        html += '</div>';
      }
    });
    return html;
  };

  /* ------------------------------------------------------------
     DOM event wiring — called after each render
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._bindDragDrop = function (container) {
    var self = this;

    // Folder chevrons + folder row click
    var rows = container.querySelectorAll('.bpft-item');
    rows.forEach(function (row) {
      var type = row.getAttribute('data-type');
      var path = row.getAttribute('data-path');
      var name = row.getAttribute('data-name');

      // Chevron click → toggle folder
      if (type === 'folder') {
        var chevron = row.querySelector('.ft-row-chevron');
        if (chevron) {
          chevron.addEventListener('click', function (e) {
            e.stopPropagation();
            self._expanded[path] = !self._expanded[path];
            self._render();
          });
        }
        row.addEventListener('click', function (e) {
          if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
          self._expanded[path] = !self._expanded[path];
          self._render();
        });
      }

      // File click
      if (type === 'file') {
        var isWf = self._workflowSection;
        if (self._bulkMode) {
          row.addEventListener('click', function (e) {
            if (e.target.tagName === 'BUTTON') return;
            self._bulkSelected[path] = !self._bulkSelected[path];
            self._render();
          });
          var cb = row.querySelector('.bpft-bulk-cb');
          if (cb) {
            cb.addEventListener('change', function (e) {
              e.stopPropagation();
              self._bulkSelected[path] = cb.checked;
              self._render();
            });
          }
        } else {
          row.addEventListener('click', function (e) {
            if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
            if (isWf) {
              if (self._onWorkflowSelect) self._onWorkflowSelect(self._section, path, name);
            } else {
              if (self._onFileClick) self._onFileClick(self._section, path, name);
            }
          });
        }
        // Right-click context menu
        row.addEventListener('contextmenu', function (e) {
          self._showContextMenu(e, path, 'file', name);
        });
      }

      if (type === 'folder') {
        row.addEventListener('contextmenu', function (e) {
          self._showContextMenu(e, path, 'folder', name);
        });
      }

      // Action buttons
      var btns = row.querySelectorAll('[data-action]');
      btns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          var action = btn.getAttribute('data-action');
          var apath  = btn.getAttribute('data-apath');
          var aname  = btn.getAttribute('data-aname');
          if (action === 'newfile')   self.createMd(apath);
          if (action === 'delfolder') self.deleteFolder(apath, aname);
          if (action === 'delfile')   self.deleteFile(apath, aname);
        });
      });

      // Internal drag-and-drop
      if (row.getAttribute('draggable') === 'true') {
        row.addEventListener('dragstart', function (e) {
          var t = row.getAttribute('data-type');
          self._drag = { path: path, isDir: t === 'folder' || t === 'directory' };
          e.dataTransfer.effectAllowed = 'move';
          e.dataTransfer.setData('text/plain', path);
          row.style.opacity = '0.5';
        });
        row.addEventListener('dragend', function () { row.style.opacity = ''; self._drag = null; });
      }

      // Folder is a drop target (for internal move)
      if (type === 'folder') {
        row.addEventListener('dragover', function (e) {
          if (!self._drag) return;
          if (self._drag.path === path || path.indexOf(self._drag.path + '/') === 0) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = 'move';
          row.style.background = 'rgba(255,255,255,0.1)';
        });
        row.addEventListener('dragleave', function () { row.style.background = ''; });
        row.addEventListener('drop', function (e) {
          e.preventDefault();
          row.style.background = '';
          if (!self._drag || self._drag.path === path || path.indexOf(self._drag.path + '/') === 0) return;
          var srcName = self._drag.path.split('/').pop();
          var dst = path + '/' + srcName;
          var drag = self._drag;
          self._drag = null;
          var xhr = new XMLHttpRequest();
          xhr.open('POST', self._url('move'));
          var h = self._headers(true);
          for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
          xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) { self._toast('Moved', 'success'); self.load(); }
            else { self._toast('Move failed', 'error'); }
          };
          xhr.onerror = function () { self._toast('Move failed', 'error'); };
          xhr.send(JSON.stringify({ src: drag.path, dst: dst }));
        });
      }
    });
  };

  /* External/OS file drop */
  BPulseFileTree.prototype._bindExternalDrop = function (container) {
    if (!this._writable || this._readOnly) return;
    var self = this;
    container.addEventListener('dragover', function (e) {
      if (self._drag) return; // internal drag
      if (e.dataTransfer.types && (e.dataTransfer.types.indexOf('Files') >= 0 || e.dataTransfer.types.indexOf('files') >= 0)) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        container.style.outline = '2px dashed rgba(255,255,255,0.3)';
      }
    });
    container.addEventListener('dragleave', function (e) {
      if (!container.contains(e.relatedTarget)) container.style.outline = '';
    });
    container.addEventListener('drop', function (e) {
      e.preventDefault();
      container.style.outline = '';
      if (self._drag) return; // internal drop handled elsewhere
      var files = Array.from(e.dataTransfer.files);
      if (!files.length) return;
      var destFolder = '';
      var target = e.target.closest('[data-type="folder"]');
      if (target) destFolder = target.getAttribute('data-path');
      self.upload(files, destFolder);
    });
  };

  /* ------------------------------------------------------------
     Context menu
     ------------------------------------------------------------ */
  BPulseFileTree.prototype._showContextMenu = function (e, path, type, name) {
    var self = this;
    e.preventDefault();
    e.stopPropagation();
    var menuId = 'bpft-ctx-' + self._containerId;
    var old = document.getElementById(menuId);
    if (old) old.remove();

    var menu = document.createElement('div');
    menu.id = menuId;
    menu.className = 'bpft-ctx-menu';
    menu.style.cssText = 'position:fixed;z-index:9999;background:#1e1e1e;border:1px solid rgba(255,255,255,0.15);border-radius:6px;padding:4px 0;min-width:150px;box-shadow:0 4px 16px rgba(0,0,0,0.4);font-size:13px';

    function addItem(label, fn, danger) {
      var item = document.createElement('div');
      item.textContent = label;
      item.style.cssText = 'padding:6px 14px;cursor:pointer;color:' + (danger ? '#ff6b6b' : '#cccccc');
      item.addEventListener('mouseenter', function () { item.style.background = 'rgba(255,255,255,0.08)'; });
      item.addEventListener('mouseleave', function () { item.style.background = ''; });
      item.addEventListener('click', function (ev) {
        ev.stopPropagation();
        menu.remove();
        fn();
      });
      menu.appendChild(item);
    }

    function addSep() {
      var sep = document.createElement('div');
      sep.style.cssText = 'height:1px;background:rgba(255,255,255,0.08);margin:4px 0';
      menu.appendChild(sep);
    }

    if (type === 'file') {
      addItem('Preview', function () {
        if (self._workflowSection) { if (self._onWorkflowSelect) self._onWorkflowSelect(self._section, path, name); }
        else { if (self._onFileClick) self._onFileClick(self._section, path, name); }
      });
    }
    if (self._writable && !self._readOnly) {
      addItem('Rename', function () { self.rename(path, type === 'folder', name); });
    }
    if (type === 'file') {
      addItem('Download', function () { self.download(path, name); });
    }
    if (self._writable && !self._readOnly) {
      addSep();
      addItem('Delete', function () {
        if (type === 'folder') self.deleteFolder(path, name);
        else self.deleteFile(path, name);
      }, true);
    }

    document.body.appendChild(menu);
    var x = e.clientX, y = e.clientY;
    if (x + 160 > window.innerWidth)  x = window.innerWidth - 164;
    if (y + menu.offsetHeight > window.innerHeight) y = y - menu.offsetHeight;
    menu.style.left = x + 'px';
    menu.style.top  = y + 'px';
  };

  /* ------------------------------------------------------------
     mkdir — inline input row at top of tree
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.mkdir = function (parentPath) {
    var self = this;
    parentPath = parentPath || '';
    var container = document.getElementById(self._containerId);
    if (!container) return;
    // Remove existing inline input if present
    var existing = container.querySelector('.bpft-inline-input');
    if (existing) existing.remove();

    var row = document.createElement('div');
    row.className = 'ft-inline-input bpft-inline-input';
    row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 8px';
    row.innerHTML = '<span>' + _FOLDER_SVG + '</span>';
    var inp = document.createElement('input');
    inp.type = 'text';
    inp.placeholder = 'folder name';
    inp.style.cssText = 'flex:1;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);border-radius:3px;padding:2px 6px;font-size:12px;color:#cccccc;outline:none';
    row.appendChild(inp);
    container.prepend(row);
    inp.focus();

    var done = false;
    function commit() {
      if (done) return; done = true;
      var name = inp.value.trim();
      row.remove();
      if (!name) return;
      var fullPath = parentPath ? parentPath + '/' + name : name;
      var xhr = new XMLHttpRequest();
      xhr.open('POST', self._url('folder'));
      var h = self._headers(true);
      for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) { self._toast('Folder created', 'success'); self.load(); }
        else {
          try { var d = JSON.parse(xhr.responseText); self._toast(d.detail || 'Create folder failed', 'error'); }
          catch (ex) { self._toast('Create folder failed', 'error'); }
        }
      };
      xhr.onerror = function () { self._toast('Create folder failed', 'error'); };
      xhr.send(JSON.stringify({ path: fullPath }));
    }

    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { done = true; row.remove(); }
    });
    inp.addEventListener('blur', commit);
  };

  /* ------------------------------------------------------------
     createMd — inline input to create a .md file
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.createMd = function (parentPath) {
    var self = this;
    parentPath = parentPath || '';
    var container = document.getElementById(self._containerId);
    if (!container) return;
    var existing = container.querySelector('.bpft-inline-input');
    if (existing) existing.remove();

    var row = document.createElement('div');
    row.className = 'ft-inline-input bpft-inline-input';
    row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 8px';
    row.innerHTML = '<span>' + _FILE_SVG + '</span>';
    var inp = document.createElement('input');
    inp.type = 'text';
    inp.placeholder = 'filename.md';
    inp.style.cssText = 'flex:1;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);border-radius:3px;padding:2px 6px;font-size:12px;color:#cccccc;outline:none';
    row.appendChild(inp);
    container.prepend(row);
    inp.focus();

    var done = false;
    function commit() {
      if (done) return; done = true;
      var name = inp.value.trim();
      row.remove();
      if (!name) return;
      if (!name.endsWith('.md')) name += '.md';
      var fullPath = parentPath ? parentPath + '/' + name : name;
      var xhr = new XMLHttpRequest();
      xhr.open('PATCH', self._url('file'));
      var h = self._headers(true);
      for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) { self._toast('File created', 'success'); self.load(); }
        else {
          try { var d = JSON.parse(xhr.responseText); self._toast(d.detail || 'Create failed', 'error'); }
          catch (ex) { self._toast('Create failed', 'error'); }
        }
      };
      xhr.onerror = function () { self._toast('Create failed', 'error'); };
      xhr.send(JSON.stringify({ path: fullPath, content: '# ' + name.replace(/\.md$/, '') + '\n\n' }));
    }

    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { done = true; row.remove(); }
    });
    inp.addEventListener('blur', commit);
  };

  /* ------------------------------------------------------------
     rename — inline rename (BUG-FS-001: select() called right after value=)
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.rename = function (path, isDir, currentName) {
    var self = this;
    var container = document.getElementById(self._containerId);
    if (!container) return;
    var row = container.querySelector('[data-path="' + CSS.escape(path) + '"]');
    if (!row) { self._toast('Item not found in tree', 'error'); return; }
    var nameEl = row.querySelector('.ft-row-name');
    if (!nameEl) return;
    var oldName = currentName || nameEl.textContent;

    var inp = document.createElement('input');
    inp.type = 'text';
    inp.style.cssText = 'background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.2);border-radius:3px;padding:2px 6px;font-size:12px;color:#cccccc;outline:none;width:140px';
    // BUG-FS-001 fix: set value THEN select
    // SA-FT-06 fix: defer select() so it fires after browser focus settles;
    // synchronous select() can be cancelled by the layout pass that follows
    // replaceWith(), leaving the cursor at end of text — typing then appends
    // instead of replacing the selected old name.
    inp.value = oldName;
    nameEl.replaceWith(inp);
    inp.focus();
    setTimeout(function () { inp.select(); }, 0);

    var committed = false;
    function commit() {
      if (committed) return; committed = true;
      var newName = inp.value.trim();
      if (!newName || newName === oldName) { inp.replaceWith(nameEl); return; }
      var xhr = new XMLHttpRequest();
      xhr.open('POST', self._url('rename'));
      var h = self._headers(true);
      for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) { self._toast('Renamed', 'success'); self.load(); }
        else {
          try { var d = JSON.parse(xhr.responseText); self._toast(d.detail || 'Rename failed', 'error'); }
          catch (ex) { self._toast('Rename failed', 'error'); }
          inp.replaceWith(nameEl);
        }
      };
      xhr.onerror = function () { self._toast('Rename failed', 'error'); inp.replaceWith(nameEl); };
      xhr.send(JSON.stringify({ path: path, new_name: newName }));
    }

    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { committed = true; inp.replaceWith(nameEl); }
    });
    inp.addEventListener('blur', commit);
  };

  /* ------------------------------------------------------------
     deleteFile
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.deleteFile = function (path, name) {
    var self = this;
    self._confirmFn('Delete "' + (name || path) + '"?', function () {
      var xhr = new XMLHttpRequest();
      xhr.open('DELETE', self._url('file') + '?path=' + encodeURIComponent(path));
      var h = self._headers(false);
      for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) { self._toast('Deleted', 'success'); self.load(); }
        else {
          try { var d = JSON.parse(xhr.responseText); self._toast(d.detail || 'Delete failed', 'error'); }
          catch (ex) { self._toast('Delete failed', 'error'); }
        }
      };
      xhr.onerror = function () { self._toast('Delete failed', 'error'); };
      xhr.send();
    });
  };

  /* ------------------------------------------------------------
     deleteFolder
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.deleteFolder = function (path, name) {
    var self = this;
    self._confirmFn('Delete folder "' + (name || path) + '" and all its contents?', function () {
      var xhr = new XMLHttpRequest();
      xhr.open('DELETE', self._url('folder'));
      var h = self._headers(true);
      for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) { self._toast('Deleted', 'success'); self.load(); }
        else {
          try { var d = JSON.parse(xhr.responseText); self._toast(d.detail || 'Delete failed', 'error'); }
          catch (ex) { self._toast('Delete failed', 'error'); }
        }
      };
      xhr.onerror = function () { self._toast('Delete failed', 'error'); };
      xhr.send(JSON.stringify({ path: path, recursive: true }));
    });
  };

  /* ------------------------------------------------------------
     download
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.download = function (path, name) {
    var self = this;
    var url = self._url('file') + '?path=' + encodeURIComponent(path);
    var h = self._headers(false);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          var data = JSON.parse(xhr.responseText);
          var content = data.encoding === 'base64' ? Uint8Array.from(atob(data.content || ''), function (c) { return c.charCodeAt(0); }) : (data.content || '');
          var blob = new Blob([content]);
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = name;
          a.click();
        } catch (e) { self._toast('Download failed', 'error'); }
      } else { self._toast('Download failed', 'error'); }
    };
    xhr.onerror = function () { self._toast('Download failed', 'error'); };
    xhr.send();
  };

  /* ------------------------------------------------------------
     upload — XHR per-file with progress (BUG-FS-003 fix)
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.upload = function (files, destFolder) {
    var self = this;
    if (!files || !files.length) return;
    destFolder = destFolder || '';
    files.forEach(function (f) {
      self._uploadQueue.push({
        file: f,
        destFolder: destFolder,
        id: Math.random().toString(36).slice(2),
        status: 'queued',
        progress: 0,
        error: null
      });
    });
    self._renderUploadQueue();
    self._processUploadQueue();
  };

  BPulseFileTree.prototype._processUploadQueue = function () {
    var self = this;
    if (self._uploading) return;
    var next = null;
    for (var i = 0; i < self._uploadQueue.length; i++) {
      if (self._uploadQueue[i].status === 'queued') { next = self._uploadQueue[i]; break; }
    }
    if (!next) return;
    self._uploading = true;
    next.status = 'uploading';
    self._renderUploadQueue();

    var fd = new FormData();
    fd.append('file', next.file);
    var uploadUrl = self._url('upload') + (next.destFolder ? '?path=' + encodeURIComponent(next.destFolder) : '');

    var xhr = new XMLHttpRequest();
    self._uploadXhr = xhr;
    xhr.open('POST', uploadUrl);
    var tok = self._token();
    if (tok) xhr.setRequestHeader('Authorization', 'Bearer ' + tok);

    // BUG-FS-003: XHR upload progress
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) {
        next.progress = Math.round(e.loaded / e.total * 100);
        self._renderUploadQueueItem(next);
      }
    };

    xhr.onload = function () {
      self._uploading = false;
      self._uploadXhr = null;
      if (xhr.status >= 200 && xhr.status < 300) {
        next.status = 'done';
        next.progress = 100;
        self._toast('Uploaded ' + next.file.name, 'success');
        self.load();
        var queue = self._uploadQueue;
        setTimeout(function () {
          self._uploadQueue = queue.filter(function (i) { return i !== next; });
          self._renderUploadQueue();
        }, 3000);
      } else {
        next.status = 'error';
        try {
          var resp = JSON.parse(xhr.responseText);
          next.error = resp.detail || ('Upload failed: HTTP ' + xhr.status);
        } catch (ex) { next.error = 'Upload failed: HTTP ' + xhr.status; }
        self._toast('Upload failed: ' + next.file.name, 'error');
      }
      self._renderUploadQueue();
      self._processUploadQueue();
    };
    xhr.onerror = function () {
      self._uploading = false;
      self._uploadXhr = null;
      next.status = 'error';
      next.error = 'Network error';
      self._toast('Upload error: ' + next.file.name, 'error');
      self._renderUploadQueue();
      self._processUploadQueue();
    };
    xhr.send(fd);
  };

  BPulseFileTree.prototype._renderUploadQueue = function () {
    var queueEl = document.getElementById(this._containerId + '-queue');
    if (!queueEl) return;
    var queue = this._uploadQueue;
    if (!queue.length) { queueEl.innerHTML = ''; return; }
    queueEl.innerHTML = queue.map(function (item) {
      var statusColor = item.status === 'done' ? '#5c5' : item.status === 'error' ? '#c55' : '#aaa';
      var label = item.status === 'queued' ? 'Queued' : item.status === 'uploading' ? 'Uploading' : item.status === 'done' ? 'Done' : 'Error';
      return '<div style="padding:4px 8px;font-size:11px;display:flex;align-items:center;gap:6px">' +
        '<span style="color:' + statusColor + ';min-width:60px">' + label + '</span>' +
        '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#ccc">' + esc(item.file.name) + '</span>' +
        (item.status === 'uploading' ? '<div style="width:60px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px"><div style="height:4px;background:#5c9;border-radius:2px;width:' + item.progress + '%"></div></div>' : '') +
        (item.error ? '<span style="color:#c55;font-size:10px">' + esc(item.error) + '</span>' : '') +
      '</div>';
    }).join('');
  };

  BPulseFileTree.prototype._renderUploadQueueItem = function (item) {
    // Lightweight per-item progress update (no full re-render)
    this._renderUploadQueue();
  };

  /* ------------------------------------------------------------
     Bulk mode
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.toggleBulkMode = function () {
    this._bulkMode = !this._bulkMode;
    this._bulkSelected = {};
    this._render();
  };

  BPulseFileTree.prototype.getBulkCount = function () {
    return Object.keys(this._bulkSelected).length;
  };

  BPulseFileTree.prototype.bulkDelete = function () {
    var self = this;
    var paths = Object.keys(self._bulkSelected);
    if (!paths.length) { self._toast('Nothing selected', 'info'); return; }
    self._confirmFn('Delete ' + paths.length + ' selected item(s)?', function () {

    var tree = self._tree;
    function isDir(path) {
      if (!tree) return false;
      function find(nodes) {
        for (var i = 0; i < (nodes || []).length; i++) {
          if (nodes[i].path === path) return nodes[i].type === 'folder' || nodes[i].type === 'directory';
          if (nodes[i].children) {
            var r = find(nodes[i].children);
            if (r !== undefined) return r;
          }
        }
      }
      return !!find(tree.tree);
    }

    var done = 0, failed = 0, remaining = paths.slice();
    function next() {
      if (!remaining.length) {
        self._toast('Deleted ' + done + (failed ? ', ' + failed + ' failed' : '') + ' item(s)', failed ? 'error' : 'success');
        self._bulkMode = false;
        self._bulkSelected = {};
        self.load();
        return;
      }
      var p = remaining.shift();
      var dir = isDir(p);
      var xhr = new XMLHttpRequest();
      if (dir) {
        xhr.open('DELETE', self._url('folder'));
        var h = self._headers(true);
        for (var k in h) { if (Object.prototype.hasOwnProperty.call(h, k)) xhr.setRequestHeader(k, h[k]); }
        xhr.onload = function () { if (xhr.status >= 200 && xhr.status < 300) done++; else failed++; next(); };
        xhr.onerror = function () { failed++; next(); };
        xhr.send(JSON.stringify({ path: p, recursive: true }));
      } else {
        xhr.open('DELETE', self._url('file') + '?path=' + encodeURIComponent(p));
        var h2 = self._headers(false);
        for (var k2 in h2) { if (Object.prototype.hasOwnProperty.call(h2, k2)) xhr.setRequestHeader(k2, h2[k2]); }
        xhr.onload = function () { if (xhr.status >= 200 && xhr.status < 300) done++; else failed++; next(); };
        xhr.onerror = function () { failed++; next(); };
        xhr.send();
      }
    }
    next();
    }); // end _confirmFn callback
  };

  /* ------------------------------------------------------------
     search / clearSearch (F-SEARCH-01)
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.search = function (query) {
    this._searchQuery = (query || '').toLowerCase().trim();
    this._render();
  };

  BPulseFileTree.prototype.clearSearch = function () {
    this._searchQuery = '';
    this._render();
  };

  /* ------------------------------------------------------------
     loadQuota — render storage quota bar into a container
     ------------------------------------------------------------ */
  BPulseFileTree.prototype.loadQuota = function (containerId) {
    var self = this;
    var el = document.getElementById(containerId);
    if (!el) return;
    // _prefix is already the base (e.g. /api/fs); quota lives at /api/fs/quota
    var base = this._prefix;
    fetch(base + '/quota', { headers: self._headers(false) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var pct = data.used_pct || 0;
        var color = pct >= 95 ? '#ef4444' : pct >= 80 ? '#f59e0b' : '#22c55e';
        var used = data.used_bytes > 1048576
          ? (data.used_bytes / 1048576).toFixed(1) + ' MB'
          : Math.round(data.used_bytes / 1024) + ' KB';
        el.innerHTML = '<div style="font-size:10px;color:var(--text-muted,#888);margin-bottom:3px">' + used + ' used</div>' +
          '<div style="height:3px;background:rgba(255,255,255,0.1);border-radius:2px">' +
          '<div style="height:100%;width:' + Math.min(pct, 100) + '%;background:' + color + ';border-radius:2px;transition:width 0.4s"></div>' +
          '</div>';
      })
      .catch(function () {});
  };

  /* ============================================================
     Exports
     ============================================================ */
  global.BPulseFileTree    = BPulseFileTree;
  global.BPulseFilePreview = BPulseFilePreview;

})(window);
