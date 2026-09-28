# P4 - Dashboard

Self-contained `index.html` (no build step, no npm). Talks to the backend
only through the HTTP endpoints listed in the project root `README.md` -
it has no knowledge of P1/P2/P3's internals.

- Served automatically at `/` by the backend (`backend/main.py`), so there's
  no CORS setup needed in normal use.
- To point it at a different backend, set `window.API_BASE = "https://..."`
  in a small `<script>` before `index.html`'s own script block, or open it
  standalone and edit the `API_BASE` constant near the top of the script.
- To replace this with a different frontend (e.g. a Next.js app later, per
  Doc 01's eventual stack): build it against the same endpoints and either
  point `backend/main.py`'s `"/"` route at the new build, or drop this
  folder entirely and run the new frontend separately against this API.
