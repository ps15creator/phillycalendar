# Work split: Auto (UI/UX) vs Claude (Backend)

Use this document so Auto and Claude stay aligned and avoid editing the same files or breaking each other’s work. **Share this file with both assistants** (e.g. paste into Claude, or reference in Cursor for Auto).

---

## 1. Ownership at a glance

| Area | Owner | Scope |
|------|--------|--------|
| **Frontend / UI–UX** | **Auto** | All static assets, HTML, CSS, JS, client behavior, accessibility, design |
| **Backend / API / Data** | **Claude** | Flask app, database, scrapers, API design, env, deployment config |

---

## 2. File ownership

### Auto (UI/UX) — do not change these in backend tasks

- `backend/static/index.html`
- `backend/static/styles.css`
- `backend/static/app.js`
- `backend/static/sw.js`
- `backend/static/*.png`, `*.jpg`, `*.svg`, etc. (images, icons, assets under `static/`)
- Any new front-end files under `backend/static/` (e.g. `static/images/`, `static/fonts/`)

**Claude:** Avoid editing these. If the API or server behavior changes in a way that requires front-end updates, document the change in **Section 5** (API contract) and/or add a short note in this file; Auto will update the frontend.

---

### Claude (Backend) — do not change these in UI/UX tasks

- `backend/app.py`
- `backend/database.py`
- `backend/scheduler.py`
- `backend/scrapers/` (all files)
- `backend/requirements.txt`
- `backend/Procfile`, `backend/render.yaml`, `backend/Dockerfile`, `backend/runtime.txt`
- `backend/*.py` (any other Python under `backend/`)
- `.env` / environment variables and how they’re used in the backend

**Auto:** Avoid editing these. If the UI needs a new endpoint or different response shape, document it in **Section 5** or add a note here; Claude will implement the backend change.

---

### Shared / coordinate before changing

- **`backend/app.py`**  
  - Defines routes and serves `backend/static/`.  
  - **Claude** owns it. If route or static-serving behavior must change, Claude does it and notes any impact on the frontend (e.g. new path, new API field).
- **API response shape**  
  - Defined by backend, consumed by frontend. See **Section 5**.  
  - **Claude** changes the API; **Auto** updates `app.js` (and any HTML that depends on it) to match.
- **Cache/versioning**  
  - `index.html` references CSS/JS with `?v=N`.  
  - **Auto** bumps `v` when changing static assets.  
  - **Claude** does not change `?v=` in `index.html` (that file is Auto’s). If Claude ever serves HTML, keep using the same versioning pattern.

---

## 3. Workflow rules

1. **One owner per file**  
   Only the owner edits that file. If the other assistant’s work depends on it, add a note or update **Section 5** instead of editing the file yourself.

2. **Backend changes first when the API changes**  
   If an endpoint or response shape will change:
   - **Claude** implements the backend change and documents it in **Section 5** (and optionally in this file).
   - **Auto** then updates the frontend to use the new API.

3. **Frontend-first when only UI/UX changes**  
   For purely visual or client-side behavior (no new endpoints or response changes), **Auto** can change static files without waiting for Claude.

4. **Don’t edit the other owner’s files**  
   If you need a change in the other area, write it down here (or in Section 5) and assign it: “Claude: add …” or “Auto: update …”.

5. **Git**  
   Commit after each logical chunk of work (e.g. “Auto: UI refresh”, “Claude: add last_sync to /stats”). That makes it clear who changed what and easier to revert if something clashes.

---

## 4. What each side can assume

**Auto can assume:**

- Backend serves the app at `/` and static files under `/static/`.
- API base URL is same-origin (e.g. `''` or `window.location.origin`) for `fetch()` from the frontend.
- Endpoints and response shapes are as documented in **Section 5** until Claude updates that section.

**Claude can assume:**

- Frontend lives under `backend/static/` and is served by Flask as-is (no build step unless the user adds one).
- `app.js` calls `/events/upcoming`, `/stats`, `/events`, `/events/<id>`, `/scrape`, etc., with methods and request bodies as in **Section 5**.
- Frontend expects JSON with `success`, `events`, `stats`, etc. as described below. New fields are fine if documented; removing or renaming fields requires a note so Auto can update the frontend.

---

## 5. API contract (backend ↔ frontend)

**Claude** owns the backend and this contract. When changing endpoints or response shapes, **Claude** updates this section and adds a short note at the top of this file (e.g. “API change 2026-02-XX: /stats now returns last_sync”). **Auto** uses this to keep `app.js` in sync.

### Endpoints the frontend uses

| Method | Path | Used for | Request | Response (relevant fields) |
|--------|------|----------|--------|----------------------------|
| GET | `/events/upcoming` | Load event list | — | `{ success, events: [{ id, title, description, start_date, end_date, location, category, price, source, source_url, registration_deadline }] }` |
| GET | `/stats` | Stats bar | — | `{ success, stats: { total_events, upcoming_events } }` |
| GET | `/events/<id>` | (if used) | — | Single event object |
| POST | `/events` | Add event (admin) | JSON body, `X-Admin-Token` header | `{ success, ... }` |
| PUT | `/events/<id>` | Edit event (admin) | JSON body, `X-Admin-Token` header | `{ success, ... }` |
| DELETE | `/events/<id>` | Delete event (admin) | `X-Admin-Token` header | `{ success, ... }` |
| POST | `/scrape` | Trigger scrape (admin) | — | `{ success, total_added, ... }` |

### Event object (minimum)

- `id`, `title`, `description`, `start_date`, `end_date`, `location`, `category`, `price`, `source`, `source_url`, `registration_deadline`  
- Dates: ISO or RFC 2822; frontend parses with `parseLocalDate()`.

### Stats (minimum)

- `total_events`, `upcoming_events`  
- Optional: `last_sync` or `last_updated` (if added, frontend will show it in “Last Updated”).

### Admin

- Admin routes require header: `X-Admin-Token: <value>` (value from env `ADMIN_TOKEN`).

---

## 6. Changelog (coordination notes)

Add short dated entries when the split affects both sides, so the other assistant knows what changed.

| Date | Change | Who | Note for the other |
|------|--------|-----|--------------------|
| (example) | Add `last_sync` to `/stats` | Claude | Auto: show `data.stats.last_sync` in “Last Updated” instead of current time. |
| 2026-02 | Eagles green dominant; header logo slot; hero bg slot; footer Philly pride row | Auto | Claude: no backend change. Optional: add last_sync to /stats. |
| (example) | New `/static/images/` for logos | Auto | Claude: no change; Flask already serves `static/`. |

---

## 7. Quick reference for the user

- **UI/UX, design, frontend behavior, accessibility** → Assign to **Auto**.  
- **API, database, scrapers, deployment, env, backend logic** → Assign to **Claude**.  
- **“Make the site look like this” / “Add this to the design”** → Auto (static files).  
- **“Add an endpoint” / “Change how data is stored” / “Fix the scraper”** → Claude (backend).  
- When in doubt, add a note in **Section 6** and assign the work to one assistant; the other can follow up from the document.

---

*Last updated: 2026-02. Adjust file paths or sections if the repo structure changes.*
