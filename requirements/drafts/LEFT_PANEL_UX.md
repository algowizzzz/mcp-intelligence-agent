# Left Panel UX — Requirements & Documentation
**Version:** 1.0 | **Date:** 2026-04-03 | **Status:** Implemented (tabs, rename, delete)

---

## 1. Overview

The left sidebar is the primary navigation surface. It is split into two persistent horizontal tabs that separate conversational history from data and workflow resources.

```
┌──────────────────────────┐
│  ☰                       │  ← toggle sidebar
│  [  Chats  ] [ Data & W ]│  ← two horizontal tabs
├──────────────────────────┤
│                          │
│  (active tab content)    │
│                          │
├──────────────────────────┤
│  Admin  │  Theme  │  ...  │  ← sidebar-bottom (always visible)
└──────────────────────────┘
```

---

## 2. Tab 1: Chats

### 2.1 Structure
```
CONVERSATIONS          [+]
───────────────────────────
Today
  > Chat about JPM...   ✎ ×
  > OSFI watch brief    ✎ ×
Yesterday
  > Portfolio scan      ✎ ×
Previous 7 Days
  ...
```

### 2.2 Grouping
Conversations are sorted by `updated` timestamp descending, then bucketed:
| Group | Range |
|-------|-------|
| Today | Same calendar day |
| Yesterday | Prior calendar day |
| Previous 7 Days | 2–7 days ago |
| Previous 30 Days | 8–30 days ago |
| Older | > 30 days ago |

Empty groups are hidden.

### 2.3 Chat Actions (on hover)
Each conversation row reveals an actions row containing:
- **Rename** (pencil icon) — triggers inline edit
- **Delete** (× icon) — triggers confirmation modal

Double-clicking the title text also triggers inline rename.

### 2.4 Rename Flow
1. User clicks pencil or double-clicks title
2. Title span is replaced with an `<input>` pre-filled with the current title
3. **Commit:** Enter key or focus-out → saves non-empty value, re-renders sidebar
4. **Cancel:** Escape key → reverts to original value
5. Empty string is rejected — reverts to prior title

### 2.5 Delete Flow
1. User clicks × icon → confirmation modal appears
2. Modal shows conversation title, offers "Cancel" / "Delete"
3. On confirm: conversation removed from `_conversations`, sidebar re-rendered
4. If the deleted conversation was active: switches to the most recently updated remaining conversation, or shows the welcome screen if none remain

### 2.6 Persistence
All conversations (including renamed titles) are persisted to `localStorage` under the key `mcp_conversations`. Active conversation ID is stored under `mcp_active_conversation`.

---

## 3. Tab 2: Data & Workflows

### 3.1 Structure
```
[ Chats ] [ Data & Workflows ]  ← active tab
───────────────────────────────
DATA
  ▶ Domain Data          [0]   [↻]
  ▶ My Data              [5]   [📁] [+]
───────────────────────────────
WORKFLOWS
  ▶ Verified             [8]   [↻]
  ▶ My Workflows         [2]   [📁] [+] [↑]
```

### 3.2 Subsections

#### DATA group
| Subsection | Description | Actions |
|------------|-------------|---------|
| **Domain Data** | Read-only IRIS/OSFI reference data served from `data/` on the backend. Users can browse and attach files to chat context but cannot upload here. | Refresh |
| **My Data** | User-uploaded files in `data/uploads/`. Supports nested folders. Files can be dragged into chat. | New Folder, Upload File |

#### WORKFLOWS group
| Subsection | Description | Actions |
|------------|-------------|---------|
| **Verified** | Curated, tested workflows in `data/workflows/verified/`. Read-only for end users. Clicking a workflow loads it into the context bar. | Refresh |
| **My Workflows** | User-created or uploaded `.md` workflow files in `data/workflows/my_workflows/`. Full CRUD. | New Folder, New Workflow, Upload .md |

### 3.3 File Tree Behaviour
- Each subsection has an expand/collapse chevron
- Subsections are lazy-loaded on first open of the tab
- File count badge shows total items in the tree
- Folders are expandable; files show type icon
- Right-click context menu: Preview, Rename, Delete (for My Data / My Workflows)
- Drag-and-drop between folders within the same subsection

---

## 4. Implemented Features (v1.0)

| Feature | Status | Notes |
|---------|--------|-------|
| Two horizontal tabs (Chats / Data & Workflows) | ✅ Done | Persists via `_activeSidebarTab` JS var; lazy-loads file trees |
| DATA group with Domain Data + My Data subsections | ✅ Done | |
| WORKFLOWS group with Verified + My Workflows subsections | ✅ Done | |
| Chat rename (pencil icon + double-click) | ✅ Done | Inline input, Enter/Escape/blur handling |
| Chat delete (× icon + modal) | ✅ Done | Existing behaviour, now in action row |
| Group labels with horizontal rule | ✅ Done | CSS `::after` pseudo-element |

---

## 5. Planned / Backlog Features

### 5.1 Chat Management
| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| C1 | **Chat search / filter** — search box above conversation list, filters by title and message content | High | Useful once chats accumulate; debounced `input` event filtering `_conversations` in memory |
| C2 | **Pin conversations** — pin important chats to top of list, above time groups | Medium | Add `pinned: true` to conversation object; `localStorage` persisted |
| C3 | **Chat folders / labels** — organise conversations into user-defined folders or colour-coded labels | Medium | Requires a folder structure on top of `_conversations` array |
| C4 | **Export conversation** — download full chat as PDF or Markdown | Medium | Generate from `_messages` array; reuse `md_to_docx` MCP tool for Word export |
| C5 | **Share conversation** — generate a read-only shareable link | Low | Requires backend endpoint to persist and serve conversation by token |
| C6 | **Duplicate conversation** — clone an existing chat as a new conversation | Low | Copy messages + create new ID |
| C7 | **Conversation summary** — auto-generate a 1-line summary from first assistant reply, stored as `summary` field | High | Replace generic "New Chat" title auto-populated from first user message |
| C8 | **Bulk select & delete** — checkbox mode in Chats tab, delete multiple at once | Low | Mirror admin bulk-delete pattern |
| C9 | **Tab state persistence** — remember which tab was active across page refreshes | Low | `localStorage.setItem('mcp_active_tab', tab)` |

### 5.2 Data & Workflows Panel
| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| D1 | **File preview on hover / click** — quick-look preview for CSV, Parquet, PDF, Markdown without opening admin panel | High | Slide-out panel or popover, reuse existing preview code |
| D2 | **Drag file from sidebar to chat input** — attach a file from My Data directly by dragging to input box | High | `dragstart` on file row, `drop` on `#input-area`; injects `@filename` chip |
| D3 | **Recent files** — "Recently Used" sub-section above Domain Data showing last 5 files attached to any chat | Medium | Track `recentFiles` array in `localStorage` |
| D4 | **Workflow quick-run** — "Run" button on verified workflow row that pre-fills the input with the workflow invocation prompt | High | One-click instead of click → read → type |
| D5 | **Workflow favourites** — star a verified workflow to promote it to a "Favourites" sub-group above Verified | Medium | `localStorage` set of favourite filenames |
| D6 | **My Data storage indicator** — show total upload size and a soft quota warning | Low | Backend `/api/fs/uploads/stats` endpoint returning total bytes |
| D7 | **File tags** — user-defined tags on uploaded files, filterable in the tree | Low | Tags stored in a sidecar JSON file alongside each upload |
| D8 | **Workflow version history** — list previous versions of a My Workflow file via `list_versions` tool | Medium | Show version list in a popover on the row |

### 5.3 Global Sidebar UX
| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| G1 | **Resizable sidebar** — drag handle to widen/narrow sidebar, persisted in `localStorage` | Medium | CSS `resize` or manual mouse drag on border |
| G2 | **Sidebar search across all content** — unified search bar at top of sidebar searching chats, files, and workflows simultaneously | High | Triggered by Cmd+K shortcut; results grouped by type |
| G3 | **Keyboard navigation** — arrow keys to move between conversations, Enter to open | Medium | `tabindex` on sidebar items, `keydown` handler |
| G4 | **Sidebar collapse to icon rail** — collapsed sidebar shows only icons for the two tabs + bottom buttons | Low | Requires `--sidebar-width-collapsed` CSS var and icon-only mode |
| G5 | **Notifications badge** — badge on "Data & Workflows" tab when new files are uploaded externally or workflows are updated | Low | Periodic polling or server-sent events |

---

## 6. Technical Notes

### State
```javascript
_activeSidebarTab  // 'chats' | 'dw' — current active tab
_conversations     // Array<Conversation> — all chat sessions
_activeConvId      // string | null — active conversation ID
_ftTrees           // {[section]: TreeData} — cached file trees
_ftSectionOpen     // {[section]: boolean} — expand state per subsection
```

### Key Functions
| Function | Description |
|----------|-------------|
| `switchSidebarTab(tab)` | Toggles active tab; lazy-loads file trees on first 'dw' switch |
| `renderSidebar()` | Re-renders conversation list with grouping, rename, delete |
| `startRenameConversation(convId)` | Replaces title span with inline input |
| `renameConversation(convId, title)` | Persists new title, calls `renderSidebar()` |
| `confirmDeleteConversation(convId)` | Shows delete modal |
| `deleteConversation(convId)` | Removes from `_conversations`, auto-switches if active |
| `ftLoad(section)` | Fetches file tree from `/api/fs/{section}/tree` |
| `ftLoadAll()` | Loads all four file tree sections |

### localStorage Keys
| Key | Type | Purpose |
|-----|------|---------|
| `mcp_conversations` | JSON array | All conversation objects |
| `mcp_active_conversation` | string | Active conversation ID |
| `mcp_theme` | string | `'light'` or `'dark'` |
| `mcp_active_tab` *(planned)* | string | Last active sidebar tab |

---

## 7. Accessibility
- Tab buttons are `<button>` elements — keyboard focusable
- Rename input receives focus automatically on activation
- Delete confirmation modal traps focus (planned — currently relies on `onclick` on overlay)
- All icon-only buttons have `title` attributes for screen readers
