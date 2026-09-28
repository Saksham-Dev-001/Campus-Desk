/* =====================================================================
   CampusDesk - Cards: menu (right), long-press mobile, select mode
   ===================================================================== */
(function () {
  'use strict';

  var selection = { folders: {}, files: {} };
  var selectMode = false;

  function total() {
    return Object.keys(selection.folders).length +
           Object.keys(selection.files).length;
  }

  /* --------------------------------------------------------------
     Navigate helper (used by menu items)
     -------------------------------------------------------------- */
  window.navigateTo = function (url) {
    window.closeAllMenus();
    window.location.href = url;
  };

  /* --------------------------------------------------------------
     Card menus
     -------------------------------------------------------------- */
  window.closeAllMenus = function () {
    document.querySelectorAll('.fcard-menu.open').forEach(function (m) {
      m.classList.remove('open');
    });
    document.querySelectorAll('.fcard.menu-active').forEach(function (c) {
      c.classList.remove('menu-active');
    });
    document.body.classList.remove('card-menu-open');
  };

  window.toggleCardMenu = function (btn, event) {
    if (event) { event.stopPropagation(); event.preventDefault(); }
    var menu = btn.closest('.fcard-menu');
    var card = btn.closest('.fcard');
    if (!menu) return;
    var wasOpen = menu.classList.contains('open');
    window.closeAllMenus();
    if (!wasOpen) {
      menu.classList.add('open');
      if (card) card.classList.add('menu-active');
      document.body.classList.add('card-menu-open');
    }
  };

  // Close menu on outside click
  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('.fcard-menu')) {
      window.closeAllMenus();
    }
  });

  // Close menu on scroll (feels natural on mobile)
  window.addEventListener('scroll', function () {
    if (document.body.classList.contains('card-menu-open')) {
      window.closeAllMenus();
    }
  }, { passive: true });

  /* --------------------------------------------------------------
     LONG-PRESS on mobile → opens the menu
     -------------------------------------------------------------- */
  var LONG_PRESS_MS = 480;
  var longPressTimer = null;
  var longPressTriggered = false;

  function attachLongPress(card) {
    if (card.dataset.lpAttached === '1') return;
    card.dataset.lpAttached = '1';

    card.addEventListener('touchstart', function (e) {
      // Ignore if user is in select mode
      if (document.body.classList.contains('select-mode')) return;
      // Ignore touches on interactive elements
      if (e.target.closest('button, a, input, .fcard-check, .fcard-menu')) return;

      longPressTriggered = false;
      longPressTimer = setTimeout(function () {
        longPressTriggered = true;

        // Haptic feedback (if supported)
        if (navigator.vibrate) navigator.vibrate(15);

        // Open the menu
        var menu = card.querySelector('.fcard-menu');
        if (menu) {
          window.closeAllMenus();
          menu.classList.add('open');
          card.classList.add('menu-active');
          document.body.classList.add('card-menu-open');

          // iOS-style context menu position — we use fixed bottom sheet on mobile
        }
      }, LONG_PRESS_MS);
    }, { passive: true });

    card.addEventListener('touchend', function (e) {
      clearTimeout(longPressTimer);
      if (longPressTriggered) {
        // Prevent the tap from triggering navigation
        e.preventDefault();
        longPressTriggered = false;
      }
    });

    card.addEventListener('touchmove', function () {
      clearTimeout(longPressTimer);
    }, { passive: true });

    card.addEventListener('touchcancel', function () {
      clearTimeout(longPressTimer);
      longPressTriggered = false;
    });
  }

  // Card click → navigate (folders only) or nothing (files)
  function attachCardClick(card) {
    if (card.dataset.clickAttached === '1') return;
    card.dataset.clickAttached = '1';

    card.addEventListener('click', function (e) {
      // Ignore clicks inside menu, buttons, checkboxes
      if (e.target.closest('.fcard-menu, .fbtn, .fcard-check, button, a, input')) return;
      // Ignore in select mode
      if (document.body.classList.contains('select-mode')) return;
      // Ignore if long-press just fired
      if (longPressTriggered) return;

      var href = card.dataset.href;
      if (href) window.location.href = href;
    });
  }

  /* --------------------------------------------------------------
     Select mode
     -------------------------------------------------------------- */
  function updateSelectBtn() {
    var btn = document.getElementById('selectModeBtn');
    if (!btn) return;
    var label = btn.querySelector('span');
    if (selectMode) {
      btn.classList.remove('outline');
      if (label) label.textContent = 'Done';
    } else {
      btn.classList.add('outline');
      if (label) label.textContent = 'Select';
    }
  }

  window.toggleSelectMode = function () {
    selectMode = !selectMode;
    document.body.classList.toggle('select-mode', selectMode);
    if (!selectMode) window.clearSelection();
    updateSelectBtn();
  };

  window.enterSelectMode = function () {
    if (!selectMode) {
      selectMode = true;
      document.body.classList.add('select-mode');
      updateSelectBtn();
    }
  };

  window.exitSelectMode = function () {
    if (selectMode) {
      selectMode = false;
      document.body.classList.remove('select-mode');
      window.clearSelection();
      updateSelectBtn();
    }
  };

  window.selectFromMenu = function (id, kind) {
    window.closeAllMenus();
    window.enterSelectMode();
    var cb = document.querySelector('.sel-check[data-kind="' + kind + '"][data-id="' + id + '"]');
    if (cb) {
      cb.checked = true;
      var bucket = kind === 'folder' ? selection.folders : selection.files;
      bucket[String(id)] = true;
      updateBar();
    }
  };

  /* --------------------------------------------------------------
     Selection state
     -------------------------------------------------------------- */
  function updateBar() {
    var n = total();
    var bar = document.getElementById('selBar');
    var cnt = document.getElementById('selCount');
    if (cnt) cnt.textContent = n;

    if (bar) {
      if (n > 0) bar.classList.add('show');
      else bar.classList.remove('show');
    }

    document.querySelectorAll('.sel-check').forEach(function (cb) {
      var kind = cb.dataset.kind;
      var id = String(cb.dataset.id);
      var checked = selection[kind + 's'] && selection[kind + 's'][id];
      cb.checked = !!checked;
      var card = cb.closest('.fcard');
      if (card) {
        if (checked) card.classList.add('selected');
        else card.classList.remove('selected');
      }
    });
  }

  window.toggleSelect = function (cb, event) {
    if (event) event.stopPropagation();
    var kind = cb.dataset.kind;
    var id = String(cb.dataset.id);
    var bucket = kind === 'folder' ? selection.folders : selection.files;
    if (cb.checked) bucket[id] = true;
    else delete bucket[id];
    updateBar();
  };

  window.selectAllVisible = function () {
    document.querySelectorAll('.sel-check').forEach(function (cb) {
      cb.checked = true;
      var kind = cb.dataset.kind;
      var id = String(cb.dataset.id);
      var bucket = kind === 'folder' ? selection.folders : selection.files;
      bucket[id] = true;
    });
    updateBar();
  };

  window.clearSelection = function () {
    selection.folders = {};
    selection.files = {};
    document.querySelectorAll('.sel-check').forEach(function (cb) { cb.checked = false; });
    document.querySelectorAll('.fcard.selected').forEach(function (c) { c.classList.remove('selected'); });
    updateBar();
  };

  window.bulkDelete = function () {
    var folderIds = Object.keys(selection.folders);
    var fileIds = Object.keys(selection.files);
    if (!folderIds.length && !fileIds.length) return;

    var n = folderIds.length + fileIds.length;
    var msg = 'Delete ' + n + ' item' + (n === 1 ? '' : 's') + '?\n\n';
    if (folderIds.length) {
      msg += '⚠️ ' + folderIds.length + ' folder(s) will be deleted with ALL their contents.\n';
    }
    msg += '\nThis cannot be undone.';
    if (!confirm(msg)) return;

    var csrf = document.querySelector('input[name="csrf_token"]');
    fetch('/bulk-delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrf ? csrf.value : ''
      },
      credentials: 'same-origin',
      body: JSON.stringify({
        folder_ids: folderIds.map(Number),
        file_ids: fileIds.map(Number)
      })
    })
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (data) {
        if (data && data.ok) {
          if (window.showToast) window.showToast(data.message || 'Deleted.', 'success');
          setTimeout(function () { window.location.reload(); }, 400);
        } else {
          if (window.showToast) window.showToast((data && data.message) || 'Delete failed.', 'error');
        }
      })
      .catch(function () {
        if (window.showToast) window.showToast('Network error while deleting.', 'error');
      });
  };

  /* --------------------------------------------------------------
     Share sheet
     -------------------------------------------------------------- */
  var currentShare = { type: null, id: null, name: '', mime: '' };

  window.shareItem = function (type, id, name, mime) {
    window.closeAllMenus();
    currentShare = { type: type, id: id, name: name, mime: mime || '' };

    var back = document.getElementById('shareBack');
    if (!back) return;

    var nameEl = document.getElementById('shareName');
    var metaEl = document.getElementById('shareMeta');
    var linkEl = document.getElementById('shareLink');

    var url = type === 'file'
      ? window.location.origin + '/files/' + id + '/download'
      : window.location.origin + '/files?folder_id=' + id;

    if (nameEl) nameEl.textContent = name;
    if (metaEl) metaEl.textContent = type === 'folder' ? 'Folder' : (mime || 'File');
    if (linkEl) linkEl.value = url;

    var wa = document.getElementById('shareWA');
    if (wa) wa.href = 'https://wa.me/?text=' + encodeURIComponent(name + '\n' + url);

    var tg = document.getElementById('shareTelegram');
    if (tg) tg.href = 'https://t.me/share/url?url=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(name);

    var mail = document.getElementById('shareMail');
    if (mail) mail.href = 'mailto:?subject=' + encodeURIComponent(name) + '&body=' + encodeURIComponent('Check out this file:\n' + url);

    back.classList.add('show');
    document.body.style.overflow = 'hidden';
  };

  window.closeShare = function () {
    var back = document.getElementById('shareBack');
    if (!back) return;
    back.classList.remove('show');
    document.body.style.overflow = '';
  };

  window.copyShareLink = function (ev) {
    var linkEl = document.getElementById('shareLink');
    if (!linkEl) return;
    linkEl.select();
    linkEl.setSelectionRange(0, 99999);

    var done = function () {
      if (window.showToast) window.showToast('Link copied to clipboard', 'success');
      if (ev && ev.target) {
        var btn = ev.target.closest('button');
        if (btn) {
          var orig = btn.innerHTML;
          btn.innerHTML = '✓ Copied';
          setTimeout(function () { btn.innerHTML = orig; }, 1500);
        }
      }
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(linkEl.value).then(done).catch(function () {
        try { document.execCommand('copy'); done(); } catch (e) {}
      });
    } else {
      try { document.execCommand('copy'); done(); } catch (e) {}
    }
  };

  window.nativeShare = function () {
    var linkEl = document.getElementById('shareLink');
    if (!linkEl) return;
    var url = linkEl.value;
    var name = currentShare.name || 'CampusDesk file';
    if (navigator.share) {
      navigator.share({ title: name, text: name, url: url }).catch(function () {});
    } else {
      window.copyCopyShareLinkFallback(url);
    }
  };
  window.copyCopyShareLinkFallback = function () { window.copyShareLink(); };

  document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'shareBack') window.closeShare();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      window.closeAllMenus();
      var back = document.getElementById('shareBack');
      if (back && back.classList.contains('show')) {
        window.closeShare();
        return;
      }
      if (total() > 0) window.clearSelection();
      if (selectMode) window.exitSelectMode();
    }
  });

  /* --------------------------------------------------------------
     Boot
     -------------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    updateBar();
    document.querySelectorAll('.fcard').forEach(function (card) {
      attachLongPress(card);
      attachCardClick(card);
    });
  });
})();
