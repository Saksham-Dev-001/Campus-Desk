/* =====================================================================
   CampusDesk — theme bootstrap.
   MUST be loaded in <head> BEFORE any CSS paint so there is no flash.
   ===================================================================== */
(function () {
  var STORAGE_KEY = 'campusdesk-theme';

  function resolveInitialTheme() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (e) {}
    // First visit → respect OS preference
    try {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    } catch (e) {}
    return 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0b0f1e' : '#ffffff');
  }

  // Apply immediately (before paint)
  applyTheme(resolveInitialTheme());

  // Public toggle used by the topbar button
  window.toggleTheme = function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch (e) {}
  };
})();
