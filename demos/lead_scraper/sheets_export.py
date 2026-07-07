"""
Optional Google Sheets export for the lead scraper.

This is intentionally isolated: the CSV path works with ZERO credentials, and
this module is only imported when output.google_sheets.enabled is true in the
config. It will NOT silently pretend to work — if the service account file or
libraries are missing, it raises a clear error telling you exactly what to do.

SETUP (one-time, ~5 min):
  1. pip install gspread google-auth
  2. Google Cloud Console -> create a project -> enable the Google Sheets API.
  3. Create a Service Account -> add a JSON key -> download it as
     service_account.json into this folder (it is .gitignored).
  4. Open your target Google Sheet and Share it with the service account's
     email (client_email in the JSON), giving Editor access.
  5. Put the sheet's ID in config: output.google_sheets.spreadsheet_id
     (the long string in the sheet URL between /d/ and /edit).
"""
from __future__ import annotations

import os


def export_to_sheets(rows: list[dict], fieldnames: list[str], gs_cfg: dict) -> None:
    sa_path = gs_cfg.get("service_account_json", "service_account.json")
    spreadsheet_id = gs_cfg.get("spreadsheet_id", "")
    worksheet_name = gs_cfg.get("worksheet", "Leads")

    if not spreadsheet_id:
        raise RuntimeError(
            "google_sheets.enabled is true but spreadsheet_id is empty. "
            "Set output.google_sheets.spreadsheet_id in your config."
        )
    if not os.path.exists(sa_path):
        raise RuntimeError(
            f"google_sheets.enabled is true but service account file '{sa_path}' "
            "was not found. See the SETUP steps at the top of sheets_export.py. "
            "(CSV output still works without this.)"
        )
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        raise RuntimeError(
            "Google Sheets export needs extra libraries. Run:\n"
            "    pip install gspread google-auth\n"
            f"(original import error: {e})"
        )

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_key(spreadsheet_id)

    try:
        ws = sh.worksheet(worksheet_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=len(rows) + 10, cols=len(fieldnames) + 2)

    values = [fieldnames] + [[row.get(f, "") for f in fieldnames] for row in rows]
    ws.update("A1", values)
