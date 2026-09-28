/* CampusDesk - Teachers bulk actions + 3-dot menu (v2) */
(function () {
  'use strict';
  var active = false;
  function cbs() { return document.querySelectorAll('.tch-cb'); }
  function update() {
    var n = 0;
    cbs().forEach(function (cb) {
      if (cb.checked) n++;
      var tr = cb.closest('tr');
      if (tr) tr.classList.toggle('tch-selected', cb.checked);
    });
    var cnt = document.getElementById('teacherSelCount');
    if (cnt) cnt.textContent = n;
    var bar = document.getElementById('teacherSelBar');
    if (bar) bar.classList.toggle('show', n > 0);
  }
  function enterSelectMode() {
    if (active) return;
    active = true;
    document.body.classList.add('tch-select-mode');
    var lbl = document.getElementById('th-menu-select-label');
    if (lbl) lbl.textContent = 'Exit selection';
  }
  function exitSelectMode() {
    if (!active) return;
    active = false;
    document.body.classList.remove('tch-select-mode');
    var lbl = document.getElementById('th-menu-select-label');
    if (lbl) lbl.textContent = 'Select multiple';
    cbs().forEach(function (cb) { cb.checked = false; });
    update();
  }
  window.toggleTeacherMenu = function (e) {
    if (e) e.stopPropagation();
    var w = document.getElementById('thMenuWrap');
    if (!w) return;
    w.classList.toggle('open');
  };
  window.closeTeacherMenu = function () {
    var w = document.getElementById('thMenuWrap');
    if (w) w.classList.remove('open');
  };
  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('#thMenuWrap')) closeTeacherMenu();
  });
  window.toggleTeacherSelect = function () {
    if (active) exitSelectMode(); else enterSelectMode();
    update();
    closeTeacherMenu();
  };
  window.exitTeacherSelect = exitSelectMode;
  window.teacherSelectAll = function () {
    enterSelectMode();           // <<< PEHLE mode on karo (ticks visible ho)
    cbs().forEach(function (cb) { cb.checked = true; });
    update();
    closeTeacherMenu();
  };
  window.teacherSelectionChanged = update;
  window.teacherBulkDelete = function () {
    closeTeacherMenu();
    var ids = [];
    cbs().forEach(function (cb) { if (cb.checked) ids.push(parseInt(cb.value, 10)); });
    if (!ids.length) {
      if (window.showToast) window.showToast('Pehle koi teacher select karo', 'info');
      else alert('Pehle koi teacher select karo');
      return;
    }
    if (!confirm('Delete ' + ids.length + ' teacher(s)?\n\nBranch assignments bhi hat jayenge.')) return;
    var csrf = document.querySelector('input[name="csrf_token"]');
    fetch('/admin/teachers/bulk-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
                 'X-Requested-With': 'XMLHttpRequest',
                 'X-CSRFToken': csrf ? csrf.value : '' },
      credentials: 'same-origin',
      body: JSON.stringify({ user_ids: ids })
    }).then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (d) {
        if (d && d.ok) {
          if (window.showToast) window.showToast(d.message, 'success');
          setTimeout(function () { window.location.reload(); }, 400);
        } else if (window.showToast) {
          window.showToast((d && d.message) || 'Delete failed', 'error');
        }
      }).catch(function () {
        if (window.showToast) window.showToast('Network error', 'error');
      });
  };
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeTeacherMenu(); exitSelectMode(); }
  });
  document.addEventListener('DOMContentLoaded', update);
})();
