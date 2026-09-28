# CampusDesk

**Right information → Right student → Right time.**

A college information & document management platform built by **Vishal & Saksham**.

---

## ⚡ Quick Start (Windows)

1. Extract the ZIP
2. Double-click **`start.bat`**
3. Browser opens automatically at `http://localhost:5000`

That's it. `start.bat` handles everything:
- Creates virtual environment
- Installs dependencies
- Sets up `.env`
- Initializes database + seeds demo data
- Launches server

## ⚡ Quick Start (Linux / macOS)

```bash
chmod +x start.sh
./start.sh
```

## Manual Start

```
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

---

## 🔑 Demo Logins

Password for **every** demo account: `password123`

| Role ↕▾ | Username ↕▾ | Academic Placement ↕▾ |
|---|---|---|
| −**Admin** | `admin` | Full system access |
| −**Teacher** | `teacher1` | Dr. Anjali Verma — CSE |
| −**Teacher** | `teacher2` | Prof. Rajesh Kumar — CSE |
| −Student Admin | `CSE2024001` | Vishal Kumar — CSE · 1st Yr · A · A2 |
| −Student | `CSE2024002` | Saksham Singh — CSE · 1st Yr · A · A2 |
| −Student | `CSE2024003` | Rahul Sharma — CSE · 1st Yr · A · A1 |
| −Student | `CSE2024004` | Priya Nair — CSE · 1st Yr · A · A1 |
| −Student | `CS2024001` | Rahul Sharma — **CS** · 1st Yr · A · A2 *(same naam, alag branch!)* |
| −Student | `CS2024002` | Ananya Iyer — CS · 1st Yr · A · A2 |
| −Student | `IT2024001` | Vikram Joshi — IT · 1st Yr · A · A1 |
| −Student | `ECE2024001` | Pooja Reddy — ECE · 1st Yr · A · A1 |
| −Student | `ME2024001` | Arjun Mehta — ME · 1st Yr · A · A1 |
| −Student | `CE2024001` | Kavya Rao — CE · 1st Yr · A · A1 |
| −Student | `AIML2024001` | Aryan Shah — AIML · 1st Yr · A · A1 |
| −Student | `DS2024001` | Riya Kapoor — DS · 1st Yr · A · A1 |
⚙

> **Note the duplicate name:** `CSE2024003` and `CS2024001` are both "Rahul Sharma"
> but they are **different people in different branches**. CampusDesk identifies
> students by enrollment number, never by name.

---

## 🎯 The Exhibition Demo

1. Login as `teacher1` / `password123`
2. Go to **Assignments** → **+ Create Assignment**
3. Fill the form. In **Target Audience**, select:
`B.Tech` → `CSE` → `1st Year` → `Sem 1` → `Section A` → `Batch A2`
4. **Publish**

Then verify:

| Login as ↕▾ | Result ↕▾ |
|---|---|
| −`CSE2024001` (CSE · A2) | ✅ **Assignment visible** |
| −`CSE2024003` (CSE · A1) | ❌ Assignment absent |
| −`CS2024001` (CS · A2) | ❌ Assignment absent |
⚙

**File versioning demo:**

1. As `teacher1` → **Study Material** → navigate to `CSE / 1st Year / Sem 1 / Section A / A2`
2. Upload any PDF. Log in as `CSE2024001` → download (v1).
3. Back as teacher, click 🔄 **Replace** on the file and upload a new PDF.
4. As `CSE2024001`, download again → you get **v2**. Old version kept in history.

---

## 📱 Mobile-First Design

CampusDesk works equally well on phone and desktop:

**On phone:**

- Bottom navigation bar with 4-5 key actions
- Sidebar becomes a slide-in drawer (☰ button)
- Cards, forms and grids stack vertically
- Timetable scrolls horizontally
- Modals open from bottom (bottom-sheet style)
- Touch-friendly tap targets (min 44px)
- Safe-area-inset support for notched phones

**On desktop:**

- Persistent sidebar with all navigation
- Multi-column grid layouts
- Full-width tables with hover states
- Keyboard shortcuts (Esc to close modals)

**Theme:**

- **Light mode** — clean white surfaces
- **Dark mode** — deep navy, easy on eyes
- 🌓 Toggle in topbar — your choice is remembered
- Respects your system preference on first visit

---

## 📚 Project Structure

```
campusdesk/
├── app.py                  Flask app factory, blueprint wiring
├── run.py                  Launcher (init DB + run server)
├── config.py               Env-driven config
├── models.py               Full relational schema
├── seed.py                 Demo college data
├── extensions.py           LoginManager + CSRF
├── verify.py               Diagnostic (data check)
├── reset.py                Wipe + reseed
├── start.bat / start.sh    One-click launchers
├── reset.bat               Reset + reseed (Windows)
├── requirements.txt
├── .env.example
│
├── services/
│   ├── targeting.py        THE core targeting engine
│   └── storage.py          StorageProvider abstraction
│
├── routes/
│   ├── auth.py             Login / logout
│   ├── student.py          Student dashboard, notices, timetable
│   ├── teacher.py          Teacher dashboard, content creation
│   ├── admin.py            Users, structure, import, storage
│   ├── files.py            File & folder manager
│   ├── search.py           Permission-aware search
│   └── api.py              JSON endpoints for targeting UI
│
├── templates/              Jinja2 templates
└── static/
    ├── css/style.css
    ├── js/theme.js         Theme bootstrap (loaded first)
    ├── js/app.js           UI helpers, targeting logic
    └── sample_students.csv
```

---

## 🎓 Academic Hierarchy

```
Course → Branch → Year → Semester → Section → Batch → Student
```

Example:

```
B.Tech → CSE → 1st Year → Sem 1 → Section A → Batch A2 → Vishal Kumar
```

Every **Folder, File, Notice, Assignment, Timetable entry** carries the *same
six nullable target columns*:

| Column ↕▾ | Meaning ↕▾ |
|---|---|
| −`course_id` | B.Tech / M.Tech / … |
| −`branch_id` | CSE / IT / ECE / … |
| −`year_id` | 1st Year / 2nd Year / … |
| −`semester_id` | Sem 1 / Sem 2 / … |
| −`section_id` | A / B / C |
| −`batch_id` | A1 / A2 / A3 / … |
| −`subject_id` | Optional — specific subject |
⚙

**Rule:** a NULL target column means "applies to everyone below the set level".

| Set on a Notice ↕▾ | Who sees it ↕▾ |
|---|---|
| −(nothing set) | Everyone in the college |
| −`branch=CSE` | Every CSE student |
| −`branch=CSE, year=1st` | Every CSE 1st-year student |
| −`branch=CSE, year=1st, section=A, batch=A2` | Only CSE 1st-year Section A Batch A2 |
⚙

Filtering happens **server-side** by `services/targeting.py`. The frontend
never decides what a student may see.

---

## 💾 Storage Abstraction

```
Frontend  →  Flask  →  StorageProvider  →  { LocalProvider | TelegramProvider }
```

- **`LocalProvider`** (default) writes files to `uploads/storage/<BRANCH>/`
- **`TelegramProvider`** stores files in **branch-level** Telegram channels
— teachers & students never touch Telegram; it's purely the physical layer

Switch via `.env`:

```
STORAGE_PROVIDER=telegram
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_BRANCH_CHANNELS={"CSE":"-100...","CS":"-100..."}
```

The DB only stores an opaque `storage_ref` string. Migrating to Cloudflare R2
later means writing one new `StorageProvider` subclass — no route or template
changes.

---

## 👥 Roles

| Role ↕▾ | Can do ↕▾ |
|---|---|
| −**Student** | View dashboard, notices, assignments, material, timetable. Submit requests. Download permitted files. |
| −**Student Admin** | Everything a student can, **plus** manage folders and files for their academic group. |
| −**Teacher** | Create notices, assignments, timetable entries. Manage files/folders. Handle student requests. |
| −**Admin** | Full control: users, academic structure, CSV import, storage mapping, audit log. |
⚙

---

## 📥 Bulk Student Import

Admin → **Bulk Import** → upload a CSV:

```
name,enrollment_number,course,branch,year,semester,section,batch,password
Aarav Gupta,CSE2025001,B.Tech,CSE,1st Year,Sem 1,A,A1,password123
```

- Only `name` and `enrollment_number` are required
- Missing courses / branches / sections / batches are created automatically
- Re-importing the same enrollment number **updates** the existing student
- Duplicate names are handled correctly — identity is always the enrollment number

Sample CSV included at `static/sample_students.csv`.

---

## 🔒 Security

- Passwords hashed with Werkzeug PBKDF2-SHA256
- Session-based auth via Flask-Login
- CSRF protection on every POST (Flask-WTF)
- Role-based route guards on every blueprint
- Server-side target filtering — students cannot fetch restricted files even
by guessing URLs
- Upload validation: extension allow-list, safe filename sanitisation,
configurable max size
- All secrets from environment variables
- Telegram credentials never leave the server

---

## ✅ What's Fully Working

- Authentication for all four roles
- Smart targeting engine (server-side)
- Student dashboard with "For You" sections
- Teacher dashboard + dynamic targeting UI
- File/folder manager — create, rename, delete, upload, **replace**, download
- File versioning (`file_versions` table)
- Notices with priority + targeting
- Assignments with due dates + targeting
- Weekly timetable with targeting
- Notification centre (auto-generated for relevant students only)
- Permission-aware global search
- Student request workflow
- Admin: users, structure, CSV import, storage mapping, audit log
- Storage abstraction (Local + Telegram)
- Duplicate-name safety via enrollment numbers
- 🌓 Dark / Light theme with persistence
- 📱 Mobile-first responsive layout
- Demo seed data ready for exhibition

## 🔮 Optional / Future

- Assignment submission upload by students (table exists)
- Cloudflare R2 / S3 storage provider (drop-in subclass)
- PostgreSQL migration (change `DATABASE_URL`)
- Email / push notifications
- PWA installation (`manifest.json` + service worker)
- Per-teacher section scoping

---

Built with care by **Vishal & Saksham**.

</BDS:create_file>

<BDS:create_file fileName="campusdesk/requirements.txt">

```txt
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
Werkzeug==3.0.3
requests==2.32.3
python-dotenv==1.0.1

