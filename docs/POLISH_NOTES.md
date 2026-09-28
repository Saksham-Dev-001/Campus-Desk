# CampusDesk — Polish Pack v2.1

Naye features + UX improvements. Sirf kuch files replace/add karne hain.

## Kya naya hai

### 🔔 Notification bell
- Topbar mein bell icon — unread count badge ke saath
- Click karo → dropdown mein recent notifications
- Har 30 second auto-update
- "Mark all read" ek click mein

### 🍞 Toast notifications
- Flash messages ab screen ke corner mein toast ki tarah aate hain
- Auto-dismiss after 4 seconds
- Non-blocking — page reload ke baad bhi nahi rukte

### 📤 Assignment submission
- Students ab assignments ke saath file upload kar sakte hain
- Teacher ko submission list dikhti hai (submitted/not submitted)
- One submission per student per assignment (replace kar sakte ho)

### 👁️ File preview
- PDFs aur images ke saath eye icon
- Modal mein inline preview
- Download kiye bina content dekh sakte ho

### ⌨️ Keyboard shortcuts
- `Ctrl+K` (or `Cmd+K` on Mac) → search pe focus
- `Esc` → close any modal / drawer
- `G then D` → go to Dashboard
- `G then N` → go to Notifications

### 📱 PWA — install as app
- Browser mein "Install CampusDesk" option aayegi
- Phone pe native app jaisa icon
- Offline-friendly shell

### 🖨️ Print styles
- Timetable / notices / assignments print karo cleanly
- Sidebar, nav, buttons auto-hide

### 🎨 Better avatars
- Har user ka deterministic color (name se generate)
- Initials displayed (e.g., "VK" for Vishal Kumar)

---

## Apply karne ka tarika

Apne `campusdesk/` folder mein:

### Naye files (copy karo)
- `POLISH_NOTES.md`
- `static/css/polish.css`
- `static/js/polish.js`
- `static/manifest.json`
- `static/icons/icon.svg`

### Existing files (replace karo)
- `models.py`
- `app.py`
- `templates/base.html`
- `templates/assignments.html`
- `templates/dashboard_student.html`
- `templates/dashboard_teacher.html`
- `templates/notifications.html`
- `templates/search.html`
- `routes/api.py`
- `routes/student.py`
- `routes/teacher.py`

### Chalao

```

reset.bat     (schema thoda change hua hai — submissions cleanup)
start.bat

```

---

## Test karo

1. **Bell**: Login karo → bell icon dabao → notifications dikhengi
2. **Preview**: Study Material mein jao → kisi file ke aage eye icon
3. **Submit**: student account se → Assignments → Submit button
4. **Ctrl+K**: Topbar search pe focus
5. **PWA**: Chrome mein URL bar mein install icon
6. **Toast**: Koi bhi action (notice publish etc.) → corner mein toast
