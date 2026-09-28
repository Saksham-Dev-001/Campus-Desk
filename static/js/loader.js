/* =====================================================================
   CampusDesk — Global loading overlay
   Usage:
     cdLoader.show('Deleting…', 'full_spec.md', 'danger');
     cdLoader.show('Uploading…', 'unit 1.pdf');
     cdLoader.hide();
     cdLoader.success('Deleted!');   // green flash, auto-hide
   ===================================================================== */
(function () {
  'use strict';

  function ensure() {
    var el = document.getElementById('cdLoader');
    if (el) return el;

    el = document.createElement('div');
    el.id = 'cdLoader';
    el.className = 'cd-loader';
    el.innerHTML =
      '<div class="cd-loader-card">' +
        '<div class="cd-spinner">' +
          '<svg viewBox="0 0 50 50" fill="none">' +
            '<circle cx="25" cy="25" r="20" stroke="currentColor" ' +
              'stroke-width="4" opacity="0.15" ' +
              'style="stroke: var(--accent, #4c74ff);" />' +
            '<circle cx="25" cy="25" r="20" stroke="currentColor" ' +
              'stroke-width="4" />' +
          '</svg>' +
          '<div class="cd-spinner-icon" id="cdLoaderIcon">⏳</div>' +
        '</div>' +
        '<h3 class="cd-loader-title" id="cdLoaderTitle">Loading…</h3>' +
        '<p class="cd-loader-sub" id="cdLoaderSub"></p>' +
        '<div class="cd-loader-bar"></div>' +
      '</div>';
    document.body.appendChild(el);
    return el;
  }

  var ICONS = {
    delete: '🗑️',
    upload: '⬆️',
    save: '💾',
    download: '⬇️',
    send: '📤',
    default: '⏳',
  };

  var _timer = null;

  window.cdLoader = {
    show: function (title, sub, variant) {
      var el = ensure();
      var titleEl = document.getElementById('cdLoaderTitle');
      var subEl = document.getElementById('cdLoaderSub');
      var iconEl = document.getElementById('cdLoaderIcon');

      if (titleEl) titleEl.textContent = title || 'Loading…';
      if (subEl) {
        subEl.textContent = sub || '';
        subEl.style.display = sub ? '' : 'none';
      }

      // Reset classes
      el.classList.remove('danger', 'success', 'show');

      var v = (variant || '').toLowerCase();
      if (v === 'danger' || v === 'delete') {
        el.classList.add('danger');
        if (iconEl) iconEl.textContent = ICONS.delete;
      } else if (v === 'upload') {
        if (iconEl) iconEl.textContent = ICONS.upload;
      } else if (v === 'save') {
        if (iconEl) iconEl.textContent = ICONS.save;
      } else if (v === 'download') {
        if (iconEl) iconEl.textContent = ICONS.download;
      } else if (v === 'send') {
        if (iconEl) iconEl.textContent = ICONS.send;
      } else {
        if (iconEl) iconEl.textContent = ICONS.default;
      }

      // Force reflow so transitions fire
      void el.offsetHeight;
      el.classList.add('show');

      // Safety timeout — auto-hide after 20s in case something breaks
      clearTimeout(_timer);
      _timer = setTimeout(function () {
        window.cdLoader.hide();
      }, 20000);
    },

    hide: function () {
      var el = document.getElementById('cdLoader');
      if (!el) return;
      el.classList.remove('show', 'danger', 'success');
      clearTimeout(_timer);
    },

    success: function (msg, delay) {
      var el = ensure();
      var titleEl = document.getElementById('cdLoaderTitle');
      var subEl = document.getElementById('cdLoaderSub');
      var iconEl = document.getElementById('cdLoaderIcon');

      if (titleEl) titleEl.textContent = msg || 'Done!';
      if (subEl) { subEl.textContent = ''; subEl.style.display = 'none'; }
      if (iconEl) iconEl.textContent = '✓';

      el.classList.remove('danger', 'show');
      el.classList.add('success', 'show');

      setTimeout(function () {
        window.cdLoader.hide();
      }, delay || 700);
    },
  };

  /* ---------------------------------------------------------------
     Auto-show on delete/upload form submits
     --------------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    // Delete confirmation form
    var deleteForm = document.getElementById('deleteForm');
    if (deleteForm) {
      deleteForm.addEventListener('submit', function () {
        var nameEl = document.getElementById('deleteItemName');
        var name = nameEl ? nameEl.textContent.trim() : '';
        window.cdLoader.show('Deleting…', name || 'Please wait', 'danger');
      });
    }

    // Replace file form
    var replaceForm = document.getElementById('replaceForm');
    if (replaceForm) {
      replaceForm.addEventListener('submit', function () {
        window.cdLoader.show('Replacing…', 'Uploading new version', 'upload');
      });
    }

    // Folder delete form — any form whose action ends with /delete and is inside a card or modal
    document.querySelectorAll('form[action$="/delete"]').forEach(function (f) {
      if (f.id === 'deleteForm') return; // already handled
      f.addEventListener('submit', function () {
        window.cdLoader.show('Deleting…', 'Please wait', 'danger');
      });
    });

    // Folder delete from cards (form with action containing /folders/X/delete)
    document.querySelectorAll('form[action*="/folders/"]').forEach(function (f) {
      if (f.action.indexOf('/delete') === -1) return;
      f.addEventListener('submit', function () {
        window.cdLoader.show('Deleting folder…', 'Removing all contents', 'danger');
      });
    });
  });
})();
