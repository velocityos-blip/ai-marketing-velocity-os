# AI Marketing (Velocity OS)

**Velocity OS is an AI-powered marketing workspace for planning campaigns, coordinating specialist agents, and turning repeatable marketing work into practical playbooks.**

It brings campaign operations and a reusable library of **108 marketing agent skills and playbooks** into one open repository. Teams can use the self-hosted marketing agents on their own, or connect campaign work to the Velocity OS dashboard.

## What it helps you do

- Turn a company brief, audience, offer, and goal into a campaign plan.
- Assign structured work across CMO, Digital Marketing, Content, and Analyst roles.
- Draft and review channel-ready marketing content with human approval.
- Organize campaigns, tasks, schedules, social accounts, and performance metrics.
- Reuse documented skills and playbooks for common marketing and growth workflows.
- Run locally in a no-API-key demo mode, or configure supported model providers for agent runs.

Agent outputs are drafts and recommendations for a human to review. Publishing is an explicit approval step; campaign budgets are planning inputs and the app does not buy ads.

## The marketing agents and playbooks

The repository includes **108 reusable playbooks** under [marketing-agents/skills](marketing-agents/skills/). They cover practical work across marketing strategy, content, SEO, social media, campaigns, analytics, and growth. Each playbook gives an agent a focused role, clear inputs, and a repeatable workflow.

The self-hosted marketing desk runs a four-step workflow:

1. **CMO** assesses the brief and identifies strategic direction and gaps.
2. **Digital Marketing** turns the assessment into a channel plan and experiments.
3. **Content** drafts a campaign asset from the brief and preceding work.
4. **Analyst** reviews the draft and proposes how to measure the result.

You can try the local, template-based mode without provider keys, then configure each role to use a supported model provider. See the [marketing agents guide](marketing-agents/README.md) for setup, provider configuration, publishing boundaries, and operating notes.

## Repository layout

| Path | Purpose |
| --- | --- |
| [frontend/](frontend/) | React dashboard for teams, campaigns, agent work, schedules, integrations, and skills |
| [backend/](backend/) | FastAPI API for workspaces, campaign workflows, AI tools, and marketing operations |
| [marketing-agents/](marketing-agents/) | Independent self-hosted marketing desk and 108 agent playbooks |
| [deploy/](deploy/) | Docker Compose, Caddy, bootstrap, and deployment documentation |

The main Velocity OS dashboard and the standalone marketing desk have separate authentication and data stores. The self-hosted edition can run independently.

## Try the self-hosted marketing desk

Requires Python 3.11 or newer.

```sh
cd marketing-agents
python3 -m unittest -v
python3 app.py
```

Open **http://127.0.0.1:8787**, create a company, enter a goal and audience, then choose **Start agent run**. The default local mode generates labeled templates; it does not call a language model or publish content. Configure your own provider keys to run with a model. See the [full setup guide](marketing-agents/README.md).

## Run the full dashboard

The dashboard uses a React frontend, FastAPI backend, and MongoDB. For local development:

- Frontend: from frontend/, run `npm install` and `npm start`. Configure `REACT_APP_BACKEND_URL` for the API origin.
- Backend: install [backend requirements](backend/requirements.txt), configure MongoDB and a private `JWT_SECRET_KEY`, then start from the repository root with `uvicorn server:app --app-dir backend --host 0.0.0.0 --port 8000`.
- Deployment: start with the [deployment guide](deploy/README.md).

AI and billing integrations require their own provider credentials and deployment dependencies. Never commit secrets, API keys, social tokens, or production data.

## Security and publishing

The standalone pilot stores local company data and social credentials in its private data directory. Protect that directory and its backups; review the [operating boundary](marketing-agents/README.md#operating-boundary) before exposing a deployment. The app does not publish automatically: a user must approve copy and explicitly publish it. The standalone edition currently supports Mastodon; other channel integrations and scheduled publishing are not implemented there.

## Contributing

Issues and pull requests are welcome. When adding or editing a playbook, keep it specific, actionable, and clear about required inputs, expected output, and human review. See the existing files in [marketing-agents/skills](marketing-agents/skills/).

---

**AI Marketing (Velocity OS)** · Campaign workspace, marketing agents, and reusable playbooks.