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
   File preview — uses /api/files/<id>/preview (registered route)
   Also detects when the iframe got a non-PDF (404 error page) and
   shows a friendly fallback instead of embedding the whole dashboard.
   --------------------------------------------------------------------- */
(function () {
  'use strict';

  window.previewFile = function (fileId, filename, mimeType) {
    var back = document.getElementById('previewBack');
    var title = document.getElementById('previewTitle');
    var sub = document.getElementById('previewSub');
    var body = document.getElementById('previewBody');
    if (!back || !body) return;

    filename = filename || 'File';
    mimeType = mimeType || '';
    title.textContent = filename;
    sub.textContent = mimeType;

    back.classList.add('show');
    document.body.style.overflow = 'hidden';

    // Registered route lives under /api
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

  /* Watch the iframe to detect a 404/HTML error page sneaking in */
  function watchIframe(iframe, filename, fileId, mimeType) {
    if (!iframe) return;
    var checked = false;

    function check() {
      if (checked) return;
      checked = true;
      try {
        // Same-origin: we can inspect the body.
        var doc = iframe.contentDocument || iframe.contentWindow.document;
        if (!doc) return;
        var hasSidebar = doc.querySelector('.sidebar, .topbar, .mobile-nav');
        var isError = doc.querySelector('.error-page, .empty h1');
        var looksLikeHtml = doc.body && doc.body.querySelector('html, body');

        // If the loaded page contains app chrome, it's the error page.
        if (hasSidebar || (isError && looksLikeHtml)) {
          showFallback(iframe.parentNode, filename, fileId, mimeType,
                       'Preview unavailable — the file may not exist or you may not have access.');
        }
      } catch (e) {
        // Cross-origin — cannot inspect. Ignore.
      }
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
          '<button type="button" class="btn outline" onclick="closePreview()">Close</button>' +
        '</div>' +
      '</div>';
  }

  window.closePreview = function () {
    var back = document.getElementById('previewBack');
    if (!back) return;
    back.classList.remove('show');
    var body = document.getElementById('previewBody');
    if (body) body.innerHTML = '';
    document.body.style.overflow = '';
  };

  document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'previewBack') {
      window.closePreview();
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
