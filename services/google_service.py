from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from config.settings import GOOGLE_SERVICE_JSON,MFJ_TRACKER_SHEET_ID
import re

class GoogleServices:
    def __init__(self):
        if not GOOGLE_SERVICE_JSON or not isinstance(GOOGLE_SERVICE_JSON, dict):
            raise ValueError("GOOGLE_SERVICE_JSON must be a valid dict")

        self.credentials = service_account.Credentials.from_service_account_info(
            GOOGLE_SERVICE_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        self._sheets_service = None
        
    def sheets(self):
        """Return the Google Sheets API client (lazy-loaded)."""
        if self._sheets_service is None:
            self._sheets_service = build("sheets", "v4", credentials=self.credentials)
        return self._sheets_service

    
    def read_from_sheet(
        self,
        sheet_id: str = MFJ_TRACKER_SHEET_ID,
        sheet_range: str = "'ScraperUse'!A1:Z1000",  
    ):
        """
        Return Job published name for rows where 'Expired on MFJ' is NOT truthy.
        """

        def truthy(v: object) -> bool:
            if isinstance(v, bool):
                return v
            s = str(v).strip().lower()
            return s in {"yes", "true", "checked", "1"}
        
        def is_https(url_string: str) -> bool:
            """Check if string starts with https://"""
            if not url_string or not isinstance(url_string, str):
                return False

            return url_string.strip().lower().startswith("https://")

        service = self.sheets()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_range
        ).execute()

        values = result.get("values", [])
        if not values:
            return []

        headers = values[0]
        rows = values[1:]
        header_index = {h.strip().lower(): i for i, h in enumerate(headers)}
        try:
            expired_idx = header_index["expired on mfj"]
            scraped_idx = header_index["scraped"]
            job_name_idx = header_index["job published name"]
            mfj_link_idx = header_index["mfj link"]
            idx = header_index["ed job id"]
        except KeyError:
            raise RuntimeError(
                "Expected headers 'Expired on MFJ' and 'Job published name' not found."
            )
        
        jobs = []
        for row in rows:
            mfj_link_val = row[mfj_link_idx] if mfj_link_idx < len(row) else ""
            scraped_idx_val = row[scraped_idx] if scraped_idx < len(row) else ""
            expired_val = row[expired_idx] if expired_idx < len(row) else ""
            job_name = row[job_name_idx] if job_name_idx < len(row) else ""
            idx_val = row[idx] if idx < len(row) else ""
            if not truthy(expired_val) and job_name and is_https(mfj_link_val) and not truthy(scraped_idx_val):
                jobs.append({"job":job_name,"id":idx_val})

        return jobs

    def writetotrackersheet(
        self,
        jobid,
        sheet_id: str = MFJ_TRACKER_SHEET_ID,
        sheet_range: str = "'ScraperUse'!A1:Z1000",
    ):
        """Update the 'scraped' status to 'yes' for the specified job."""
        service = self.sheets()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_range
        ).execute()

        values = result.get("values", [])
        if not values:
            return

        headers = values[0]
        header_index = {h.strip().lower(): i for i, h in enumerate(headers)}

        try:
            idx = header_index["ed job id"]
            scraped_idx = header_index["scraped"]
        except KeyError:
            raise RuntimeError("Expected headers 'Job published name' and 'scraped' not found.")

        for row_idx, row in enumerate(values[1:], start=2):  # Rows start from 2 (1-based, after header)
            if len(row) > idx and row[idx] == jobid:
                # Update the 'scraped' column for this row
                update_range = f"'ScraperUse'!{chr(65 + scraped_idx)}{row_idx}"
                update_result = service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=update_range,
                    body={"values": [["Yes"]]},
                    valueInputOption="RAW"
                ).execute()
                print(f"Updated scraped status to 'yes' for job: {idx}")
                break
