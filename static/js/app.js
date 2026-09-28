/* =====================================================================
   CampusDesk - UI helpers
     * mobile sidebar drawer
     * modals
     * cascading targeting dropdowns (client-side, instant)
   ===================================================================== */

/* ---------------- Mobile sidebar drawer ---------------- */
function openSidebar() {
  var s = document.getElementById('sidebar');
  var b = document.getElementById('sidebarBackdrop');
  if (s) s.classList.add('open');
  if (b) b.classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeSidebar() {
  var s = document.getElementById('sidebar');
  var b = document.getElementById('sidebarBackdrop');
  if (s) s.classList.remove('open');
  if (b) b.classList.remove('show');
  document.body.style.overflow = '';
}
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('.sidebar .nav a');
  if (a && window.innerWidth <= 900) closeSidebar();
});

/* ---------------- Modals ---------------- */
function openModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('show');
  document.body.style.overflow = '';
}
document.addEventListener('click', function (e) {
  if (e.target.classList && e.target.classList.contains('modal-back')) {
    e.target.classList.remove('show');
    document.body.style.overflow = '';
  }
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-back.show').forEach(function (m) {
      m.classList.remove('show');
    });
    document.body.style.overflow = '';
    closeSidebar();
  }
});

/* =====================================================================
   Cascading targeting dropdowns (client-side)
   -----------------------------------------------------------------
   Data is baked into the page from the server. We filter existing
   <option> elements by their data-* attributes. No network calls.

   Rules:
     Course       -> filters Branch
     Course+Year  -> filters Section
     Section      -> filters Batch
     Branch+Sem   -> filters Subject
   When a parent changes, the child selection is cleared and
   the child list is re-filtered. Children of children also reset.
   ===================================================================== */

function _setOptions(sel, predicate) {
  /* Show/hide options matching predicate. Returns count of visible. */
  if (!sel) return 0;
  var visible = 0;
  Array.from(sel.options).forEach(function (opt) {
    if (opt.value === '') return; // keep placeholder
    var ok = predicate(opt);
    opt.hidden = !ok;
    opt.disabled = !ok;
    if (ok) visible++;
  });
  return visible;
}

function _clearSelection(sel) {
  if (sel) sel.value = '';
}

function _safeVal(sel) {
  return sel ? (sel.value || '') : '';
}

function cascadeTargetingForm(scope) {
  var courseSel   = scope.querySelector('.target-course');
  var branchSel   = scope.querySelector('.target-branch');
  var yearSel     = scope.querySelector('.target-year');
  var semesterSel = scope.querySelector('.target-semester');
  var sectionSel  = scope.querySelector('.target-section');
  var batchSel    = scope.querySelector('.target-batch');
  var subjectSel  = scope.querySelector('.target-subject');
  if (!courseSel && !branchSel) return;

  /* -------- filter functions -------- */
  function filterBranches() {
    var cid = _safeVal(courseSel);
    return _setOptions(branchSel, function (opt) {
      if (!cid) return true;
      return opt.dataset.courseId === cid;
    });
  }
  function filterSections() {
    var bid = _safeVal(branchSel);
    var yid = _safeVal(yearSel);
    return _setOptions(sectionSel, function (opt) {
      if (bid && opt.dataset.branchId !== bid) return false;
      if (yid && opt.dataset.yearId !== yid) return false;
      return true;
    });
  }
  function filterBatches() {
    var sid = _safeVal(sectionSel);
    return _setOptions(batchSel, function (opt) {
      if (!sid) return true;
      return opt.dataset.sectionId === sid;
    });
  }
  function filterSubjects() {
    var bid = _safeVal(branchSel);
    var sid = _safeVal(semesterSel);
    return _setOptions(subjectSel, function (opt) {
      var sb = opt.dataset.branchId || '';
      var ss = opt.dataset.semesterId || '';
      if (bid && sb && sb !== bid) return false;
      if (sid && ss && ss !== sid) return false;
      return true;
    });
  }

  /* -------- helpers to reset children -------- */
  function resetBranch()  { _clearSelection(branchSel);  resetSection(); resetSubjects(); }
  function resetSection() { _clearSelection(sectionSel); resetBatch(); }
  function resetBatch()   { _clearSelection(batchSel); }
  function resetSubjects(){ _clearSelection(subjectSel); }

  /* -------- wire change handlers -------- */
  if (courseSel) {
    courseSel.addEventListener('change', function () {
      resetBranch();
      filterBranches();
    });
  }
  if (branchSel) {
    branchSel.addEventListener('change', function () {
      resetSection();
      resetSubjects();
      filterSections();
      filterSubjects();
    });
  }
  if (yearSel) {
    yearSel.addEventListener('change', function () {
      resetSection();
      filterSections();
    });
  }
  if (semesterSel) {
    semesterSel.addEventListener('change', function () {
      resetSubjects();
      filterSubjects();
    });
  }
  if (sectionSel) {
    sectionSel.addEventListener('change', function () {
      resetBatch();
      filterBatches();
    });
  }

  /* -------- initial pass (respects any server-pre-selected values) -------- */
  // Preserve the current values so filtering doesn't clear a pre-selected
  // child just because its parent was rendered empty.
  var keepBranch   = branchSel   ? branchSel.value   : '';
  var keepSection  = sectionSel  ? sectionSel.value  : '';
  var keepBatch    = batchSel    ? batchSel.value    : '';
  var keepSubject  = subjectSel  ? subjectSel.value  : '';

  filterBranches();
  filterSections();
  filterBatches();
  filterSubjects();

  // Restore if still visible
  function restore(sel, value) {
    if (!sel || !value) return;
    var match = Array.from(sel.options).find(function (o) {
      return o.value === value && !o.disabled;
    });
    if (match) sel.value = value;
  }
  restore(branchSel, keepBranch);
  restore(sectionSel, keepSection);
  restore(batchSel, keepBatch);
  restore(subjectSel, keepSubject);
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.modal form').forEach(function (form) {
    if (form.querySelector('.target-course')) {
      cascadeTargetingForm(form);
    }
  });

  document.querySelectorAll('.flash').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 5000);
  });
});

/* ---------------- Mobile PWA / Anti-Zoom Guard ---------------- */
(function () {
  // Prevent multi-touch pinch zoom on mobile devices and installed PWA
  document.addEventListener('gesturestart', function (e) {
    e.preventDefault();
  }, { passive: false });
  document.addEventListener('gesturechange', function (e) {
    e.preventDefault();
  }, { passive: false });
  document.addEventListener('gestureend', function (e) {
    e.preventDefault();
  }, { passive: false });

  // Prevent double-tap zoom while keeping normal fast tap interactions
  var lastTouchEnd = 0;
  document.addEventListener('touchend', function (e) {
    var now = Date.now();
    if (now - lastTouchEnd <= 300) {
      var tag = e.target && e.target.tagName;
      if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
        e.preventDefault();
      }
    }
    lastTouchEnd = now;
  }, { passive: false });
})();
