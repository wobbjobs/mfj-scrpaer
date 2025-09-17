from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from config.settings import GOOGLE_SERVICE_JSON,MFJ_TRACKER_SHEET_ID



class GoogleServices:
    def __init__(self):
        if not GOOGLE_SERVICE_JSON or not isinstance(GOOGLE_SERVICE_JSON, dict):
            raise ValueError("GOOGLE_SERVICE_JSON must be a valid dict")

        self.credentials = service_account.Credentials.from_service_account_info(
            GOOGLE_SERVICE_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
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
        sheet_range: str = "'Kate Use'!A1:Z1000",  
    ):
        """
        Return Job published name for rows where 'Expired on MFJ' is NOT truthy.
        """

        def truthy(v: object) -> bool:
            if isinstance(v, bool):
                return v
            s = str(v).strip().lower()
            return s in {"yes", "true", "checked", "1"}

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
            job_name_idx = header_index["job published name"]
        except KeyError:
            raise RuntimeError(
                "Expected headers 'Expired on MFJ' and 'Job published name' not found."
            )

        jobs = []
        for row in rows:
            expired_val = row[expired_idx] if expired_idx < len(row) else ""
            job_name = row[job_name_idx] if job_name_idx < len(row) else ""
            if not truthy(expired_val) and job_name:
                jobs.append(job_name)

        return jobs

    def writetotrackersheet(self):
        #Todo: Add a write to google sheet function
        pass
    

