/* =====================================================================
   CampusDesk - Polish Pack v2.3
     * Toast notification system
     * Notification bell + polling
     * File preview modal (correct /api/files/... URL)
     * Keyboard shortcuts
     * Page-transition loading bar
     * Avatar color application
   ===================================================================== */

/* ---------------------------------------------------------------------
   Toast system
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  var ICON = { success: '✓', error: '✕', info: 'ℹ' };

  function ensureContainer() {
    var c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  window.showToast = function (message, kind, timeout) {
    kind = kind || 'info';
    timeout = timeout || 4000;
    if (!message) return;

    var container = ensureContainer();
    var toast = document.createElement('div');
    toast.className = 'toast ' + kind;

    var icon = document.createElement('div');
    icon.className = 'toast-icon';
    icon.textContent = ICON[kind] || ICON.info;

    var body = document.createElement('div');
    body.className = 'toast-body';
    body.textContent = message;

    var close = document.createElement('button');
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss');
    close.textContent = '×';
    close.onclick = function () { dismiss(toast); };

    toast.appendChild(icon);
    toast.appendChild(body);
    toast.appendChild(close);
    container.appendChild(toast);

    var timer = setTimeout(function () { dismiss(toast); }, timeout);
    toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
    toast.addEventListener('mouseleave', function () {
      setTimeout(function () { dismiss(toast); }, 1500);
    });
  };

  function dismiss(toast) {
    if (!toast || toast.classList.contains('hide')) return;
    toast.classList.add('hide');
    setTimeout(function () { toast.remove(); }, 240);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.flash').forEach(function (el) {
      var kind = el.classList.contains('success') ? 'success'
                : el.classList.contains('error') ? 'error' : 'info';
      window.showToast(el.textContent.trim(), kind);
      el.remove();
    });
  });
})();

/* ---------------------------------------------------------------------
   Notification bell
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  var POLL_MS = 30000;

  function bell() { return document.getElementById('bellPanel'); }
  function badge() { return document.getElementById('bellBadge'); }
  function list() { return document.getElementById('bellList'); }

  window.toggleBell = function (e) {
    if (e) e.stopPropagation();
    var p = bell();
    if (!p) return;
    p.classList.toggle('open');
    if (p.classList.contains('open')) refreshBell();
  };

  document.addEventListener('click', function (e) {
    var p = bell();
    if (!p) return;
    if (!p.classList.contains('open')) return;
    if (p.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.bell-btn')) return;
    p.classList.remove('open');
  });

  function fetchJSON(url) {
    return fetch(url, {
      headers: { 'Accept': 'application/json' },
      credentials: 'same-origin'
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  function updateBadge() {
    fetchJSON('/api/notifications/unread-count').then(function (data) {
      if (!data) return;
      var b = badge();
      if (!b) return;
      var n = data.count || 0;
      if (n > 0) {
        b.textContent = n > 99 ? '99+' : String(n);
        b.classList.remove('hidden');
      } else {
        b.classList.add('hidden');
      }
    });
  }

  function refreshBell() {
    fetchJSON('/api/notifications/recent?limit=8').then(function (data) {
      var l = list();
      if (!l || !data) return;

      if (!data.items || data.items.length === 0) {
        l.innerHTML = '<div class="bell-empty">🔕<br>No notifications yet</div>';
        return;
      }

      l.innerHTML = data.items.map(function (n) {
        return '<a class="bell-item ' + (n.read ? '' : 'unread') + '" ' +
               'href="' + (n.link || '/student/notifications') + '" ' +
               'onclick="markRead(' + n.id + ', event)">' +
                 '<div class="bell-item-title">' + escapeHtml(n.title) + '</div>' +
                 (n.message ? '<div class="bell-item-msg">' + escapeHtml(n.message) + '</div>' : '') +
                 '<div class="bell-item-time">' + (n.time_ago || '') + '</div>' +
               '</a>';
      }).join('');
    });
  }

  window.markRead = function (id, e) {
    try {
      var fd = new FormData();
      var tok = document.querySelector('input[name="csrf_token"]');
      if (tok) fd.append('csrf_token', tok.value);
      fetch('/student/notifications/read/' + id, {
        method: 'POST', body: fd, credentials: 'same-origin'
      });
    } catch (_) {}
  };

  window.markAllRead = function (e) {
    if (e) e.preventDefault();
    try {
      var fd = new FormData();
      var tok = document.querySelector('input[name="csrf_token"]');
      if (tok) fd.append('csrf_token', tok.value);
      fetch('/student/notifications/read-all', {
        method: 'POST', body: fd, credentials: 'same-origin'
      }).then(function () {
        refreshBell();
        updateBadge();
        window.showToast('All notifications marked as read', 'success');
      });
    } catch (_) {}
  };

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('bellBadge')) return;
    updateBadge();
    setInterval(updateBadge, POLL_MS);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) updateBadge();
    });
  });
})();

/* ---------------------------------------------------------------------
   File preview — Smart Board Classroom Presentation Suite
   Includes:
     * Smart Board 100% Fullscreen Mode
     * Laser Pointer with pulsating aura & motion trail
     * Dark Canvas / Projector Invert Mode for low-glare reading
     * Zen Focus Mode (Auto-hide header for 100% canvas) & Floating Mini Dock
     * In-Folder File Navigation (Prev/Next Note without exiting preview)
     * Remote clicker / keyboard shortcuts (L, D, H, F, arrows, PageUp/Down)
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  var currentPlaylist = [];
  var currentPlaylistIndex = -1;

  var isLaserActive = false;
  var laserCanvas = null;
  var laserCtx = null;
  var laserPoints = [];
  var laserAnimId = null;
  var laserCurrentPos = null;

  var isDarkCanvas = false;
  var isZenMode = false;

  /* ---------------- Smart Board Full Screen ---------------- */
  function updateSmartBoardUI(active) {
    var btn = document.getElementById('btnSmartBoard');
    var label = document.getElementById('smartBoardLabel');
    var exp = btn ? btn.querySelector('.icon-expand') : null;
    var comp = btn ? btn.querySelector('.icon-compress') : null;
    if (!btn) return;

    if (active) {
      btn.classList.add('active');
      if (label) label.textContent = 'Exit Smart Board';
      if (exp) exp.style.display = 'none';
      if (comp) comp.style.display = 'inline-block';
    } else {
      btn.classList.remove('active');
      if (label) label.textContent = 'Full Screen (Smart Board)';
      if (exp) exp.style.display = 'inline-block';
      if (comp) comp.style.display = 'none';
    }
  }

  window.toggleSmartBoardMode = function () {
    var back = document.getElementById('previewBack');
    var shell = document.getElementById('previewShell');
    if (!back || !shell) return;

    var isNowActive = !shell.classList.contains('is-smartboard');

    if (isNowActive) {
      shell.classList.add('is-smartboard');
      back.classList.add('is-smartboard');
      updateSmartBoardUI(true);

      try {
        var el = document.documentElement;
        if (el.requestFullscreen) {
          el.requestFullscreen().catch(function () {});
        } else if (el.webkitRequestFullscreen) {
          el.webkitRequestFullscreen();
        } else if (el.msRequestFullscreen) {
          el.msRequestFullscreen();
        }
      } catch (_) {}

      if (window.showToast) {
        window.showToast('🎯 Smart Board Teaching Mode enabled! Full screen ready.', 'info', 2200);
      }
    } else {
      window.exitSmartBoardMode();
    }
  };

  window.exitSmartBoardMode = function () {
    var back = document.getElementById('previewBack');
    var shell = document.getElementById('previewShell');
    if (shell) shell.classList.remove('is-smartboard', 'is-fullscreen');
    if (back) back.classList.remove('is-smartboard', 'is-fullscreen');
    updateSmartBoardUI(false);

    if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
      try {
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
        else if (document.msExitFullscreen) document.msExitFullscreen();
      } catch (_) {}
    }
  };

  function handleFullscreenChange() {
    if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
      var shell = document.getElementById('previewShell');
      var back = document.getElementById('previewBack');
      if (shell && shell.classList.contains('is-smartboard')) {
        shell.classList.remove('is-smartboard', 'is-fullscreen');
        if (back) back.classList.remove('is-smartboard', 'is-fullscreen');
        updateSmartBoardUI(false);
      }
    }
  }

  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.addEventListener('msfullscreenchange', handleFullscreenChange);

  /* ---------------- In-Folder Playlist Navigation ---------------- */
  function scanPlaylist(targetId) {
    currentPlaylist = [];
    currentPlaylistIndex = -1;

    // 1. Files grid in files.html
    var cards = document.querySelectorAll('.fcard[data-kind="file"]');
    if (cards.length > 0) {
      cards.forEach(function (card) {
        var idStr = card.getAttribute('data-id');
        if (!idStr) return;
        var fid = parseInt(idStr, 10);
        var nameEl = card.querySelector('.fcard-name');
        var name = nameEl ? nameEl.textContent.trim() : 'File';
        var btn = card.querySelector('button[onclick*="previewFile"]');
        if (btn) {
          var m = btn.getAttribute('onclick').match(/previewFile\(\s*\d+\s*,\s*['"](.*?)['"]\s*,\s*['"](.*?)['"]\s*\)/);
          var mime = m ? m[2] : '';
          currentPlaylist.push({ id: fid, filename: name, mimeType: mime });
        }
      });
    }

    // 2. Generic fallback across any page
    if (currentPlaylist.length === 0) {
      var allBtns = document.querySelectorAll('[onclick*="previewFile"]');
      var seen = {};
      allBtns.forEach(function (b) {
        var oc = b.getAttribute('onclick') || '';
        var m = oc.match(/previewFile\(\s*(\d+)\s*,\s*['"](.*?)['"]\s*,\s*['"](.*?)['"]\s*\)/);
        if (m && !seen[m[1]]) {
          seen[m[1]] = true;
          currentPlaylist.push({ id: parseInt(m[1], 10), filename: m[2], mimeType: m[3] });
        }
      });
    }

    for (var i = 0; i < currentPlaylist.length; i++) {
      if (currentPlaylist[i].id === targetId) {
        currentPlaylistIndex = i;
        break;
      }
    }

    renderPlaylistUI();
  }

  function renderPlaylistUI() {
    var navGroup = document.getElementById('previewNavGroup');
    var navCounter = document.getElementById('previewNavCounter');
    var btnPrev = document.getElementById('btnPrevFile');
    var btnNext = document.getElementById('btnNextFile');
    var dockCounter = document.getElementById('dockCounter');
    var dockPrev = document.getElementById('dockBtnPrev');
    var dockNext = document.getElementById('dockBtnNext');

    if (!navGroup) return;

    if (currentPlaylist.length > 1 && currentPlaylistIndex >= 0) {
      navGroup.style.display = 'inline-flex';
      var text = (currentPlaylistIndex + 1) + ' / ' + currentPlaylist.length;
      if (navCounter) navCounter.textContent = text;
      if (dockCounter) dockCounter.textContent = text;

      var isFirst = currentPlaylistIndex === 0;
      var isLast = currentPlaylistIndex === currentPlaylist.length - 1;

      if (btnPrev) btnPrev.disabled = isFirst;
      if (btnNext) btnNext.disabled = isLast;
      if (dockPrev) dockPrev.disabled = isFirst;
      if (dockNext) dockNext.disabled = isLast;
    } else {
      navGroup.style.display = 'none';
    }
  }

  window.previewNextFile = function () {
    if (currentPlaylistIndex >= 0 && currentPlaylistIndex < currentPlaylist.length - 1) {
      var nextItem = currentPlaylist[currentPlaylistIndex + 1];
      window.previewFile(nextItem.id, nextItem.filename, nextItem.mimeType);
    }
  };

  window.previewPrevFile = function () {
    if (currentPlaylistIndex > 0) {
      var prevItem = currentPlaylist[currentPlaylistIndex - 1];
      window.previewFile(prevItem.id, prevItem.filename, prevItem.mimeType);
    }
  };

  /* ---------------- Virtual Laser Pointer ---------------- */
  function initLaserCanvas() {
    if (laserCanvas) return;
    laserCanvas = document.getElementById('previewLaserCanvas');
    if (!laserCanvas) return;
    laserCtx = laserCanvas.getContext('2d');
    resizeLaserCanvas();
    window.addEventListener('resize', resizeLaserCanvas);
  }

  function resizeLaserCanvas() {
    if (!laserCanvas) return;
    laserCanvas.width = window.innerWidth;
    laserCanvas.height = window.innerHeight;
  }

  function onLaserMove(e) {
    if (!isLaserActive || !laserCanvas) return;
    var x = e.clientX != null ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : null);
    var y = e.clientY != null ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : null);
    if (x == null || y == null) return;

    var now = Date.now();
    laserCurrentPos = { x: x, y: y, time: now };
    laserPoints.push({ x: x, y: y, time: now });
    if (laserPoints.length > 14) laserPoints.shift();
  }

  function onLaserLeave() {
    laserCurrentPos = null;
  }

  function laserLoop() {
    if (!isLaserActive || !laserCtx || !laserCanvas) return;

    laserCtx.clearRect(0, 0, laserCanvas.width, laserCanvas.height);
    var now = Date.now();

    laserPoints = laserPoints.filter(function (p) {
      return now - p.time < 260;
    });

    if (laserPoints.length > 1) {
      for (var i = 1; i < laserPoints.length; i++) {
        var p1 = laserPoints[i - 1];
        var p2 = laserPoints[i];
        var age = now - p2.time;
        var alpha = Math.max(0, 1 - age / 260);

        laserCtx.beginPath();
        laserCtx.moveTo(p1.x, p1.y);
        laserCtx.lineTo(p2.x, p2.y);
        laserCtx.strokeStyle = 'rgba(255, 30, 60, ' + (alpha * 0.7) + ')';
        laserCtx.lineWidth = 4 * alpha;
        laserCtx.lineCap = 'round';
        laserCtx.stroke();
      }
    }

    if (laserCurrentPos && now - laserCurrentPos.time < 600) {
      var lx = laserCurrentPos.x;
      var ly = laserCurrentPos.y;

      var grad = laserCtx.createRadialGradient(lx, ly, 2, lx, ly, 26);
      grad.addColorStop(0, 'rgba(255, 0, 50, 0.95)');
      grad.addColorStop(0.35, 'rgba(255, 50, 80, 0.6)');
      grad.addColorStop(1, 'rgba(255, 0, 0, 0)');
      laserCtx.fillStyle = grad;
      laserCtx.beginPath();
      laserCtx.arc(lx, ly, 26, 0, Math.PI * 2);
      laserCtx.fill();

      laserCtx.fillStyle = '#ff1144';
      laserCtx.beginPath();
      laserCtx.arc(lx, ly, 6.5, 0, Math.PI * 2);
      laserCtx.fill();

      laserCtx.fillStyle = '#ffffff';
      laserCtx.beginPath();
      laserCtx.arc(lx, ly, 2.5, 0, Math.PI * 2);
      laserCtx.fill();
    }

    laserAnimId = requestAnimationFrame(laserLoop);
  }

  window.toggleLaserPointer = function (force) {
    initLaserCanvas();
    if (!laserCanvas) return;

    isLaserActive = (typeof force === 'boolean') ? force : !isLaserActive;

    var btn = document.getElementById('btnLaserPointer');
    var dockBtn = document.getElementById('dockBtnLaser');

    if (isLaserActive) {
      laserCanvas.classList.add('active');
      if (btn) btn.classList.add('laser-active');
      if (dockBtn) dockBtn.classList.add('active');

      window.addEventListener('pointermove', onLaserMove, { passive: true });
      window.addEventListener('touchmove', onLaserMove, { passive: true });
      window.addEventListener('pointerdown', onLaserMove, { passive: true });
      window.addEventListener('pointerleave', onLaserLeave, { passive: true });

      cancelAnimationFrame(laserAnimId);
      laserLoop();

      if (window.showToast) {
        window.showToast('🔴 Laser Pointer ON! Point anywhere on the screen.', 'info', 2200);
      }
    } else {
      laserCanvas.classList.remove('active');
      if (btn) btn.classList.remove('laser-active');
      if (dockBtn) dockBtn.classList.remove('active');

      window.removeEventListener('pointermove', onLaserMove);
      window.removeEventListener('touchmove', onLaserMove);
      window.removeEventListener('pointerdown', onLaserMove);
      window.removeEventListener('pointerleave', onLaserLeave);

      cancelAnimationFrame(laserAnimId);
      if (laserCtx && laserCanvas) {
        laserCtx.clearRect(0, 0, laserCanvas.width, laserCanvas.height);
      }
      laserPoints = [];
      laserCurrentPos = null;
    }
  };

  /* ---------------- Dark Canvas (Projector Invert) ---------------- */
  window.toggleDarkCanvas = function (force) {
    var body = document.getElementById('previewBody');
    var btn = document.getElementById('btnInvertCanvas');
    var dockBtn = document.getElementById('dockBtnInvert');
    if (!body) return;

    isDarkCanvas = (typeof force === 'boolean') ? force : !isDarkCanvas;

    if (isDarkCanvas) {
      body.classList.add('dark-canvas');
      if (btn) btn.classList.add('dark-active');
      if (dockBtn) dockBtn.classList.add('active');

      if (window.showToast) {
        window.showToast('🌙 Dark Canvas Mode ON (Low glare for projector)', 'info', 2200);
      }
    } else {
      body.classList.remove('dark-canvas');
      if (btn) btn.classList.remove('dark-active');
      if (dockBtn) dockBtn.classList.remove('active');
    }
  };

  /* ---------------- Zen Focus Mode (Auto-Hide Header) ---------------- */
  window.toggleZenMode = function (force) {
    var shell = document.getElementById('previewShell');
    var dock = document.getElementById('previewFloatingDock');
    var btn = document.getElementById('btnZenMode');
    if (!shell) return;

    isZenMode = (typeof force === 'boolean') ? force : !isZenMode;

    if (isZenMode) {
      shell.classList.add('is-zen');
      if (dock) dock.style.display = 'flex';
      if (btn) btn.classList.add('zen-active');

      window.addEventListener('mousemove', handleZenMouseMove);

      if (window.showToast) {
        window.showToast('📺 Zen Mode: 100% canvas. Move pointer to top to reveal header.', 'info', 2600);
      }
    } else {
      shell.classList.remove('is-zen');
      if (dock) dock.style.display = 'none';
      if (btn) btn.classList.remove('zen-active');
      var head = document.getElementById('previewHead');
      if (head) head.classList.remove('reveal');
      window.removeEventListener('mousemove', handleZenMouseMove);
    }
  };

  function handleZenMouseMove(e) {
    if (!isZenMode) return;
    var head = document.getElementById('previewHead');
    if (!head) return;
    if (e.clientY < 40) {
      head.classList.add('reveal');
    } else if (e.clientY > 90) {
      head.classList.remove('reveal');
    }
  }

  /* ---------------- Open File Preview ---------------- */
  window.previewFile = function (fileId, filename, mimeType) {
    var back = document.getElementById('previewBack');
    var shell = document.getElementById('previewShell');
    var title = document.getElementById('previewTitle');
    var sub = document.getElementById('previewSub');
    var body = document.getElementById('previewBody');
    var dlBtn = document.getElementById('previewDownloadBtn');
    if (!back || !body) return;

    filename = filename || 'File';
    mimeType = mimeType || '';
    if (title) title.textContent = filename;
    if (sub) sub.textContent = mimeType;

    // Reset temporary states
    if (shell) shell.classList.remove('closing');
    back.classList.remove('closing');

    // Update in-folder playlist
    scanPlaylist(fileId);

    // Set download URL
    if (dlBtn) dlBtn.href = '/files/' + fileId + '/download';

    back.classList.add('show');
    document.body.style.overflow = 'hidden';

    var url = '/api/files/' + fileId + '/preview';
    var isPdf = mimeType.indexOf('pdf') !== -1 || /\.pdf$/i.test(filename);
    var isImg = mimeType.indexOf('image/') === 0;

    if (isPdf) {
      body.innerHTML =
        '<iframe id="previewFrame" src="' + url + '" title="PDF preview"></iframe>';
      watchIframe(document.getElementById('previewFrame'), filename, fileId, mimeType);
    } else if (isImg) {
      body.innerHTML =
        '<img id="previewImg" src="' + url + '" alt="' + filename + '">';
      var img = document.getElementById('previewImg');
      if (img) {
        img.onerror = function () { showFallback(body, filename, fileId, mimeType, 'Could not load image.'); };
      }
    } else {
      showFallback(body, filename, fileId, mimeType, 'This file type cannot be previewed in the browser.');
    }
  };

  function watchIframe(iframe, filename, fileId, mimeType) {
    if (!iframe) return;
    var checked = false;

    function check() {
      if (checked) return;
      checked = true;
      try {
        var doc = iframe.contentDocument || iframe.contentWindow.document;
        if (!doc) return;
        var hasSidebar = doc.querySelector('.sidebar, .topbar, .mobile-nav');
        var isError = doc.querySelector('.error-page, .empty h1');
        var looksLikeHtml = doc.body && doc.body.querySelector('html, body');

        if (hasSidebar || (isError && looksLikeHtml)) {
          showFallback(iframe.parentNode, filename, fileId, mimeType,
                       'Preview unavailable — the file may not exist or you may not have access.');
        }
      } catch (e) {}
    }

    iframe.addEventListener('load', check);
  }

  function showFallback(body, filename, fileId, mimeType, msg) {
    if (!body) return;
    body.innerHTML =
      '<div class="preview-unsupported">' +
        '<div class="big-icon">📄</div>' +
        '<h3>Preview not available</h3>' +
        '<p>' + msg + '</p>' +
        '<div style="display:flex;gap:8px;justify-content:center;margin-top:18px;flex-wrap:wrap;">' +
          '<a class="btn" href="/files/' + fileId + '/download">⬇ Download file</a>' +
          '<button type="button" class="btn outline" onclick="closePreviewWithAnim()">Close</button>' +
        '</div>' +
      '</div>';
  }

  /* ---------------- Close Preview with Animation ---------------- */
  window.closePreviewWithAnim = function () {
    var back = document.getElementById('previewBack');
    var shell = document.getElementById('previewShell');
    if (!back || !back.classList.contains('show')) return;

    // Reset tools
    window.toggleLaserPointer(false);
    window.toggleDarkCanvas(false);
    window.toggleZenMode(false);

    if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
      try {
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
        else if (document.msExitFullscreen) document.msExitFullscreen();
      } catch (_) {}
    }

    if (shell) shell.classList.add('closing');
    back.classList.add('closing');

    setTimeout(function () {
      back.classList.remove('show', 'closing', 'is-smartboard', 'is-fullscreen');
      if (shell) shell.classList.remove('closing', 'is-smartboard', 'is-fullscreen');
      var body = document.getElementById('previewBody');
      if (body) body.innerHTML = '';
      document.body.style.overflow = '';
      updateSmartBoardUI(false);
    }, 180);
  };

  window.closePreview = window.closePreviewWithAnim;

  document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'previewBack') {
      window.closePreviewWithAnim();
    }
  });

  /* ---------------- Keyboard & Remote Clicker Shortcuts ---------------- */
  document.addEventListener('keydown', function (e) {
    var back = document.getElementById('previewBack');
    if (!back || !back.classList.contains('show')) return;

    var tag = (e.target.tagName || '').toLowerCase();
    var typing = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;
    if (typing) return;

    var key = e.key;
    var kLower = key.toLowerCase();

    if (key === 'Escape' || key === 'Esc') {
      if (isZenMode) {
        window.toggleZenMode(false);
      } else if (document.fullscreenElement || document.webkitFullscreenElement) {
        window.exitSmartBoardMode();
      } else {
        window.closePreviewWithAnim();
      }
      return;
    }

    if (kLower === 'l') {
      e.preventDefault();
      window.toggleLaserPointer();
    } else if (kLower === 'd') {
      e.preventDefault();
      window.toggleDarkCanvas();
    } else if (kLower === 'h' || kLower === 'z') {
      e.preventDefault();
      window.toggleZenMode();
    } else if (kLower === 'f' || kLower === 's') {
      e.preventDefault();
      window.toggleSmartBoardMode();
    } else if (key === 'ArrowRight' || key === ']' || key === 'PageDown') {
      e.preventDefault();
      window.previewNextFile();
    } else if (key === 'ArrowLeft' || key === '[' || key === 'PageUp') {
      e.preventDefault();
      window.previewPrevFile();
    }
  });
})();

/* ---------------------------------------------------------------------
   Keyboard shortcuts
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  var gPressed = false;
  var gTimer = null;

  document.addEventListener('keydown', function (e) {
    var tag = (e.target.tagName || '').toLowerCase();
    var typing = tag === 'input' || tag === 'textarea' ||
                 tag === 'select' || e.target.isContentEditable;

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      var s = document.querySelector('.topbar .search input');
      if (s) {
        e.preventDefault();
        s.focus();
        s.select();
      }
      return;
    }

    if (!typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (e.key.toLowerCase() === 'g') {
        gPressed = true;
        clearTimeout(gTimer);
        gTimer = setTimeout(function () { gPressed = false; }, 1200);
        return;
      }
      if (gPressed) {
        var map = {
          d: '/dashboard',
          n: '/student/notifications',
          a: '/student/assignments',
          t: '/student/timetable',
          f: '/files'
        };
        var dest = map[e.key.toLowerCase()];
        if (dest) {
          e.preventDefault();
          window.location.href = dest;
        }
        gPressed = false;
      }
    }
  });
})();

/* ---------------------------------------------------------------------
   Page-transition loading bar
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  function bar() {
    var b = document.getElementById('loadingBar');
    if (!b) {
      b = document.createElement('div');
      b.id = 'loadingBar';
      b.className = 'loading-bar';
      document.body.appendChild(b);
    }
    return b;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (!a) return;
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' ||
          href.indexOf('http') === 0 || href.indexOf('mailto:') === 0) return;
      if (a.target === '_blank' || a.hasAttribute('download')) return;
      if (e.ctrlKey || e.metaKey || e.shiftKey) return;
      bar().classList.add('active');
    });

    document.addEventListener('submit', function (e) {
      if (e.target.target === '_blank') return;
      bar().classList.add('active');
    });

    window.addEventListener('pageshow', function () {
      var b = document.getElementById('loadingBar');
      if (b) b.classList.remove('active');
    });
  });
})();

/* ---------------------------------------------------------------------
   Avatar colors
   --------------------------------------------------------------------- */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.avatar[data-color]').forEach(function (el) {
      el.style.backgroundImage = el.getAttribute('data-color');
    });
  });
})();
