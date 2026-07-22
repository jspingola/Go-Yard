# Turn on self-logging (one time, ~10 minutes)

This lets the app save its picks by itself to a Google Sheet you own, so you
never touch the notebook again. After this, logging and grading are automatic.

## 1. Make the log sheet
Go to Google Drive → **New → Google Sheets**. Name it "HR Model Log". Copy its
URL from the address bar (you'll paste it in step 4).

## 2. Create a service account (the app's "robot user")
1. Go to **console.cloud.google.com** and create a project (any name).
2. **APIs & Services → Library**: search **Google Sheets API** → **Enable**.
   Then search **Google Drive API** → **Enable**.
3. **APIs & Services → Credentials → Create credentials → Service account**.
   Give it a name, click through Create → Done.
4. Click the new service account → **Keys → Add key → Create new key → JSON**.
   A `.json` file downloads. Keep it handy.
5. Note the service account's **email** (ends in `...iam.gserviceaccount.com`).

## 3. Share the sheet with the robot
Open your Google Sheet → **Share** → paste the service-account email →
set it to **Editor** → Send. (This is what lets the app write to it.)

## 4. Paste the credentials into Streamlit
On **share.streamlit.io**, open your app → **⋮ → Settings → Secrets**, and paste
the block below, filling values from your downloaded JSON:

```toml
log_sheet_url = "https://docs.google.com/spreadsheets/d/PASTE_YOUR_SHEET_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\nLINE1\nLINE2\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Every field maps 1:1 to the JSON file. **The one gotcha:** `private_key` must keep
its `\n` newline markers exactly as they appear in the JSON, inside the quotes.

Click **Save**. The app reboots, detects the secrets, and starts logging on the
next run. The Accuracy section switches to "Grade my logged picks" — no uploads.

## That's it
From now on: open the app, it runs and logs itself; tap **Grade my logged picks**
any day after games finish. If you ever want to eyeball the raw history, just open
that Google Sheet — every night's top 10 is right there.
