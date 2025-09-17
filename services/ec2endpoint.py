from services.aws import S3Services
from config.settings import EC2_RESUME_PROCESS_ENDPOINT
from services.tracker import ScrapingTracker
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class mfjendpoint:
    def __init__(self):
        self.endpoint = EC2_RESUME_PROCESS_ENDPOINT
        self.s3_service = S3Services()
        self.tracker = ScrapingTracker()

    def s3linktoprocess(self, s3_links: list[str]) -> dict:
        """
        Send list of S3 links to the resume processing API.
        """
        payload = {"s3_urls": s3_links}
        resp = requests.post(self.endpoint, json=payload)

        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Error {resp.status_code}: {resp.text}")

    def get_recent_resumes_s3_links(self, hours_back: int = 24, job_title: Optional[str] = None) -> List[str]:
        """Get S3 presigned URLs for recently uploaded resumes."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        s3_links = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        if job_title:
            job_titles_to_check = [job_title]
        else:
            job_titles_to_check = []
            for job_name, job_info in self.tracker.data["jobs"].items():
                if job_info.get("last_processed"):
                    try:
                        last_processed = datetime.fromisoformat(job_info["last_processed"])
                        if last_processed >= cutoff_time:
                            job_titles_to_check.append(job_name)
                    except:
                        continue
        
        for job_name in job_titles_to_check:
            clean_job_name = "".join(c for c in job_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
            
            for section in ["applicants", "possible_matches"]:
                s3_prefix = f"{today}/{clean_job_name}/{section}/"
                
                try:
                    response = self.s3_service.s3.list_objects_v2(
                        Bucket=self.s3_service.bucket_name,
                        Prefix=s3_prefix
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            if obj['LastModified'].replace(tzinfo=None) >= cutoff_time:
                                presigned_url = self.s3_service.retrieve_s3_url(obj['Key'])
                                if presigned_url:
                                    s3_links.append(presigned_url)
                except:
                    continue
        
        return s3_links

    def process_recent_resumes(self, hours_back: int = 24, job_title: Optional[str] = None) -> Dict:
        """Get recent resume S3 links and send them for processing."""
        s3_links = self.get_recent_resumes_s3_links(hours_back, job_title)
        
        if not s3_links:
            return {
                "status": "no_files",
                "message": f"No resumes found in the last {hours_back} hours",
                "processed_count": 0
            }
        
        try:
            result = self.s3linktoprocess(s3_links)
            result["processed_count"] = len(s3_links)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "processed_count": 0
            }

    def process_specific_job_resumes(self, job_title: str) -> Dict:
        """Process all resumes for a specific job title uploaded today."""
        return self.process_recent_resumes(hours_back=24, job_title=job_title)