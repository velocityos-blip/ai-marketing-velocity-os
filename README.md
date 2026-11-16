# Velocity OS

Velocity OS is a marketing workspace that puts campaign planning, AI writing tools, and team tasks in one application. A marketer can draft ad copy for a campaign; a team can organize related tasks by workspace and record the metrics it wants to track.

## What’s in the repository

| Area | What the code implements |
| --- | --- |
| Team workspace | Account registration and login, invitations, member roles, and workspace settings |
| Marketing operations | API routes for company profiles, social profiles, metrics, strategies, and tasks |
| AI tools | Separate endpoints for marketing assessments, strategy drafts, copy, ad creative text, and generating tasks from a strategy |
| Subscriptions | Stripe checkout, payment status, and webhook handling |

## Architecture

The [React application](frontend/src/App.js) handles routing, sign-in, the dashboard, and team management. The [feature pages](frontend/src/pages.js) call the backend for subscriptions, AI tools, and tasks. The [FastAPI server](backend/server.py) exposes the API under `/api`, uses PyMongo for workspace data, and calls the Emergent integrations library for language model and Stripe requests.

## Local development

- **Frontend:** From `frontend/`, run `npm install`, then `npm start`. Set `REACT_APP_BACKEND_URL` to the backend origin before starting the frontend.
- **Backend:** The application entry point is `server:app` inside `backend/`. It needs MongoDB and backend configuration, including `MONGO_URL` and a private `JWT_SECRET_KEY`. AI and billing use separate provider credentials.
- **Setup status:** Install the [backend requirements](backend/requirements.txt). Existing Stripe and AI tools also require the Emergent integrations package in their deployment environment. With the dependencies and services configured, `GET /api/health` is the backend’s health route.

## Self-hosted marketing agents

[Run the marketing agents edition](marketing-agents/README.md) to take a company brief through CMO assessment, channel planning, copywriting, review, and approved Mastodon publishing. This standalone Python edition supports per-role model selection and a local demo that requires no API keys.

## Campaigns in the VOS dashboard

Company members can use their existing VOS sign-in to start a campaign on the dashboard and read the CMO, Digital Marketing, Content and Analyst handoffs. Owners and admins can also approve copy and manage the publishing account. The server resolves membership for each request using the existing VOS team directory. The standalone edition has its own history. Connecting the dashboard creates a campaign store for each existing VOS workspace.

Deploy the full repository with Python 3.11, the existing MongoDB connection and JWT signing configuration, and one Uvicorn worker. Start from the repository root with `uvicorn server:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 1`. Give VOS_DATA a private, persistent directory dedicated to this service. Campaigns, quota reservations and publishing tokens live there. Tokens are stored in SQLite, so restrict host and backup access. Configure roles and provider credentials as described in the [agent guide](marketing-agents/README.md). Billing entitlements for the campaign allowance are managed separately.

For a deployment under /vos/, build the frontend with `PUBLIC_URL=/vos INLINE_RUNTIME_CHUNK=false GENERATE_SOURCEMAP=false npm run build` from frontend/. Leave REACT_APP_BACKEND_URL unset so the browser uses /vos/api. Serve the compiled files below /vos/ with SPA fallback for dashboard and sign-in routes. Proxy /vos/api/* to /api/* on the existing VOS backend. Preserve the session cookie, bearer token and X-VOS-Client header. The main website can link directly to /vos/dashboard.

To test the integrated flow, install mongomock in the test environment and run `python -m unittest test_dashboard_campaigns` from backend/. The test uses temporary campaign storage and a simulated MongoDB instance.
