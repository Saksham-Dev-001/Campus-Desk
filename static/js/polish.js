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

  /* ---------------- PDF.js Presentation Engine ---------------- */
  var currentPdfDoc = null;
  var currentPdfPage = 1;
  var totalPdfPages = 1;
  var currentPdfScale = 1.0;
  var currentScaleMode = 'fit-page'; // 'fit-page', 'fit-width', or 'custom'
  var isRenderingPdf = false;
  var pendingPdfPage = null;

  function resetPdfState() {
    currentPdfDoc = null;
    currentPdfPage = 1;
    totalPdfPages = 1;
    currentPdfScale = 1.0;
    currentScaleMode = 'fit-page';
    isRenderingPdf = false;
    pendingPdfPage = null;
  }

  function renderPdfPage(pageNum) {
    if (!currentPdfDoc) return;
    isRenderingPdf = true;

    currentPdfDoc.getPage(pageNum).then(function (page) {
      var canvas = document.getElementById('pdfCanvas');
      if (!canvas) {
        isRenderingPdf = false;
        return;
      }
      var ctx = canvas.getContext('2d');
      var container = document.getElementById('pdfCanvasContainer');
      var availWidth = container ? (container.clientWidth - 48) : (window.innerWidth - 60);
      var availHeight = container ? (container.clientHeight - 48) : (window.innerHeight - 80);
      if (availWidth < 200) availWidth = 400;
      if (availHeight < 200) availHeight = 600;

      var unscaledViewport = page.getViewport({ scale: 1.0 });
      var scale = currentPdfScale;
      if (currentScaleMode === 'fit-page') {
        var scaleX = availWidth / unscaledViewport.width;
        var scaleY = availHeight / unscaledViewport.height;
        scale = Math.min(scaleX, scaleY);
        if (scale < 0.2) scale = 0.5;
        currentPdfScale = scale;
      } else if (currentScaleMode === 'fit-width') {
        scale = availWidth / unscaledViewport.width;
        if (scale < 0.2) scale = 0.5;
        currentPdfScale = scale;
      }

      var viewport = page.getViewport({ scale: scale });
      var outputScale = window.devicePixelRatio || 1;

      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = Math.floor(viewport.width) + 'px';
      canvas.style.height = Math.floor(viewport.height) + 'px';

      var transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;
      var renderContext = {
        canvasContext: ctx,
        transform: transform,
        viewport: viewport
      };

      var renderTask = page.render(renderContext);
      renderTask.promise.then(function () {
        isRenderingPdf = false;
        var container = document.getElementById('pdfCanvasContainer');
        if (container) setupPdfTouchGestures(container);
        if (pendingPdfPage !== null) {
          var p = pendingPdfPage;
          pendingPdfPage = null;
          renderPdfPage(p);
        }
      }).catch(function (err) {
        if (err && err.name !== 'RenderingCancelledException') {
          console.error('PDF page render error:', err);
        }
        isRenderingPdf = false;
      });

      updatePdfNavigationUI();
    }).catch(function (err) {
      console.error('Failed to get PDF page:', err);
      isRenderingPdf = false;
    });
  }

  function queueRenderPdfPage(pageNum) {
    if (isRenderingPdf) {
      pendingPdfPage = pageNum;
    } else {
      renderPdfPage(pageNum);
    }
  }

  /* ---------------- Smart Board Touch Gesture Engine ---------------- */
  /* Supports:
     1. Two-finger pinch-to-zoom:
        - Instant 60fps CSS transform scaling during touchmove without redrawing canvas
        - Renders crisp vector PDF at exact final scale on touchend
     2. Single-finger drag / pan:
        - Smooth dragging of canvas container when zoomed in or when content overflows
     3. Single-finger swipe:
        - Fast horizontal flick left/right when at full-page view to flip slides
     4. Interactive pen / mouse drag pan when zoomed in
  */
  function setupPdfTouchGestures(container) {
    if (!container || container._hasTouchGestures) return;
    container._hasTouchGestures = true;

    var initialPinchDist = 0;
    var initialScale = 1.0;
    var isPinching = false;
    var isDragging = false;
    var touchStartX = 0;
    var touchStartY = 0;
    var scrollStartX = 0;
    var scrollStartY = 0;
    var touchStartTime = 0;
    var currentScaleRatio = 1.0;

    function getDistance(t1, t2) {
      var dx = t1.clientX - t2.clientX;
      var dy = t1.clientY - t2.clientY;
      return Math.hypot(dx, dy);
    }

    container.addEventListener('touchstart', function (e) {
      if (!currentPdfDoc) return;

      if (e.touches.length === 2) {
        // Two-finger pinch gesture
        isPinching = true;
        isDragging = false;
        container.classList.add('is-pinching');
        initialPinchDist = getDistance(e.touches[0], e.touches[1]);
        initialScale = currentPdfScale;
        currentScaleRatio = 1.0;
        e.preventDefault();
      } else if (e.touches.length === 1) {
        // Single finger touch
        isDragging = true;
        isPinching = false;
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        scrollStartX = container.scrollLeft;
        scrollStartY = container.scrollTop;
        touchStartTime = Date.now();
      }
    }, { passive: false });

    container.addEventListener('touchmove', function (e) {
      if (!currentPdfDoc) return;

      if (isPinching && e.touches.length === 2) {
        e.preventDefault();
        var currentDist = getDistance(e.touches[0], e.touches[1]);
        if (initialPinchDist > 5) {
          currentScaleRatio = currentDist / initialPinchDist;
          var canvas = document.getElementById('pdfCanvas');
          if (canvas) {
            canvas.style.transform = 'scale(' + currentScaleRatio + ')';
            canvas.style.transformOrigin = 'center center';
          }
          var tempScale = Math.min(4.0, Math.max(0.35, initialScale * currentScaleRatio));
          var zoomVal = document.getElementById('dockZoomVal');
          if (zoomVal) {
            zoomVal.textContent = Math.round(tempScale * 100) + '%';
          }
        }
      } else if (isDragging && e.touches.length === 1 && !isPinching) {
        var dx = e.touches[0].clientX - touchStartX;
        var dy = e.touches[0].clientY - touchStartY;

        var canScrollX = container.scrollWidth > (container.clientWidth + 10);
        var canScrollY = container.scrollHeight > (container.clientHeight + 10);

        if (canScrollX || canScrollY || currentPdfScale > 1.1) {
          container.scrollLeft = scrollStartX - dx;
          container.scrollTop = scrollStartY - dy;
          e.preventDefault();
        }
      }
    }, { passive: false });

    function handleTouchEnd(e) {
      if (!currentPdfDoc) return;

      if (isPinching) {
        isPinching = false;
        container.classList.remove('is-pinching');
        var canvas = document.getElementById('pdfCanvas');
        if (canvas) {
          canvas.style.transform = '';
        }
        var finalScale = Math.min(4.0, Math.max(0.35, initialScale * currentScaleRatio));
        if (Math.abs(finalScale - currentPdfScale) > 0.05) {
          currentScaleMode = 'custom';
          currentPdfScale = finalScale;
          queueRenderPdfPage(currentPdfPage);
        }
      } else if (isDragging) {
        isDragging = false;
        var changedTouch = e.changedTouches ? e.changedTouches[0] : null;
        if (changedTouch) {
          var dx = changedTouch.clientX - touchStartX;
          var dy = changedTouch.clientY - touchStartY;
          var dt = Date.now() - touchStartTime;

          var canScrollX = container.scrollWidth > (container.clientWidth + 20);
          if (!canScrollX && dt < 450 && Math.abs(dx) > 75 && Math.abs(dx) > Math.abs(dy) * 1.5) {
            if (dx < 0) {
              window.dockNextAction();
            } else {
              window.dockPrevAction();
            }
          }
        }
      }
    }

    container.addEventListener('touchend', handleTouchEnd);
    container.addEventListener('touchcancel', handleTouchEnd);

    // Mouse / Interactive Pen drag panning when zoomed in
    var isMouseDown = false;
    var mouseStartX = 0;
    var mouseStartY = 0;
    var mouseScrollX = 0;
    var mouseScrollY = 0;

    container.addEventListener('mousedown', function (e) {
      if (!currentPdfDoc || e.button !== 0) return;
      var canScroll = (container.scrollWidth > container.clientWidth) || (container.scrollHeight > container.clientHeight) || currentPdfScale > 1.1;
      if (canScroll) {
        isMouseDown = true;
        mouseStartX = e.clientX;
        mouseStartY = e.clientY;
        mouseScrollX = container.scrollLeft;
        mouseScrollY = container.scrollTop;
        container.style.cursor = 'grabbing';
      }
    });

    window.addEventListener('mousemove', function (e) {
      if (!isMouseDown) return;
      var dx = e.clientX - mouseStartX;
      var dy = e.clientY - mouseStartY;
      container.scrollLeft = mouseScrollX - dx;
      container.scrollTop = mouseScrollY - dy;
    });

    window.addEventListener('mouseup', function () {
      if (isMouseDown) {
        isMouseDown = false;
        if (container) container.style.cursor = '';
      }
    });
  }

  function updatePdfNavigationUI() {
    var isPdf = !!currentPdfDoc;
    var navGroup = document.getElementById('previewNavGroup');
    var navCounter = document.getElementById('previewNavCounter');
    var btnPrev = document.getElementById('btnPrevFile');
    var btnNext = document.getElementById('btnNextFile');
    var dockCounter = document.getElementById('dockCounter');
    var dockPrev = document.getElementById('dockBtnPrev');
    var dockNext = document.getElementById('dockBtnNext');
    var sidePrev = document.getElementById('pdfSidePrev');
    var sideNext = document.getElementById('pdfSideNext');
    var zoomVal = document.getElementById('dockZoomVal');
    var zoomSep = document.getElementById('dockZoomSep');
    var zIn = document.getElementById('dockBtnZoomIn');
    var zOut = document.getElementById('dockBtnZoomOut');
    var zFit = document.getElementById('dockBtnZoomFit');

    if (isPdf) {
      if (navGroup) navGroup.style.display = 'inline-flex';
      var text = currentPdfPage + ' / ' + totalPdfPages;
      if (navCounter) navCounter.textContent = 'Page ' + text;
      if (dockCounter) dockCounter.textContent = text;
      var triggerPage = document.getElementById('dockTriggerPage');
      if (triggerPage) triggerPage.textContent = text;

      var atFirst = currentPdfPage <= 1;
      var atLast = currentPdfPage >= totalPdfPages;

      if (btnPrev) btnPrev.disabled = atFirst;
      if (btnNext) btnNext.disabled = atLast;
      if (dockPrev) {
        dockPrev.style.display = 'inline-flex';
        dockPrev.disabled = atFirst;
      }
      if (dockNext) {
        dockNext.style.display = 'inline-flex';
        dockNext.disabled = atLast;
      }
      if (dockCounter && dockCounter.parentElement) {
        dockCounter.parentElement.style.display = 'inline-flex';
      }

      // Always show side arrows in PDF presentation mode with prominent disabled styling
      if (sidePrev) {
        sidePrev.style.display = 'flex';
        sidePrev.disabled = atFirst;
        sidePrev.classList.toggle('is-disabled', atFirst);
      }
      if (sideNext) {
        sideNext.style.display = 'flex';
        sideNext.disabled = atLast;
        sideNext.classList.toggle('is-disabled', atLast);
      }

      if (zoomVal) {
        if (currentScaleMode === 'fit-page') zoomVal.textContent = 'Fit';
        else if (currentScaleMode === 'fit-width') zoomVal.textContent = 'Width';
        else zoomVal.textContent = Math.round(currentPdfScale * 100) + '%';
      }
      if (zoomSep) zoomSep.style.display = 'block';
      if (zIn) zIn.style.display = 'inline-flex';
      if (zOut) zOut.style.display = 'inline-flex';
      if (zFit) zFit.style.display = 'inline-flex';
    } else {
      // Non-PDF file
      if (currentPlaylist.length > 1 && currentPlaylistIndex >= 0) {
        if (navGroup) navGroup.style.display = 'inline-flex';
        var text = (currentPlaylistIndex + 1) + ' / ' + currentPlaylist.length;
        if (navCounter) navCounter.textContent = 'Note ' + text;
        if (dockCounter) dockCounter.textContent = text;
        var triggerPage = document.getElementById('dockTriggerPage');
        if (triggerPage) triggerPage.textContent = text;
        var isFirst = currentPlaylistIndex === 0;
        var isLast = currentPlaylistIndex === currentPlaylist.length - 1;
        if (btnPrev) btnPrev.disabled = isFirst;
        if (btnNext) btnNext.disabled = isLast;
        if (dockPrev) {
          dockPrev.style.display = 'inline-flex';
          dockPrev.disabled = isFirst;
        }
        if (dockNext) {
          dockNext.style.display = 'inline-flex';
          dockNext.disabled = isLast;
        }
        if (dockCounter && dockCounter.parentElement) {
          dockCounter.parentElement.style.display = 'inline-flex';
        }
        if (sidePrev) {
          sidePrev.style.display = 'flex';
          sidePrev.disabled = isFirst;
          sidePrev.classList.toggle('is-disabled', isFirst);
        }
        if (sideNext) {
          sideNext.style.display = 'flex';
          sideNext.disabled = isLast;
          sideNext.classList.toggle('is-disabled', isLast);
        }
      } else {
        if (navGroup) navGroup.style.display = 'none';
        if (dockPrev) dockPrev.style.display = 'none';
        if (dockNext) dockNext.style.display = 'none';
        if (dockCounter && dockCounter.parentElement) {
          dockCounter.parentElement.style.display = 'none';
        }
        if (sidePrev) sidePrev.style.display = 'none';
        if (sideNext) sideNext.style.display = 'none';
        var triggerPage = document.getElementById('dockTriggerPage');
        if (triggerPage) triggerPage.textContent = 'Tools';
      }

      if (zoomSep) zoomSep.style.display = 'none';
      if (zIn) zIn.style.display = 'none';
      if (zOut) zOut.style.display = 'none';
      if (zFit) zFit.style.display = 'none';
    }
  }

  function renderPlaylistUI() {
    updatePdfNavigationUI();
  }

  window.pdfNextPage = function () {
    if (currentPdfDoc && currentPdfPage < totalPdfPages) {
      currentPdfPage++;
      queueRenderPdfPage(currentPdfPage);
      var container = document.getElementById('pdfCanvasContainer');
      if (container) container.scrollTop = 0;
    }
  };

  window.pdfPrevPage = function () {
    if (currentPdfDoc && currentPdfPage > 1) {
      currentPdfPage--;
      queueRenderPdfPage(currentPdfPage);
      var container = document.getElementById('pdfCanvasContainer');
      if (container) container.scrollTop = 0;
    }
  };

  window.pdfGoToPage = function (n) {
    n = parseInt(n, 10);
    if (currentPdfDoc && !isNaN(n) && n >= 1 && n <= totalPdfPages) {
      currentPdfPage = n;
      queueRenderPdfPage(currentPdfPage);
      var container = document.getElementById('pdfCanvasContainer');
      if (container) container.scrollTop = 0;
    }
  };

  window.promptGoToPage = function () {
    if (!currentPdfDoc) return;
    var input = prompt('Go to page (1 - ' + totalPdfPages + '):', currentPdfPage);
    if (input !== null) {
      window.pdfGoToPage(input);
    }
  };

  window.pdfZoomIn = function () {
    currentScaleMode = 'custom';
    currentPdfScale = Math.min(3.5, currentPdfScale * 1.2);
    queueRenderPdfPage(currentPdfPage);
  };

  window.pdfZoomOut = function () {
    currentScaleMode = 'custom';
    currentPdfScale = Math.max(0.35, currentPdfScale / 1.2);
    queueRenderPdfPage(currentPdfPage);
  };

  window.pdfZoomFit = function () {
    if (currentScaleMode === 'fit-page') {
      currentScaleMode = 'fit-width';
    } else {
      currentScaleMode = 'fit-page';
    }
    queueRenderPdfPage(currentPdfPage);
  };

  window.dockNextAction = function () {
    if (currentPdfDoc) {
      window.pdfNextPage();
    } else {
      window.previewNextFile();
    }
  };

  window.dockPrevAction = function () {
    if (currentPdfDoc) {
      window.pdfPrevPage();
    } else {
      window.previewPrevFile();
    }
  };

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

  /* ---------------- Zen Focus Mode & Floating Dock Minimize ---------------- */
  var isDockCollapsed = true;

  window.toggleDockCollapse = function (collapse) {
    if (typeof collapse === 'boolean') {
      isDockCollapsed = collapse;
    } else {
      isDockCollapsed = !isDockCollapsed;
    }
    updateDockVisibility();
  };

  function updateDockVisibility() {
    var dock = document.getElementById('previewFloatingDock');
    var trigger = document.getElementById('previewDockTrigger');
    if (!dock) return;

    if (isZenMode) {
      if (isDockCollapsed) {
        dock.style.display = 'none';
        if (trigger) trigger.style.display = 'inline-flex';
      } else {
        dock.style.display = 'flex';
        if (trigger) trigger.style.display = 'none';
      }
    } else {
      dock.style.display = 'none';
      if (trigger) trigger.style.display = 'none';
    }
  }

  window.toggleZenMode = function (force) {
    var shell = document.getElementById('previewShell');
    var btn = document.getElementById('btnZenMode');
    if (!shell) return;

    isZenMode = (typeof force === 'boolean') ? force : !isZenMode;

    if (isZenMode) {
      shell.classList.add('is-zen');
      isDockCollapsed = true; // Minimized by default to bottom-right corner!
      updateDockVisibility();
      if (btn) btn.classList.add('zen-active');

      window.addEventListener('mousemove', handleZenMouseMove);

      if (window.showToast) {
        window.showToast('📺 Zen View: Controls minimized to bottom right. Tap to expand.', 'info', 2600);
      }
    } else {
      shell.classList.remove('is-zen');
      updateDockVisibility();
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
    var isPdf = (mimeType && mimeType.indexOf('pdf') !== -1) || /\.pdf$/i.test(filename);
    var isImg = (mimeType && mimeType.indexOf('image/') === 0) || /\.(png|jpe?g|webp|gif|svg)$/i.test(filename);

    resetPdfState();

    if (isPdf) {
      body.innerHTML =
        '<div class="pdf-viewer-wrap" id="pdfViewerWrap">' +
          '<div class="pdf-loading" id="pdfLoading">' +
            '<div class="pdf-loading-spinner"></div>' +
            '<span>Opening note presentation...</span>' +
          '</div>' +
          '<div class="pdf-canvas-container" id="pdfCanvasContainer" style="display:none;">' +
            '<canvas id="pdfCanvas"></canvas>' +
          '</div>' +
        '</div>';

      if (window.pdfjsLib) {
        try {
          window.pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        } catch (_) {}

        var loadingTask = window.pdfjsLib.getDocument({
          url: url,
          withCredentials: true
        });

        loadingTask.promise.then(function (pdf) {
          currentPdfDoc = pdf;
          totalPdfPages = pdf.numPages;
          currentPdfPage = 1;

          var loadingEl = document.getElementById('pdfLoading');
          if (loadingEl) loadingEl.style.display = 'none';
          var container = document.getElementById('pdfCanvasContainer');
          if (container) {
            container.style.display = 'flex';
            setupPdfTouchGestures(container);
          }

          updatePdfNavigationUI();
          renderPdfPage(1);
        }).catch(function (err) {
          console.warn('PDF.js loading failed, falling back to native iframe:', err);
          fallbackToIframe(body, url, filename, fileId, mimeType);
        });
      } else {
        fallbackToIframe(body, url, filename, fileId, mimeType);
      }
    } else if (isImg) {
      updatePdfNavigationUI();
      body.innerHTML =
        '<img id="previewImg" src="' + url + '" alt="' + filename + '">';
      var img = document.getElementById('previewImg');
      if (img) {
        img.onerror = function () { showFallback(body, filename, fileId, mimeType, 'Could not load image.'); };
      }
    } else {
      updatePdfNavigationUI();
      showFallback(body, filename, fileId, mimeType, 'This file type cannot be previewed in the browser.');
    }
  };

  function fallbackToIframe(body, url, filename, fileId, mimeType) {
    if (!body) return;
    body.innerHTML =
      '<iframe id="previewFrame" src="' + url + '" title="PDF preview"></iframe>';
    watchIframe(document.getElementById('previewFrame'), filename, fileId, mimeType);
  }

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

    resetPdfState();
    isZenMode = false;
    isDockCollapsed = true;
    updateDockVisibility();
    updatePdfNavigationUI();

    // Reset tools
    window.toggleZenMode(false);
    var sidePrev = document.getElementById('pdfSidePrev');
    var sideNext = document.getElementById('pdfSideNext');
    if (sidePrev) sidePrev.style.display = 'none';
    if (sideNext) sideNext.style.display = 'none';

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
      return;
    }
    var dock = document.getElementById('previewFloatingDock');
    var trigger = document.getElementById('previewDockTrigger');
    if (!isZenMode || !dock || isDockCollapsed) return;
    if (dock.contains(e.target) || (trigger && trigger.contains(e.target))) return;
    var sidePrev = document.getElementById('pdfSidePrev');
    var sideNext = document.getElementById('pdfSideNext');
    if ((sidePrev && sidePrev.contains(e.target)) || (sideNext && sideNext.contains(e.target))) return;

    window.toggleDockCollapse(true);
  });

  window.addEventListener('resize', function () {
    if (currentPdfDoc && (currentScaleMode === 'fit-page' || currentScaleMode === 'fit-width')) {
      queueRenderPdfPage(currentPdfPage);
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

    if (kLower === 'm') {
      if (isZenMode) {
        e.preventDefault();
        window.toggleDockCollapse();
      }
    } else if (kLower === 'h' || kLower === 'z') {
      e.preventDefault();
      window.toggleZenMode();
    } else if (kLower === 'f' || kLower === 's') {
      e.preventDefault();
      window.toggleSmartBoardMode();
    } else if (key === 'ArrowRight' || key === ']' || key === 'PageDown' || (key === ' ' && !e.shiftKey)) {
      e.preventDefault();
      window.dockNextAction();
    } else if (key === 'ArrowLeft' || key === '[' || key === 'PageUp' || (key === ' ' && e.shiftKey)) {
      e.preventDefault();
      window.dockPrevAction();
    } else if (key === '+' || key === '=') {
      if (currentPdfDoc) { e.preventDefault(); window.pdfZoomIn(); }
    } else if (key === '-' || key === '_') {
      if (currentPdfDoc) { e.preventDefault(); window.pdfZoomOut(); }
    } else if (kLower === '0' || kLower === 'w') {
      if (currentPdfDoc) { e.preventDefault(); window.pdfZoomFit(); }
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
