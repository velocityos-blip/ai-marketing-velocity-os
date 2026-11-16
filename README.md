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
- **Setup status:** The checked-in [requirements file](backend/requirements.txt) joins the AnyIO and HTTPX pins on one line and omits the imported Emergent integration package. Resolve those dependencies in your local environment before starting Uvicorn. With the dependencies and services configured, `GET /api/health` is the backend’s health route.
