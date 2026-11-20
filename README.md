# Campus Event Management System

A web-based university event platform built for the CT-365 Software Engineering
Complex Computing Problem (CCP). Students discover and register for campus events,
organizers create and manage their own events, and administrators oversee users,
roles and the whole system.

Thar Institute of Engineering Sciences & Technology (TIEST), affiliated with
NED University of Engineering & Technology.

**Technology:** Python 3, Flask, Flask-SQLAlchemy, SQLite, Jinja2, Bootstrap 5, JavaScript, Pytest.

---

## 1. Run it on Windows (one step)

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and tick
   **"Add python.exe to PATH"** during installation.
2. Open this project folder in VS Code (or File Explorer).
3. Double-click **`setup_and_run.bat`**.

The script creates a virtual environment, installs the requirements, creates the
database and demo data (only the first time), starts the server and opens
**http://127.0.0.1:5000** in your browser. Keep the black window open while you use
the application. Press **CTRL+C** in that window to stop the server.

Re-running the script is safe: it reuses the virtual environment and never creates
duplicate demo accounts or events.

### Manual steps (optional, for VS Code terminals)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py            # initialises the database, seeds demo data, starts the server
python -m pytest -q      # runs the automated test suite
```

---

## 2. Demo accounts

These are **local academic demonstration accounts only**. Do not use them, or any
similar passwords, in production.

| Role       | Email                 | Password       |
|------------|-----------------------|----------------|
| Admin      | admin@campus.edu      | Admin@123      |
| Organizer  | organizer@campus.edu  | Organizer@123  |
| Student    | student@campus.edu    | Student@123    |

All three roles use the **same server and the same address**. Sign out (Log out
button) and sign in as another role to switch.

---

## 3. User guide

**Students**
- Browse upcoming events, search by name, filter by category.
- Open an event to see date, time, venue, seats left and the waitlist count.
- Register. If seats are free you are confirmed immediately; if the event is full you
  join the waitlist and see your position.
- Cancel an active registration from the event page or **My registrations**. The
  earliest waitlisted student is promoted automatically.

**Organizers** (only their own events)
- **Create event** with title, description, category, venue, date, start and end time,
  capacity and status (open / closed / cancelled).
- **My events**: edit, change status, open the attendee list, export CSV.
- **Attendees**: see confirmed participants and the waitlist in order, and check in
  confirmed attendees.

**Administrators**
- System overview with user, event and registration statistics.
- **All events**: manage any event, including those created by organizers.
- **Users and roles**: promote students to organizers, or revert organizers to students.
  Administrator accounts cannot be created through sign-up or changed in the UI.
- **All registrations**: monitor every registration record.

---

## 4. Project structure

```
Campus_Event_CCP_Final/
├── README.md
├── requirements.txt
├── run.py                  start the app / initialise the database (--init-only)
├── setup_and_run.bat       one-step Windows setup and launch
├── .gitignore
├── app/
│   ├── __init__.py         application factory, CSRF, error pages, template helpers
│   ├── models.py           User, Event, Registration (constraints and indexes)
│   ├── routes.py           all HTTP routes with role decorators and ownership checks
│   ├── services.py         business rules: registration, waitlist, check-in, roles, seed
│   ├── validators.py       server-side validation of every form
│   ├── templates/          Jinja2 templates (base layout, role dashboards, pages)
│   └── static/
│       ├── css/style.css   design system (navy/indigo palette, cards, tables, responsive)
│       ├── js/app.js       confirmation dialogs and mobile sidebar
│       └── images/
├── instance/               SQLite database is created here at runtime (git-ignored)
├── tests/                  pytest suite with an isolated temporary database per test
├── Design/                 Mermaid diagrams that describe the implemented system
├── TestReports/            executed test output
└── Screenshots/            (to be captured, see completion checklist)
```

---

## 5. Business rules (implemented in `app/services.py`)

- Only student accounts register for events.
- Registration is accepted only for open events that start in the future.
- One active (non-cancelled) registration per student per event. Enforced in code and by
  a unique partial index in the database.
- Seats available: confirmed. Event full: waitlisted, in arrival order.
- A newcomer can only take a free seat if nobody is ahead of them on the waitlist.
- Cancelling a confirmed registration promotes the earliest waitlisted student.
- Capacity cannot be lowered below the number of confirmed registrations. Raising it
  promotes waitlisted students.
- Only confirmed registrations can be checked in. Waitlisted, cancelled and checked-in
  registrations cannot be cancelled after check-in. Attendees cannot be checked in for
  a cancelled event.
- Organizers manage only their own events. Administrators manage all events.
- Only administrators assign roles. Only student and organizer roles can be assigned.

---

## 6. Security measures

- Passwords are stored as salted hashes (Werkzeug `generate_password_hash`).
- Session-based login with HTTP-only, SameSite=Lax cookies.
- CSRF token required on every POST form (returns HTTP 400 when missing or wrong).
- Role-based access on every protected route, plus ownership checks for event actions.
  Direct URL access by unauthorized users returns 403 (or redirects to login).
- Public registration cannot choose a role. Admin accounts cannot be created through the UI.
- Post-login redirects are restricted to same-site paths (open-redirect protection).
- CSV exports neutralise spreadsheet formula injection.
- Custom 400, 403, 404 and 500 pages. Details are not leaked to users.

---

## 7. Testing

```powershell
python -m pytest -v
```

The suite has 50 automated tests covering authentication, role authorization,
event validation and search, registration, waitlist promotion, cancellation,
capacity rules, check-in, CSV export, database integrity and demo-seed idempotency.
Each test uses its own temporary SQLite database. Results are recorded in
`TestReports/`.

---

## 8. Known limitations

- Built for local demonstration with Flask's development server, not production hosting.
  The demo passwords and the default secret key must be replaced before any real use
  (set `CAMPUS_SECRET_KEY`).
- Capacity protection relies on SQLite's single-writer locking. Highly concurrent
  registration across several server processes would need PostgreSQL and row locking.
- No email notifications. Confirmations appear as on-screen messages.
- No login rate limiting or password reset flow.
- The page uses Bootstrap and Bootstrap JavaScript from a CDN, so it needs an internet
  connection to load its styles.

---

## CT-365 Submission Index

Documentation for the CT-365 Software Engineering CCP. Application source is at the repository root, as described in SourceCode/README.md.

| Deliverable | Folder | Files |
|---|---|---|
| D1 Proposal and feasibility | Proposal/ | SE_CCP_GroupXX_CampusEventManagement_D1_Proposal_and_Feasibility.pdf (+ .md) |
| D2 SRS and requirements | SRS/ | ..._D2_Software_Requirements_Specification.pdf (+ .md); ..._RTM.xlsx |
| D3 Analysis and design | Design/ | ..._D3_Analysis_and_Design.pdf (+ .md); Diagrams/ (PNG, SVG, Mermaid source) |
| D4 Implementation and tracking | ProjectManagement/ | ..._D4_Implementation_and_Tracking.pdf (+ .md); Sprint_1.md; Sprint_2.md; Task board and milestones .xlsx; contribution template |
| D5 Testing and QA | TestReports/ | ..._D5_Test_Plan.pdf; ..._D5_Test_Execution_Report.pdf; ..._Test_Cases.xlsx; ..._Defect_Log.xlsx; pytest output files |
| D6 Final report and demo | FinalReport/ | ..._D6_Final_Report.pdf; ..._User_Guide.pdf; CCP_Submission_Checklist.xlsx |
| Presentation | Presentation/ | ..._Presentation.pptx (speaker notes included) |
| Screenshots | Screenshots/ | 01-11 from the running application; 12 rendered test output; 13 pending |
| Input data | InputData/ | Demo accounts and demo events description |

**Naming.** Files follow the instructor's convention SE_CCP_GroupXX_ProjectTitle. Replace "GroupXX" with the group number.

**Placeholders.** Team names, roll numbers, instructor name, submission date and repository URL are marked in square brackets and must be completed by the team.

**Test folder note.** The recommended "Tests/" folder is not created separately because it would conflict with the automated test package "tests/" on case-insensitive systems (Windows, macOS). Test documents are in TestReports/.

**Publishing.** No GitHub remote exists yet. Follow the steps in ProjectManagement/..._D4_Implementation_and_Tracking.pdf, Section 16.1.
