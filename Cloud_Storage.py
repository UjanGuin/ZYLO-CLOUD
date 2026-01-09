#!/usr/bin/env python3
import os
import time
import mimetypes
from pathlib import Path
from flask import (
    Flask, request, render_template_string, send_from_directory,
    jsonify, abort, redirect, url_for, session
)
from werkzeug.utils import secure_filename

# =========================
# CONFIG
# =========================
ADMIN_PASSWORD = "7149"
SD_CARD_PATH = Path("/home/ujan/Desktop/yoyo/").resolve()   # adjust if needed
MAX_CONTENT_LENGTH_MB = 4096         # 1 GB max per request
ALLOWED_PREVIEW_TEXT = ('.txt', '.md', '.csv', '.log', '.json', '.py', '.html', '.ino')

SD_CARD_PATH.mkdir(parents=True, exist_ok=True)

# Flask
app = Flask(__name__)
app.secret_key = os.environ.get("UJAN_SECRET_KEY", "very_secret_key_change_me")
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_MB * 1024 * 1024

# =========================
# UTILITIES
# =========================
def resolve_path(rel: str) -> Path:
    if not rel or rel == '/':
        return SD_CARD_PATH
    rel = str(rel).lstrip("/")
    candidate = (SD_CARD_PATH / rel).resolve()
    try:
        candidate.relative_to(SD_CARD_PATH)
    except Exception:
        raise ValueError("Invalid path")
    return candidate

def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.02f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.02f} PB"

def safe_filename(name: str) -> str:
    name = os.path.basename(name)
    name = secure_filename(name)
    if not name:
        name = "file"
    return name

def unique_save_path(directory: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = directory / filename
    idx = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({idx}){suffix}"
        idx += 1
    return candidate

def list_directory(dirpath: Path):
    items = []
    for entry in sorted(dirpath.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
        stat = entry.stat()
        if entry.is_dir():
            items.append({
                "name": entry.name,
                "is_dir": True,
                "size": None,
                "size_h": "-",
                "mtime": stat.st_mtime,
                "mtime_h": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "type": "directory",
                "ext": ""
            })
        else:
            ext = entry.suffix.lower()
            items.append({
                "name": entry.name,
                "is_dir": False,
                "size": stat.st_size,
                "size_h": human_size(stat.st_size),
                "mtime": stat.st_mtime,
                "mtime_h": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "type": mimetypes.guess_type(entry.name)[0] or "application/octet-stream",
                "ext": ext[1:] if ext.startswith('.') else ext
            })
    return items

# =========================
# AUTH (simple)
# =========================
def logged_in():
    return session.get("ujan_authenticated", False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == ADMIN_PASSWORD:
            session["ujan_authenticated"] = True
            return redirect(url_for("index"))
        else:
            return render_template_string(LOGIN_PAGE, error="Incorrect password", sd=SD_CARD_PATH)
    return render_template_string(LOGIN_PAGE, error=None, sd=SD_CARD_PATH)

@app.route("/logout")
def logout():
    session.pop("ujan_authenticated", None)
    return redirect(url_for("login"))

@app.before_request
def require_login():
    if request.endpoint in ("login", "static"):
        return
    if request.path.startswith("/ngrok") or request.path.startswith("/public"):
        return
    if not logged_in() and request.path != url_for("login"):
        return redirect(url_for("login"))

# =========================
# TEMPLATES
# =========================
LOGIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ZYLO Cloud — Unlock</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
  <style>
    :root {
      --bg-deep: #020617;
      --glass-bg: rgba(255, 255, 255, 0.04);
      --glass-border: rgba(255, 255, 255, 0.1);
      --accent: #6366f1;
      --accent-bright: #a855f7;
      --accent-cyan: #22d3ee;
    }
    body {
      background: var(--bg-deep);
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.12) 0px, transparent 50%);
      color: #ffffff;
      font-family: 'Inter', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0;
    }
    .login-card {
      background: var(--glass-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--glass-border);
      border-radius: 24px;
      padding: 2.5rem;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    }
    .brand {
      font-weight: 800;
      font-size: 1.5rem;
      background: linear-gradient(to right, var(--accent-cyan), var(--accent-bright));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.5rem;
      text-align: center;
    }
    .form-control {
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--glass-border);
      color: white;
      border-radius: 12px;
      padding: 12px 16px;
    }
    .form-control:focus {
      background: rgba(255,255,255,0.08);
      border-color: var(--accent-cyan);
      box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.1);
      color: white;
    }
    .btn-unlock {
      background: linear-gradient(135deg, var(--accent), var(--accent-bright));
      border: none;
      color: white;
      font-weight: 600;
      border-radius: 12px;
      padding: 12px;
      margin-top: 1rem;
      transition: transform 0.2s;
    }
    .btn-unlock:hover { opacity: 0.9; }
    .btn-unlock:active { transform: scale(0.98); }
    .alert-glass {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border-radius: 12px;
      font-size: 0.85rem;
    }
  </style>
</head>
<body>
  <div class="login-card">
    <div class="brand"><i class="fa-solid fa-cloud-bolt me-2"></i>ZYLO CLOUD</div>
    <!-- Removed text-muted to make it white -->
    <p class="text-center small mb-4 text-white">Enter administrative password</p>
    
    {% if error %}
    <div class="alert alert-glass mb-4">
      <i class="fa-solid fa-circle-exclamation me-2"></i>{{ error }}
    </div>
    {% endif %}
    
    <form method="post">
      <div class="mb-3">
        <!-- Removed text-muted to make it white -->
        <label class="form-label small text-white">Access Key</label>
        <input name="password" type="password" class="form-control" placeholder="••••••••" autofocus>
      </div>
      <div class="d-grid">
        <button class="btn btn-unlock">Unlock Vault</button>
      </div>
    </form>
    
    <div class="mt-4 pt-3 border-top border-white border-opacity-10">
       <!-- Removed text-muted to make Secure Host white -->
       <div class="d-flex align-items-center gap-2 text-white" style="font-size: 0.75rem;">
          <i class="fa-solid fa-microchip"></i>
          <span>Secure Host: {{ sd }}</span>
       </div>
    </div>
  </div>
</body>
</html>
"""
# MAIN PAGE with explicit fixes for the white control/header row
MAIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ZYLO Cloud — Ultra Premium Storage</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
  <style>
    :root {
      --glass-bg: rgba(255, 255, 255, 0.04);
      --glass-border: rgba(255, 255, 255, 0.1);
      --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
      --accent: #6366f1;
      --accent-bright: #a855f7;
      --accent-cyan: #22d3ee;
      --text-main: #ffffff; 
      --text-muted: #94a3b8;
      --bg-deep: #020617;
    }

    * { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }

    html, body { 
      height: 100%; 
      margin: 0; 
      font-family: 'Inter', -apple-system, system-ui, sans-serif; 
      -webkit-font-smoothing: antialiased;
    }

    body {
      background: var(--bg-deep);
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.12) 0px, transparent 50%);
      color: var(--text-main);
      overflow-x: hidden;
    }

    /* Glass Panels */
    .glass-card {
      background: var(--glass-bg);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--glass-border);
      border-radius: 20px;
      box-shadow: var(--glass-shadow);
    }

    .navbar {
      background: rgba(15, 23, 42, 0.8);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--glass-border);
      position: sticky;
      top: 0;
      z-index: 1000;
      padding: 0.75rem 0;
    }

    .brand {
      font-weight: 800;
      font-size: 1.1rem;
      letter-spacing: -0.01em;
      background: linear-gradient(to right, var(--accent-cyan), var(--accent-bright));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .container-hero { 
      max-width: 1200px; 
      margin: 1rem auto; 
      padding: 0 1rem; 
    }

    /* Buttons */
    .btn-premium {
      background: linear-gradient(135deg, var(--accent), var(--accent-bright));
      border: none;
      color: white !important;
      font-weight: 600;
      border-radius: 12px;
      padding: 8px 16px;
    }

    .btn-premium:active { transform: scale(0.95); }

    .btn-glass {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--glass-border);
      color: var(--text-main) !important;
      border-radius: 12px;
    }

    #btn-back {
      color: var(--text-main) !important;
      opacity: 0.8;
    }
    #btn-back:hover { opacity: 1; }

    #search::placeholder {
      color: rgba(255, 255, 255, 0.5) !important;
    }

    /* FIX: Storage Info Visibility (Ensuring White) */
    #storage-info {
      color: #ffffff !important;
      opacity: 1 !important;
    }

    /* Table UI */
    .table { 
      color: var(--text-main); 
      border-collapse: separate; 
      border-spacing: 0 6px; 
      width: 100%; 
    }

    .table thead th { 
      border: none !important; 
      background: transparent !important; 
      color: #ffffff !important; 
      font-size: 0.75rem; 
      text-transform: uppercase; 
      letter-spacing: 0.1em; 
      padding: 12px;
      font-weight: 700;
    }
    
    .table tbody tr td { 
      background: rgba(255, 255, 255, 0.03); 
      border-top: 1px solid var(--glass-border); 
      border-bottom: 1px solid var(--glass-border); 
      padding: 12px;
    }
    
    .table tbody tr td:first-child { border-left: 1px solid var(--glass-border); border-radius: 14px 0 0 14px; }
    .table tbody tr td:last-child { border-right: 1px solid var(--glass-border); border-radius: 0 14px 14px 0; }

    .file-link {
      color: #ffffff !important;
      text-decoration: none;
      font-weight: 600;
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 200px; 
    }

    @media (min-width: 768px) {
        .file-link { max-width: 400px; }
    }

    .file-icon-box {
      width: 40px; height: 40px;
      flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.05);
      font-size: 1.1rem;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }

    .folder-color { color: #fbbf24; text-shadow: 0 0 10px rgba(251, 191, 36, 0.3); }
    .file-color { color: var(--accent-cyan); text-shadow: 0 0 10px rgba(34, 211, 238, 0.3); }

    /* Mobile Adaptability */
    @media (max-width: 576px) {
      .btn-glass span, .btn-premium span { display: none; }
      .container-hero { margin: 0.5rem auto; }
      .glass-card { padding: 1rem !important; border-radius: 12px; }
      .brand { font-size: 1rem; }
      .file-icon-box { width: 34px; height: 34px; font-size: 1rem; }
      .table tbody tr td { padding: 8px; }
      .path-bar { font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    }

    .path-bar {
      display: flex; align-items: center; gap: 8px;
      color: var(--text-main); font-size: 0.9rem;
      background: rgba(255,255,255,0.03);
      padding: 6px 12px;
      border-radius: 10px;
      border: 1px solid var(--glass-border);
    }

    #upload-status {
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: calc(100% - 40px);
      max-width: 320px;
      z-index: 1050;
    }
  </style>
</head>
<body>

<nav class="navbar">
  <div class="container px-3">
    <span class="brand"><i class="fa-solid fa-cloud-bolt me-2"></i>ZYLO CLOUD</span>
    <div class="ms-auto d-flex align-items-center gap-2">
      <div id="storage-info" class="small d-none d-md-block text-white me-2" style="color:#fff !important">...</div>
      <a href="/logout" class="btn btn-glass btn-sm" title="Logout"><i class="fa-solid fa-right-from-bracket"></i></a>
    </div>
  </div>
</nav>

<div class="container-hero">
  
  <div class="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-3 mb-3">
    <div class="path-bar w-100 w-sm-auto">
      <button id="btn-back" class="btn btn-link p-0 text-white me-2" style="border:none">
        <i class="fa-solid fa-chevron-left"></i>
      </button>
      <i class="fa-solid fa-folder-open small"></i> 
      <span id="current-path-display" class="text-white">/</span>
    </div>
    
    <div class="d-flex gap-2 w-100 w-sm-auto">
      <div class="input-group input-group-sm flex-grow-1">
        <input id="search" class="form-control bg-transparent border-secondary text-white shadow-none" placeholder="Filter items...">
      </div>
      <button id="refresh" class="btn btn-glass btn-sm"><i class="fa-solid fa-rotate"></i></button>
      <label class="btn btn-premium btn-sm flex-shrink-0">
        <i class="fa-solid fa-plus me-1"></i><span>Upload</span>
        <input id="file-input" type="file" class="d-none" multiple>
      </label>
    </div>
  </div>

  <div class="glass-card p-3 p-md-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div class="d-flex gap-2">
        <button id="btn-create-folder" class="btn btn-glass btn-sm"><i class="fa-solid fa-folder-plus me-sm-1"></i><span>New Folder</span></button>
        <button id="btn-delete-selected" class="btn btn-glass text-danger btn-sm border-danger"><i class="fa-solid fa-trash-can"></i></button>
      </div>
      <div class="small text-muted" id="items-info">0 items</div>
    </div>

    <div class="table-responsive">
      <table class="table align-middle">
        <thead>
          <tr>
            <th style="width:30px"><input id="select-all" type="checkbox" class="form-check-input"></th>
            <th>Name</th>
            <th class="d-none d-md-table-cell">Size</th>
            <th class="d-none d-lg-table-cell">Date</th>
            <th class="text-end px-3">Actions</th>
          </tr>
        </thead>
        <tbody id="files-body">
          <tr>
             <td colspan="5" class="text-center py-5 text-muted">
                <div class="spinner-border spinner-border-sm me-2"></div>Accessing vault...
             </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="d-flex flex-column flex-sm-row justify-content-between align-items-center mt-4 gap-3">
      <nav class="d-flex align-items-center gap-2">
        <button id="prev-page" class="btn btn-glass btn-sm"><i class="fa-solid fa-chevron-left"></i></button>
        <span class="small px-3 py-1 bg-dark rounded-pill border border-secondary" id="page-indicator">1 / 1</span>
        <button id="next-page" class="btn btn-glass btn-sm"><i class="fa-solid fa-chevron-right"></i></button>
      </nav>
    </div>
  </div>
</div>

<div id="upload-status"></div>

<div class="modal fade" id="mkdirModal" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered modal-sm">
    <div class="modal-content glass-card p-2">
      <div class="modal-header border-0">
        <h6 class="modal-title fw-bold">New Folder</h6>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <input id="new-folder-name" class="form-control bg-dark text-white border-secondary shadow-none" placeholder="Folder name">
      </div>
      <div class="modal-footer border-0">
        <button id="create-folder-confirm" class="btn btn-premium w-100">Create</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="previewModal" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-centered">
    <div class="modal-content glass-card border-0 overflow-hidden" style="max-height: 95vh;">
      <div class="modal-header border-0 bg-dark bg-opacity-50">
        <h6 class="modal-title text-truncate" id="preview-title"></h6>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body p-0 d-flex align-items-center justify-content-center bg-black overflow-auto" id="preview-body"></div>
      <div class="modal-footer border-0 bg-dark">
        <a id="preview-download" class="btn btn-premium btn-sm px-4" href="#" download>Download</a>
        <button class="btn btn-glass btn-sm" data-bs-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
  let currentPath = '/';
  let allItems = [];
  let filtered = [];
  let page = 1;
  const perPage = 15;

  const filesBody = document.getElementById('files-body');
  const pathDisplay = document.getElementById('current-path-display');
  const storageInfo = document.getElementById('storage-info');

  function api(endpoint, params = {}) {
    let path = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    const searchParams = new URLSearchParams(params).toString();
    if (searchParams) path += (path.includes('?') ? '&' : '?') + searchParams;
    return window.location.origin + path;
  }

  async function loadFiles() {
    try {
      pathDisplay.textContent = currentPath;
      const res = await fetch(api('/list', { path: currentPath }));
      if (!res.ok) throw new Error("Fetch failed");
      const data = await res.json();
      allItems = data.items || [];
      applyFiltersAndRender();
      loadStats();
    } catch (e) { 
      filesBody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-danger"><i class="fa-solid fa-wifi me-2"></i>Network Error</td></tr>`;
    }
  }

  async function loadStats() {
    try {
      const res = await fetch(api('/stats'));
      if (res.ok) {
        const data = await res.json();
        if(!data.error) storageInfo.textContent = `${data.free} Free / ${data.total}`;
      }
    } catch(e) {}
  }

  function applyFiltersAndRender() {
    const q = (document.getElementById('search').value || '').toLowerCase();
    filtered = allItems.filter(i => i.name.toLowerCase().includes(q));
    filtered.sort((a,b) => a.is_dir === b.is_dir ? a.name.localeCompare(b.name) : (a.is_dir ? -1 : 1));

    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    if (page > totalPages) page = totalPages;
    const start = (page - 1) * perPage;
    const items = filtered.slice(start, start + perPage);

    filesBody.innerHTML = '';
    if(!items.length) {
      filesBody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-muted small">No items found</td></tr>`;
    }

    items.forEach(it => {
      const tr = document.createElement('tr');
      const iconClass = it.is_dir ? 'fa-folder folder-color' : getIcon(it.ext);
      const downloadUrl = api('/download', {path: currentPath, name: it.name});
      
      tr.innerHTML = `
        <td><input type="checkbox" class="form-check-input select-item" data-name="${encodeURIComponent(it.name)}"></td>
        <td>
          <div class="d-flex align-items-center gap-2 gap-sm-3">
            <div class="file-icon-box">
               <i class="fa-solid ${iconClass}"></i>
            </div>
            <div style="min-width: 0;">
              <div class="file-link" style="cursor:pointer" data-dir="${it.is_dir}" data-name="${encodeURIComponent(it.name)}">${it.name}</div>
              <div class="small text-muted" style="font-size:0.65rem">${it.type} ${window.innerWidth < 768 ? ' • ' + it.size_h : ''}</div>
            </div>
          </div>
        </td>
        <td class="d-none d-md-table-cell text-muted small">${it.is_dir ? '--' : it.size_h}</td>
        <td class="d-none d-lg-table-cell text-muted small">${it.mtime_h}</td>
        <td class="text-end">
          <div class="d-flex align-items-center justify-content-end gap-1">
            <!-- New inline Download Button -->
            <a href="${downloadUrl}" class="btn btn-link text-info btn-sm p-1" title="Download" download>
              <i class="fa-solid fa-download"></i>
            </a>
            <div class="dropdown">
              <button class="btn btn-link text-muted btn-sm p-1" data-bs-toggle="dropdown"><i class="fa-solid fa-ellipsis-vertical"></i></button>
              <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-lg border-secondary">
                ${!it.is_dir ? `<li><button class="dropdown-item btn-preview" data-name="${encodeURIComponent(it.name)}"><i class="fa-solid fa-eye me-2"></i>Preview</button></li>` : ''}
                <li><a href="${downloadUrl}" class="dropdown-item" download><i class="fa-solid fa-download me-2"></i>Download</a></li>
                <li><hr class="dropdown-divider border-secondary"></li>
                <li><button class="dropdown-item text-danger btn-delete" data-name="${encodeURIComponent(it.name)}"><i class="fa-solid fa-trash me-2"></i>Delete</button></li>
              </ul>
            </div>
          </div>
        </td>
      `;
      filesBody.appendChild(tr);
    });

    document.getElementById('items-info').textContent = `${filtered.length} item${filtered.length !== 1 ? 's' : ''}`;
    document.getElementById('page-indicator').textContent = `${page} / ${totalPages}`;
  }

  function getIcon(ext) {
    const e = (ext||'').toLowerCase();
    if(['jpg','jpeg','png','gif','webp'].includes(e)) return 'fa-file-image file-color';
    if(['mp4','mov','webm'].includes(e)) return 'fa-file-video file-color';
    if(['mp3','wav'].includes(e)) return 'fa-file-audio file-color';
    if(['pdf'].includes(e)) return 'fa-file-pdf text-danger';
    return 'fa-file-lines file-color';
  }

  document.getElementById('btn-back').onclick = () => {
    if (currentPath === '/') return;
    const parts = currentPath.split('/').filter(p => p);
    parts.pop();
    currentPath = parts.length > 0 ? '/' + parts.join('/') : '/';
    page = 1;
    loadFiles();
  };

  document.getElementById('refresh').onclick = loadFiles;
  document.getElementById('search').oninput = () => { page = 1; applyFiltersAndRender(); };
  document.getElementById('prev-page').onclick = () => { if(page > 1) { page--; applyFiltersAndRender(); } };
  document.getElementById('next-page').onclick = () => { if(page * perPage < filtered.length) { page++; applyFiltersAndRender(); } };

  filesBody.onclick = (e) => {
    const link = e.target.closest('.file-link');
    if (link) {
      const name = decodeURIComponent(link.dataset.name);
      if(link.dataset.dir === 'true') {
        currentPath = currentPath === '/' ? '/' + name : currentPath + '/' + name;
        page = 1;
        loadFiles();
      } else previewFile(name);
      return;
    }
    const btnDel = e.target.closest('.btn-delete');
    if (btnDel) deleteItems([decodeURIComponent(btnDel.dataset.name)]);

    const btnPre = e.target.closest('.btn-preview');
    if (btnPre) previewFile(decodeURIComponent(btnPre.dataset.name));
  };

  async function deleteItems(names) {
    if(!confirm(`Delete ${names.length} item(s)?`)) return;
    try {
      const res = await fetch(api('/delete'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentPath, names})
      });
      if(res.ok) loadFiles();
    } catch (e) {}
  }

  document.getElementById('btn-delete-selected').onclick = () => {
    const selected = Array.from(document.querySelectorAll('.select-item:checked')).map(i => decodeURIComponent(i.dataset.name));
    if(selected.length) deleteItems(selected);
  };

  document.getElementById('select-all').onchange = (e) => {
    document.querySelectorAll('.select-item').forEach(i => i.checked = e.target.checked);
  };

  document.getElementById('file-input').onchange = (e) => uploadFiles(e.target.files);

  async function uploadFiles(files) {
    const statusDiv = document.getElementById('upload-status');
    for (const f of files) {
      const entry = document.createElement('div');
      entry.className = 'glass-card p-3 mb-2 shadow-lg';
      entry.innerHTML = `<div class="d-flex justify-content-between small mb-1"><span class="text-truncate me-2">${f.name}</span><span class="pct">0%</span></div><div class="progress" style="height:4px"><div class="progress-bar bg-info" style="width:0%"></div></div>`;
      statusDiv.appendChild(entry);

      await new Promise(resolve => {
        const xhr = new XMLHttpRequest();
        const form = new FormData();
        form.append('file', f);
        form.append('path', currentPath);

        xhr.upload.onprogress = (ev) => {
          const p = Math.round((ev.loaded / ev.total) * 100);
          entry.querySelector('.progress-bar').style.width = p + '%';
          entry.querySelector('.pct').textContent = p + '%';
        };
        xhr.onload = () => { setTimeout(() => entry.remove(), 1500); resolve(); };
        xhr.onerror = () => { entry.innerHTML = `<div class="text-danger small">Error: ${f.name}</div>`; resolve(); };
        xhr.open('POST', api('/upload'));
        xhr.send(form);
      });
    }
    loadFiles();
  }

  const mkModal = new bootstrap.Modal(document.getElementById('mkdirModal'));
  document.getElementById('btn-create-folder').onclick = () => mkModal.show();
  document.getElementById('create-folder-confirm').onclick = async () => {
    const name = document.getElementById('new-folder-name').value.trim();
    if(!name) return;
    const res = await fetch(api('/mkdir'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: currentPath, name})
    });
    if(res.ok) { mkModal.hide(); loadFiles(); document.getElementById('new-folder-name').value=''; }
  };

  async function previewFile(name) {
    const url = api('/preview', {path: currentPath, name: name});
    const body = document.getElementById('preview-body');
    const title = document.getElementById('preview-title');
    const dl = document.getElementById('preview-download');
    title.textContent = name;
    dl.href = api('/download', {path: currentPath, name: name});
    body.innerHTML = '<div class="spinner-border text-info"></div>';
    new bootstrap.Modal(document.getElementById('previewModal')).show();

    try {
      const res = await fetch(url);
      const type = res.headers.get('Content-Type');
      if(type && type.startsWith('image/')) body.innerHTML = `<img src="${url}" class="img-fluid" style="max-height:85vh">`;
      else if(type && type.startsWith('video/')) body.innerHTML = `<video controls autoplay class="w-100" style="max-height:85vh"><source src="${url}"></video>`;
      else if(type === 'application/pdf') body.innerHTML = `<iframe src="${url}" width="100%" height="80vh" style="border:none"></iframe>`;
      else {
        const text = await res.text();
        body.innerHTML = `<pre class="p-4 w-100 text-start overflow-auto m-0" style="height:70vh; color:#fff; font-size:12px; font-family:monospace">${text.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</pre>`;
      }
    } catch(e) { body.innerHTML = '<div class="text-danger">Preview unavailable</div>'; }
  }

  window.onload = loadFiles;
</script>
</body>
</html>
"""

# =========================
# ROUTES / API (same functionality)
# =========================
@app.route("/")
def index():
    return render_template_string(MAIN_PAGE)

@app.route("/list")
def api_list():
    rel = request.args.get("path", "/")
    try:
        dirpath = resolve_path(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400
    items = list_directory(dirpath)
    rel_out = "/" if dirpath == SD_CARD_PATH else str(dirpath.relative_to(SD_CARD_PATH)).replace(os.sep, '/')
    rel_out = '/' + rel_out.strip('/') if rel_out != '/' else '/'
    return jsonify({"path": rel_out, "items": items})

@app.route("/upload", methods=["POST"])
def upload():
    path = request.form.get('path') or request.args.get('path') or '/'
    try:
        target_dir = resolve_path(path)
    except ValueError:
        return ("Invalid path", 400)
    if not target_dir.exists() or not target_dir.is_dir():
        return ("Target directory doesn't exist", 400)
    if 'file' not in request.files:
        return ("No file part", 400)
    f = request.files['file']
    if f.filename == '':
        return ("No selected file", 400)
    fname = safe_filename(f.filename)
    dest = unique_save_path(target_dir, fname)
    f.save(str(dest))
    return ("OK", 200)

@app.route("/mkdir", methods=["POST"])
def mkdir():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    path = data.get('path', '/')
    if not name:
        return ("Missing name", 400)
    try:
        target_dir = resolve_path(path)
    except ValueError:
        return ("Invalid path", 400)
    new_dir = target_dir / safe_filename(name)
    try:
        new_dir.mkdir(exist_ok=False)
    except FileExistsError:
        return ("Exists", 409)
    except Exception:
        return ("Create failed", 500)
    return ("OK", 200)

@app.route("/download")
def download():
    rel = request.args.get('path', '/')
    name = request.args.get('name', '')
    try:
        dirpath = resolve_path(rel)
    except ValueError:
        abort(400)
    if not name:
        abort(404)
    name = safe_filename(name)
    file_path = dirpath / name
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    return send_from_directory(str(dirpath), name, as_attachment=True)

@app.route("/preview")
def preview():
    rel = request.args.get('path', '/')
    name = request.args.get('name', '')
    try:
        dirpath = resolve_path(rel)
    except ValueError:
        abort(400)
    if not name:
        abort(404)
    name = safe_filename(name)
    file_path = dirpath / name
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    ctype, _ = mimetypes.guess_type(str(file_path))
    if ctype is None:
        ctype = "application/octet-stream"
    return send_from_directory(str(dirpath), name, as_attachment=False, mimetype=ctype)

@app.route("/delete", methods=["POST"])
def delete():
    data = request.get_json() or {}
    names = data.get("names", [])
    path = data.get("path", "/")
    if not isinstance(names, list) or not names:
        return ("Bad request", 400)
    try:
        dirpath = resolve_path(path)
    except ValueError:
        return ("Invalid path", 400)
    failed = []
    for n in names:
        fname = safe_filename(n)
        target = dirpath / fname
        try:
            if target.exists():
                if target.is_dir():
                    try:
                        target.rmdir()
                    except Exception:
                        failed.append(n)
                else:
                    target.unlink()
            else:
                failed.append(n)
        except Exception:
            failed.append(n)
    if failed:
        return jsonify({"status":"partial","failed":failed}), 207
    return ("OK", 200)

@app.route("/stats")
def stats():
    try:
        st = os.statvfs(str(SD_CARD_PATH))
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = total - free
        return jsonify({"free": human_size(free), "used": human_size(used), "total": human_size(total)})
    except Exception:
        return jsonify({"error":"n/a"})

# =========================
# START (ngrok)
# =========================
if __name__ == "__main__":
    print("🚀 Server running at: https://indirectly-credible-egret.ngrok-free.app/")
    app.run(port=50000)

