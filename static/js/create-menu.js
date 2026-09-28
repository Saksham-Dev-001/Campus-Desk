/* =====================================================================
   CampusDesk - YouTube-style Create menu
   ===================================================================== */
(function () {
  'use strict';

  window.openCreateMenu = function (e) {
    if (e) e.preventDefault();
    var m = document.getElementById('createBack');
    if (!m) return;
    m.classList.add('show');
    document.body.style.overflow = 'hidden';
  };

  window.closeCreateMenu = function () {
    var m = document.getElementById('createBack');
    if (!m) return;
    m.classList.remove('show');
    document.body.style.overflow = '';
  };

  // Close on backdrop click
  document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'createBack') {
      window.closeCreateMenu();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var m = document.getElementById('createBack');
      if (m && m.classList.contains('show')) {
        window.closeCreateMenu();
      }
    }
  });

  // ---------------------------------------------------------------
  // Auto-open modals when a page is loaded with ?new=1 (or ?new=assign)
  // ---------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var params = new URLSearchParams(window.location.search);
    var flag = params.get('new');
    if (!flag) return;

    var targetId = null;

    // Map ?new=… values to modal IDs on the target pages
    if (flag === '1' || flag === 'notice' || flag === 'announcement') {
      targetId = 'noticeModal';
    } else if (flag === 'assign' || flag === 'assignment') {
      targetId = 'assignModal';
    } else if (flag === 'material' || flag === 'upload') {
      targetId = 'uploadModal';
    } else if (flag === 'folder') {
      targetId = 'folderModal';
    } else if (flag === 'official') {
      targetId = 'officialModal';
    } else if (flag === 'bulk') {
      targetId = 'bulkModal';
    } else if (flag === 'entry' || flag === 'timetable') {
      targetId = 'ttModal';
    } else if (flag === 'request') {
      targetId = 'reqModal';
    }

    if (targetId) {
      // Give the page a moment to finish rendering
      setTimeout(function () {
        if (window.openModal) {
          window.openModal(targetId);
        }
        // Clean the query param from the URL so refresh doesn't re-trigger
        try {
          var url = new URL(window.location.href);
          url.searchParams.delete('new');
          window.history.replaceState({}, '', url.toString());
        } catch (err) { /* ignore */ }
      }, 120);
    }
  });
})();
