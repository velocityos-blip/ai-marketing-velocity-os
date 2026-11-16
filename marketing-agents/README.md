# Velocity OS · Marketing agents

A self-hosted marketing desk for small companies. Go from a company brief to a reviewable campaign and an approved organic social post. This MIT-licensed edition runs independently of the React/FastAPI product at the repository root. Accounts, subscriptions, data and sessions are separate.

## Run it

Python 3.11+; no pip installs, database service or model keys required.

```sh
cd marketing-agents
python3 -m unittest -v
python3 app.py
```

Open **http://127.0.0.1:8787**. Create a company and enter a measurable goal, offer, audience and campaign budget in whole US dollars. Try “Book 10 demos in 30 days” with an audience of independent salon owners. Click **Start agent run** and expand each handoff in Campaign activity. Edit the social post before approving. The default local mode produces labeled templates, not language model inference. No API calls or publishing occur by default.

## How work moves

The CMO assesses missing evidence and assigns work. Digital Marketing uses that assessment to design a channel experiment. Content uses both messages to draft one post. The Analyst reviews the draft and defines a measurement plan. Each role receives the same brief and the preceding transcript. One run has four bounded steps. The app persists completed handoffs, model IDs and run status even if a later provider fails. A company editor can start runs and inspect results; only admins can create editors, manage channel access, approve copy and publish.

Set each role independently to **openai**, **anthropic**, **gemini**, **compatible**, or **local**. Use a compatible server to run an open-weight model. Model licenses and API subscriptions are separate from the platform license. The provider receives the brief and earlier outputs; the application never puts channel tokens in prompts. Copy `.env.example` to `.env`, set the provider model IDs and keys for your account, and load the file into the environment before launch, e.g. `set -a; . ./.env; set +a; python3 app.py` in a POSIX shell. Only source files you control. An OpenAI-compatible provider must implement text chat completions. OpenAI models selected here must support max_tokens. API keys are operator-owned; do not use consumer chat login credentials.

## Publication and limits

Connect a **mastodon.social** user access token in Company settings (read:accounts and write:statuses). Verification displays the destination account. After approval, click Publish to send the exact approved text and record the returned URL. If delivery is uncertain, the run stops in “check channel”; inspect the account before creating another post. Disconnect removes the local credential; revoke it at Mastodon to invalidate it. Other networks, ad buying, timed posting and automatic results collection are not implemented. Campaign budget is planning input; the app cannot spend it. Model charges are separate: set spending limits with each provider.

Starter allows 10 campaign starts per company per UTC calendar month; Growth allows 100. Unlimited editor seats in both. Failed or interrupted starts count because they can incur provider costs. Self-hosting is free; no checkout is implemented in this edition. The operator can change an allowance with `python3 manage.py COMPANY_ID growth`. Find the company ID in the workspace header.

## Operating boundary

Designed for trusted local pilots. One process, SQLite, private directory `private/` (override using VOS_DATA). Stop the process before copying the directory for backup. The DB contains briefs, drafts, password hashes and **unencrypted social tokens**; protect the directory and backups with disk encryption and OS access controls. The host owner controls all tenant data. Password reset, SSO, encrypted credential storage, background job scheduling, centralized audit and production monitoring are future work. Run only one server per database; startup marks unfinished work interrupted and ambiguous sends for investigation. Never expose public signup with shared paid keys without implementing invitation controls and a global cost limit. Loopback is the default bind; for a trusted internal pilot behind TLS use VOS_ORIGIN for the exact browser origin and VOS_PORT for the local listen port. No external requests are made during the test suite.

## Roadmap

1. Connect the existing VOS workspace identity and migrate the pilot workflow into a durable job queue.
2. Add OAuth with encrypted per-company credentials, scheduled campaigns, and channel-specific review policies.
3. Feed first-party conversion data back to the analyst; verify attribution before automating changes to spend.
