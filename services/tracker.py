import json
import os
from datetime import datetime
from pathlib import Path

class ScrapingTracker:
    def __init__(self, tracker_file="data/scraping_tracker.json"):
        self.tracker_file = tracker_file
        self.data = self.load_tracker()
    
    def load_tracker(self):
        """Load existing tracking data or create new structure"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "last_full_scan": None,
            "jobs": {},
            "downloaded_files": set(),
            "resume_state": None
        }
    
    def save_tracker(self):
        """Save tracking data to file"""
        # Convert set to list for JSON serialization
        data_to_save = self.data.copy()
        data_to_save["downloaded_files"] = list(self.data["downloaded_files"])
        
        with open(self.tracker_file, 'w') as f:
            json.dump(data_to_save, f, indent=2)
    
    def is_file_downloaded(self, job_title, section_name, filename):
        """Check if a file has already been downloaded"""
        file_key = f"{job_title}|{section_name}|{filename}"
        return file_key in self.data["downloaded_files"]
    
    def mark_file_downloaded(self, job_title, section_name, filename):
        """Mark a file as downloaded"""
        file_key = f"{job_title}|{section_name}|{filename}"
        
        # Convert to set if it's a list (from JSON loading)
        if isinstance(self.data["downloaded_files"], list):
            self.data["downloaded_files"] = set(self.data["downloaded_files"])
        
        self.data["downloaded_files"].add(file_key)
    
    def update_job_info(self, job_title, applicant_count=None, matches_count=None):
        """Update job information"""
        if job_title not in self.data["jobs"]:
            self.data["jobs"][job_title] = {}
        
        job_info = self.data["jobs"][job_title]
        job_info["last_processed"] = datetime.now().isoformat()
        
        if applicant_count is not None:
            job_info["applicant_count"] = applicant_count
        if matches_count is not None:
            job_info["matches_count"] = matches_count
    
    def should_process_job(self, job_title, hours_threshold=24):
        """Check if a job should be processed based on last processing time"""
        if job_title not in self.data["jobs"]:
            return True
        
        last_processed = self.data["jobs"][job_title].get("last_processed")
        if not last_processed:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_processed)
            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            return hours_since >= hours_threshold
        except:
            return True
    
    def get_job_stats(self, job_title):
        """Get statistics for a job"""
        if job_title not in self.data["jobs"]:
            return None
        return self.data["jobs"][job_title]
    
    def set_resume_state(self, job_index, current_job, section_name, current_page, current_row):
        """Store the current scraping state for resuming"""
        self.data["resume_state"] = {
            "job_index": job_index,
            "current_job": current_job,
            "section_name": section_name,
            "current_page": current_page,
            "current_row": current_row
        }

    def get_resume_state(self):
        """Get the stored resume state"""
        return self.data.get("resume_state")

    def clear_resume_state(self):
        """Clear the resume state after successful completion"""
        self.data["resume_state"] = None

    def cleanup_old_tracking(self, days_old=30):
        """Remove tracking data older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 3600)

        jobs_to_remove = []
        for job_title, job_info in self.data["jobs"].items():
            try:
                last_processed = datetime.fromisoformat(job_info["last_processed"])
                if last_processed.timestamp() < cutoff_date:
                    jobs_to_remove.append(job_title)
            except:
                jobs_to_remove.append(job_title)

        for job_title in jobs_to_remove:
            del self.data["jobs"][job_title]

        print(f"Cleaned up {len(jobs_to_remove)} old job tracking entries")
