# Put the HR Board on your phone

This turns the model into a web app with a home-screen icon. All free. Roughly
a 20–30 minute one-time setup, then it's just a tap every day.

Your app is four files (all in the `hr_app` folder):
`streamlit_app.py`, `hr_model.py`, `flyer.py`, `requirements.txt`.

## Step 1 — GitHub (holds the code)

1. Make a free account at **github.com** if you don't have one.
2. Click **New repository**. Name it something like `hr-board`. Leave it Public. Create it.
3. On the repo page, click **Add file → Upload files**, then drag in all four files
   (`streamlit_app.py`, `hr_model.py`, `flyer.py`, `requirements.txt`). Click **Commit changes**.

## Step 2 — Streamlit Community Cloud (runs the code)

1. Go to **share.streamlit.io** and **Continue with GitHub** — sign in and authorize it.
2. Click **Create app** (top right) → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** your `hr-board` repo
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
4. (Optional) Under the URL field, pick a custom subdomain, e.g. `yourname-hr-board`.
5. Click **Deploy**. First build takes a few minutes. You'll land on your live app at
   `https://<your-subdomain>.streamlit.app`.

## Step 3 — Add it to your home screen

**iPhone (Safari):** open your `streamlit.app` URL → tap the **Share** icon →
**Add to Home Screen** → **Add**. A HR Board icon appears like any app.

**Android (Chrome):** open the URL → menu (⋮) → **Add to Home screen / Install app**.

## Daily use

- Tap the icon → it loads **today's** board and the flyer automatically.
- After lineups post (1–3 hrs before first pitch), tap **Refresh data** for the sharp version.
- **Accuracy:** in the notebook, your predictions log to Google Drive as `hr_model_log.csv`.
  Download that file and drop it into the app's **Accuracy check** box to see hit rate,
  Brier score, and calibration — graded against who actually homered.

## Good to know

- **It sleeps.** Free apps go idle after inactivity, so the first open of the day may take
  ~30 seconds to wake up. That's normal.
- **Updating the model** later: just replace the file in GitHub. The app redeploys itself
  within a minute — you never touch the phone.
- **Notebook vs app:** they run the identical model. The notebook is still your durable
  accuracy logbook (it writes to Drive); the app is the daily viewer + flyer, and it can
  read that log to grade it.
- No API keys or secrets are needed. Python 3.12 (Streamlit's default) is fine.
