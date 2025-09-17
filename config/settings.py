from dotenv import load_dotenv
import os
import json

load_dotenv(dotenv_path=os.path.join("credentials", "development.env"))

MYFUTUREJOBS_USER = os.getenv('MYFUTUREJOBS_USER')
MYFUTUREJOBS_PASS = os.getenv('MYFUTUREJOBS_PASS')
MYFUTUREJOBS_URL = os.getenv('MYFUTUREJOBS_URL')
GOOGLE_SERVICE_FILE = os.path.join("credentials", "googleservice.json")
with open(GOOGLE_SERVICE_FILE, "r", encoding="utf-8") as f:GOOGLE_SERVICE_JSON = json.load(f)   
MFJ_TRACKER_SHEET_ID = os.getenv('MFJ_TRACKER_SHEET_ID')
DDTRACE_API_KEY = os.getenv('DDTRACE_API_KEY')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
AWS_S3_REGION = os.getenv('AWS_S3_REGION')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
EC2_RESUME_PROCESS_ENDPOINT = os.getenv('EC2_RESUME_PROCESS_ENDPOINT')

