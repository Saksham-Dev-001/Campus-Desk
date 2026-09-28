/* =====================================================================
   CampusDesk — Live timetable + view switching
   ===================================================================== */
(function () {
  'use strict';

  function pad(n) { return n < 10 ? '0' + n : String(n); }

  function toMin(hhmm) {
    var parts = String(hhmm || '').split(':');
    if (parts.length < 2) return NaN;
    var h = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return NaN;
    return h * 60 + m;
  }

  /* --------------------------------------------------------------
     Live clock
     -------------------------------------------------------------- */
  function updateClock() {
    var d = new Date();
    var h = d.getHours(), m = d.getMinutes(), s = d.getSeconds();
    var ampm = h >= 12 ? 'PM' : 'AM';
    var h12 = h % 12; if (h12 === 0) h12 = 12;

    var t = document.getElementById('clockTime');
    var a = document.getElementById('clockAmPm');
    var c = document.getElementById('clockSec');
    if (t) t.textContent = h12 + ':' + pad(m);
    if (a) a.textContent = ampm;
    if (c) c.textContent = ':' + pad(s);
  }

  /* --------------------------------------------------------------
     Roadmap state
     -------------------------------------------------------------- */
  function updateRoadmap() {
    var nodes = document.querySelectorAll('#roadmap .tt-node');
    if (!nodes.length) return;

    var d = new Date();
    var currentMin = d.getHours() * 60 + d.getMinutes() + d.getSeconds() / 60;

    var nowNode = null, nextNode = null;

    nodes.forEach(function (node) {
      var startM = toMin(node.dataset.start);
      var endM = toMin(node.dataset.end);
      node.classList.remove('past', 'now', 'next');
      if (isNaN(startM) || isNaN(endM)) return;

      if (currentMin >= endM) node.classList.add('past');
      else if (currentMin >= startM && currentMin < endM) {
        node.classList.add('now'); nowNode = node;
      } else if (!nextNode && currentMin < startM) {
        node.classList.add('next'); nextNode = node;
      }
    });

    document.querySelectorAll('#roadmap .tt-progress').forEach(function (p) { p.style.display = 'none'; });
    document.querySelectorAll('#roadmap .tt-progress-label').forEach(function (l) { l.style.display = 'none'; });

    if (nowNode) {
      var s = toMin(nowNode.dataset.start);
      var e = toMin(nowNode.dataset.end);
      var done = currentMin - s;
      var pct = Math.max(0, Math.min(100, (done / (e - s)) * 100));

      var bar = nowNode.querySelector('.tt-progress');
      var fill = nowNode.querySelector('.tt-progress-fill');
      var lbl = nowNode.querySelector('.tt-progress-label');
      var el = nowNode.querySelector('.elapsed');
      var rm = nowNode.querySelector('.remaining');
      if (bar) bar.style.display = 'block';
      if (fill) fill.style.width = pct + '%';
      if (lbl) lbl.style.display = 'flex';

      var minLeft = Math.max(0, Math.ceil(e - currentMin));
      if (el) el.textContent = Math.round(done) + ' min in';
      if (rm) rm.textContent = minLeft <= 1 ? 'ending now' : minLeft + ' min left';
    }

    updateStatus(nowNode, nextNode, currentMin, nodes);
  }

  function updateStatus(nowNode, nextNode, currentMin, nodes) {
    var iconEl = document.getElementById('liveStatusIcon');
    var titleEl = document.getElementById('liveStatusTitle');
    var subEl = document.getElementById('liveStatusSub');
    var status = document.getElementById('liveStatus');
    if (!titleEl || !status) return;

    status.classList.remove('live-now');

    if (nowNode) {
      var t = nowNode.querySelector('.tt-card-title');
      var tm = nowNode.querySelector('.tt-card-time');
      var endM = toMin(nowNode.dataset.end);
      var left = Math.max(0, Math.ceil(endM - currentMin));
      status.classList.add('live-now');
      if (iconEl) iconEl.textContent = '🔴';
      if (titleEl) titleEl.textContent = (t ? t.textContent : 'Class') + ' is live';
      if (subEl) subEl.textContent = (tm ? tm.textContent.trim() : '') + ' · ' +
        (left <= 1 ? 'ending now' : left + ' min remaining');
      return;
    }

    if (nextNode) {
      var nt = nextNode.querySelector('.tt-card-title');
      var s = toMin(nextNode.dataset.start);
      var till = Math.max(0, Math.ceil(s - currentMin));
      if (iconEl) iconEl.textContent = '⏭️';
      if (titleEl) titleEl.textContent = 'Next: ' + (nt ? nt.textContent : 'Class');
      if (subEl) {
        if (till <= 1) subEl.textContent = 'Starting now';
        else if (till < 60) subEl.textContent = 'Starts in ' + till + ' min';
        else subEl.textContent = 'Starts in ' + Math.floor(till / 60) + 'h ' + (till % 60) + 'm';
      }
      return;
    }

    var anyPast = false;
    nodes.forEach(function (n) { if (n.classList.contains('past')) anyPast = true; });

    if (anyPast) {
      if (iconEl) iconEl.textContent = '✅';
      if (titleEl) titleEl.textContent = 'All done for today';
      if (subEl) subEl.textContent = 'Great job! See you tomorrow.';
    } else {
      if (iconEl) iconEl.textContent = '☕';
      if (titleEl) titleEl.textContent = 'No classes scheduled';
      if (subEl) subEl.textContent = 'Enjoy your free day.';
    }
  }

  /* --------------------------------------------------------------
     Week grid (kept for compatibility — may be absent now)
     -------------------------------------------------------------- */
  function updateWeekGrid() {
    var today = window.CAMPUS_TODAY;
    if (!today) return;
    var d = new Date();
    var currentMin = d.getHours() * 60 + d.getMinutes() + d.getSeconds() / 60;

    document.querySelectorAll('.class-card').forEach(function (card) {
      card.classList.remove('now');
      if (card.dataset.day !== today) return;
      var s = toMin(card.dataset.start);
      var e = toMin(card.dataset.end);
      if (isNaN(s) || isNaN(e)) return;
      if (currentMin >= s && currentMin < e) card.classList.add('now');
    });
  }

  /* --------------------------------------------------------------
     View switching — handles 'live' and 'official'
     -------------------------------------------------------------- */
  window.switchView = function (view) {
    // Toggle tab active state
    document.querySelectorAll('.tt-tab').forEach(function (t) {
      t.classList.toggle('active', t.dataset.view === view);
    });

    // Show/hide the view containers
    var live = document.getElementById('view-live');
    var official = document.getElementById('view-official');
    var week = document.getElementById('view-week');   // legacy, may not exist

    if (live)     live.style.display     = (view === 'live')     ? 'block' : 'none';
    if (official) official.style.display = (view === 'official') ? 'block' : 'none';
    if (week)     week.style.display     = (view === 'week')     ? 'block' : 'none';

    try { localStorage.setItem('campusdesk-tt-view', view); } catch (e) {}
  };

  /* --------------------------------------------------------------
     Tick
     -------------------------------------------------------------- */
  function tick() {
    updateClock();
    updateRoadmap();
    updateWeekGrid();
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Restore last view
    try {
      var saved = localStorage.getItem('campusdesk-tt-view');
      if (saved === 'official') window.switchView('official');
      else if (saved === 'week') window.switchView('week');
      else window.switchView('live');
    } catch (e) {
      window.switchView('live');
    }

    tick();
    setInterval(tick, 1000);

    console.log('[CampusDesk] timetable.js loaded. Views:',
      {live: !!document.getElementById('view-live'),
       official: !!document.getElementById('view-official')});
  });
})();
