/* =====================================================================
   CampusDesk - Modern drop zone for file inputs
   Replaces the default ugly <input type="file"> with a drag-and-drop
   card that shows file name, size, icon, and a remove button.

   Usage in HTML:
     <label class="drop-zone" data-accept=".pdf,.doc,.docx">
       <input type="file" name="file" accept=".pdf,.doc,.docx" required>
       <div class="dz-empty">
         <div class="dz-icon">📄</div>
         <div class="dz-text">Drop your file here</div>
         <div class="dz-hint">or <span class="dz-browse">browse</span> · PDF, DOC up to 25 MB</div>
       </div>
       <div class="dz-progress"></div>
     </label>
   ===================================================================== */
(function () {
  'use strict';

  var ICONS = {
    pdf: '📕',
    doc: '📘', docx: '📘', odt: '📘', rtf: '📘',
    xls: '📗', xlsx: '📗', csv: '📗', ods: '📗',
    ppt: '📙', pptx: '📙', odp: '📙',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', webp: '🖼️', svg: '🖼️',
    zip: '🗜️', rar: '🗜️', '7z': '🗜️', tar: '🗜️', gz: '🗜️',
    txt: '📄', md: '📄', json: '📄', xml: '📄',
    mp4: '🎬', mov: '🎬', avi: '🎬', mkv: '🎬',
    mp3: '🎵', wav: '🎵', ogg: '🎵'
  };

  function getIcon(filename) {
    if (!filename || filename.indexOf('.') === -1) return '📄';
    var ext = filename.split('.').pop().toLowerCase();
    return ICONS[ext] || '📄';
  }

  function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    if (!bytes) return '';
    var k = 1024;
    var sizes = ['B', 'KB', 'MB', 'GB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1) + ' ' + sizes[i];
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function initZone(zone) {
    if (zone.dataset.dzInit === '1') return;
    zone.dataset.dzInit = '1';

    var input = zone.querySelector('input[type="file"]');
    if (!input) return;

    var empty = zone.querySelector('.dz-empty');
    var progress = zone.querySelector('.dz-progress');

    function showFile(file) {
      zone.classList.add('has-file');
      // Build file card
      var existing = zone.querySelector('.dz-file');
      if (existing) existing.remove();

      var card = document.createElement('div');
      card.className = 'dz-file';
      card.innerHTML =
        '<div class="dz-file-icon">' + getIcon(file.name) + '</div>' +
        '<div class="dz-file-info">' +
          '<div class="dz-file-name">' + escapeHtml(file.name) + '</div>' +
          '<div class="dz-file-meta">' + formatSize(file.size) + ' · ' +
            (file.type || 'unknown type') + '</div>' +
        '</div>' +
        '<button type="button" class="dz-remove" aria-label="Remove file">✕</button>';

      zone.appendChild(card);
      if (empty) empty.style.display = 'none';

      card.querySelector('.dz-remove').addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        clearFile();
      });
    }

    function clearFile() {
      input.value = '';
      zone.classList.remove('has-file');
      var card = zone.querySelector('.dz-file');
      if (card) card.remove();
      if (empty) empty.style.display = '';
    }

    // ---- Click to open file picker ----
    zone.addEventListener('click', function (e) {
      // If they clicked the remove button, don't reopen
      if (e.target.classList && e.target.classList.contains('dz-remove')) return;
      // If a file is already selected, clicking the zone lets them pick a new one
      input.click();
    });

    // ---- Native change ----
    input.addEventListener('change', function () {
      if (input.files && input.files[0]) {
        showFile(input.files[0]);
      } else {
        clearFile();
      }
    });

    // ---- Drag & drop ----
    ['dragenter', 'dragover'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add('dragging');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('dragging');
      });
    });
    zone.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;

      // Filter by accept attribute if present
      var accept = (input.getAttribute('accept') || '').split(',').map(function (s) {
        return s.trim().toLowerCase();
      }).filter(Boolean);

      var file = files[0];
      if (accept.length) {
        var name = file.name.toLowerCase();
        var ok = accept.some(function (rule) {
          if (rule.startsWith('.')) return name.endsWith(rule);
          if (rule.indexOf('/') !== -1) return file.type.startsWith(rule.split('/')[0]);
          return false;
        });
        if (!ok) {
          zone.classList.add('shake');
          setTimeout(function () { zone.classList.remove('shake'); }, 500);
          if (window.showToast) {
            window.showToast('File type not allowed.', 'error');
          }
          return;
        }
      }

      // Assign the dropped file to the input via DataTransfer
      try {
        var dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
      } catch (err) {
        // Fallback for older browsers: show card but warn
        console.warn('[CampusDesk] Cannot programmatically set file. Browsers may block.', err);
      }
      showFile(file);
    });

    // Form submit feedback
    var form = zone.closest('form');
    if (form) {
      form.addEventListener('submit', function () {
        if (input.files && input.files[0] && progress) {
          progress.classList.add('active');
        }
      });
    }

    // Prepopulate if input already has a file (rare, after redirect)
    if (input.files && input.files[0]) {
      showFile(input.files[0]);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.drop-zone').forEach(initZone);
  });
})();
