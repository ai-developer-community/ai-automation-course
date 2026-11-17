# Setup guide

This guide takes you from a new laptop to your first automation running on Google Cloud. You don't need to be a developer. Every command is here to copy, and each step says what you should see.

Plan on about an hour the first time. Most of it is creating accounts.

## What you are setting up

| Thing | What it is for | Cost |
|---|---|---|
| A Google Cloud project | Where the automations run, and where the AI model comes from | Pay for what you use. These examples cost pennies a day. New accounts get free credit |
| The `gcloud` command line tool | Lets your laptop talk to Google Cloud | Free |
| `uv` | Installs Python and the code's libraries for you | Free |
| `git` | Downloads this code | Free |
| A Google Sheet | Where the automations save leads and prospects | Free |
| Slack, Resend, Google AI Studio | Only for speed to lead and Hacker News. Skip them until you get there | Free tiers are enough |

**Do you need Docker?** No. Each automation runs in a container, but `deploy.sh` builds the container on Google Cloud with Cloud Build, so nothing is built on your laptop. Install Docker only if you want to run the container locally (see the end of this guide).

## 1. Install the tools

### On a Mac

Open the Terminal app. Install [Homebrew](https://brew.sh) first if you don't have it, then run:

```
brew install git uv
brew install --cask google-cloud-sdk
```

Close the terminal and open a new one so it can find the new tools.

### On Windows

Use WSL, which gives you a Linux terminal inside Windows. The scripts in this repository are written for Mac and Linux.

1. Open PowerShell as administrator and run `wsl --install`. Restart when it asks.
2. Open the **Ubuntu** app from the Start menu and pick a username and password.
3. In Ubuntu, install git and uv:

```
sudo apt update && sudo apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

4. Install gcloud by following the **Debian/Ubuntu** steps at [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install).

Run every command in this guide from the Ubuntu terminal.

### Check it worked

```
git --version
uv --version
gcloud --version
```

Each prints a version number. If one says `command not found`, open a new terminal and try again. If it still fails, repeat that install step.

## 2. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with a Google account.
2. Accept the terms. If it offers free credit, take it. You need to add a card, but you aren't charged until the credit runs out and you agree to upgrade.
3. Open the project picker at the top of the page and choose **New project**. Give it a name, such as `automations`.
4. Copy the **project ID** shown under the name. It looks like `automations-482113`. It is not always the same as the name, and you need the ID.
5. Check billing is on: open **Billing** in the left menu. The project should be linked to a billing account. Nothing in this guide works without it.

**Set a budget alert now.** In **Billing → Budgets & alerts**, create a budget of a small amount, such as 10 in your currency, with email alerts. These examples should cost far less than that, but an alert means a mistake can't surprise you.

## 3. Sign in to Google Cloud from your laptop

```
gcloud auth login
```

A browser window opens. Sign in with the same Google account and allow access. The terminal then says `You are now logged in as ...`.

## 4. Get the code

```
git clone https://github.com/ai-developer-community/ai-automation-course.git
cd ai-automation-course
cp .env.example .env
```

`.env` is your settings file. It holds your secrets, so it is listed in `.gitignore` and never leaves your laptop except through `deploy.sh`, which copies the secrets into Google Secret Manager. **Never commit `.env` and never paste it anywhere public.**

## 5. Fill in the settings

Open `.env` in any text editor. On a Mac, `open -e .env` opens it in TextEdit. For the first deploy you only need these:

| Setting | What to put |
|---|---|
| `PROJECT` | The project ID from step 2 |
| `REGION` | Leave `europe-west2` (London), or pick one near you, such as `us-central1` |
| `WEBHOOK_TOKEN` | A long random value. Run `openssl rand -hex 24` and paste the result |
| `WEBHOOK_SECRET` | Another one. Run the same command again |
| `SHADOW` | Leave it `true`. Nothing is sent until you change it |

Leave the rest empty for now. `deploy.sh` skips any secret that isn't set.

Then point this terminal at your project. Do this in every new terminal:

```
export CLOUDSDK_CORE_PROJECT=$(grep '^PROJECT=' .env | cut -d= -f2)
gcloud config get-value project
```

The second command should print your project ID.

## 6. Run the tests and hello world on your laptop

```
uv run pytest
uv run python automations/01_manual.py
```

The first time, `uv` downloads Python and the libraries, which takes a minute. The tests use fakes, so they need no accounts. You should see every test pass, then one log line from the automation with `"status": "ok"` in it. You may also see a `SyntaxWarning` from a Google library. It is harmless.

## 7. Deploy to Google Cloud

```
./deploy.sh
```

The first run takes five to ten minutes. It turns on the Google Cloud services the course uses, creates a service account for the automations to run as, stores your secrets in Secret Manager, builds the container image, deploys every automation and creates the schedules.

At the end it prints a command to try each automation. Start with the first:

```
gcloud run jobs execute hello-manual --region europe-west2 --wait
```

Use your own region if you changed it. You can see the run in the [Cloud Run console](https://console.cloud.google.com/run), under **Jobs**.

You now have an automation running on Google Cloud. Carry on with [DEMO.md](DEMO.md), which follows the course example by example.

## 8. Add the accounts for the bigger examples

Set these up when you reach each example, then add them to `.env` and run `./deploy.sh` again.

**The Google Sheet** (speed to lead, the research agent, Hacker News)

1. Create a sheet at [sheets.new](https://sheets.new) with three tabs named exactly `Prospects`, `Leads` and `Hacker News`. [DEMO.md](DEMO.md) lists the headings for each.
2. Copy the long ID from the sheet's address, between `/d/` and `/edit`, into `SHEET_ID`.
3. Share the sheet as **Editor** with the service account email that `deploy.sh` printed. It looks like `automations@your-project-id.iam.gserviceaccount.com`.

**Slack** (speed to lead, the research agent). Create an [incoming webhook](https://api.slack.com/messaging/webhooks) for a channel and put its address in `SLACK_WEBHOOK_URL`.

**Resend** (speed to lead, for email). Sign up at [resend.com](https://resend.com), verify a domain you own, create an API key, and set `RESEND_API_KEY` and `EMAIL_FROM`.

**Google AI Studio** (the decision model in speed to lead and Hacker News). Create a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and set `GEMINI_API_KEY`. The writing model and the agent don't need a key: on Google Cloud they sign in as the service account.

## When you are finished

Scheduled jobs keep running, and cost a little, until you stop them. To pause them:

```
gcloud scheduler jobs pause daily-research-weekdays --location europe-west2
gcloud scheduler jobs pause hacker-news-twice-a-day --location europe-west2
```

To remove everything at once, delete the project in **IAM & Admin → Settings → Shut down**. That stops all billing for it.

## Where people get stuck

| What you see | Why, and what to do |
|---|---|
| `command not found: gcloud` | The terminal was open before you installed it. Open a new terminal |
| `Billing account ... is not found` or `billing is disabled` | The project has no billing account. Link one in **Billing** (step 2) |
| `PROJECT ... not found` or `NOT_FOUND` | `PROJECT` in `.env` is the project name, not the ID, or this terminal isn't pointed at it. Fix `.env` and run the `export` line from step 5 |
| `Permission denied` or `does not have ... permission` during deploy | Your Google account isn't an Owner of the project. Use the account that created it, or ask the owner for the **Owner** role |
| `./deploy.sh: Permission denied` | Run `chmod +x deploy.sh alerts.sh`, then try again |
| `Reauthentication is needed` | Your sign-in expired. Run `gcloud auth login` |
| Deploy fails on the build step the first time | A new build account takes about a minute to get its permissions. The script retries, but if it gives up, run `./deploy.sh` again |
| A webhook returns 403 | Your Google organisation blocks public URLs. See "If your Google organisation blocks public URLs" in [DEMO.md](DEMO.md) |
| Sheets returns 403 or 404 | The sheet isn't shared with the service account, or `SHEET_ID` is wrong |

[DEMO.md](DEMO.md) has more fixes for each example.

## Optional: run the container with Docker

You never need this to deploy. It is useful if you want to check the image works before it goes to Google Cloud. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then:

```
docker build -t automations .
docker run --rm automations
```

It prints the same log line as step 6. To run another automation, put its command after the image name, for example `docker run --rm automations uv run --no-dev python automations/02_scheduled.py`.
