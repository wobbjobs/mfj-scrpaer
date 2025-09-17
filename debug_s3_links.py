#!/usr/bin/env python3
"""
Debug script to show S3 links and understand the structure.
"""

from services.ec2endpoint import mfjendpoint
from services.aws import S3Services
from services.tracker import ScrapingTracker
from datetime import datetime, timedelta


def inspect_s3_structure():
    """Show the S3 bucket structure and recent uploads."""
    s3_service = S3Services()
    tracker = ScrapingTracker()
    
    print("=== S3 Bucket Inspection ===")
    print(f"Bucket: {s3_service.bucket_name}")
    
    # Show today's prefix structure
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\nToday's date prefix: {today}/")
    
    try:
        # List all objects with today's prefix
        response = s3_service.s3.list_objects_v2(
            Bucket=s3_service.bucket_name,
            Prefix=f"{today}/",
            MaxKeys=100
        )
        
        if 'Contents' in response:
            print(f"\nFound {len(response['Contents'])} objects uploaded today:")
            for obj in response['Contents']:
                size_kb = obj['Size'] // 1024
                print(f"  {obj['Key']} ({size_kb} KB, {obj['LastModified']})")
        else:
            print("\nNo objects found for today's date.")
            
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
    
    # Show tracked jobs
    print(f"\n=== Tracked Jobs ===")
    if tracker.data["jobs"]:
        for job_name, job_info in tracker.data["jobs"].items():
            print(f"Job: {job_name}")
            print(f"  Last processed: {job_info.get('last_processed', 'Never')}")
            print(f"  Applicants: {job_info.get('applicant_count', 'Unknown')}")
            print(f"  Matches: {job_info.get('matches_count', 'Unknown')}")
    else:
        print("No jobs tracked yet.")


def test_s3_link_generation():
    """Test the S3 link generation process."""
    endpoint = mfjendpoint()
    
    print("\n=== Testing S3 Link Generation ===")
    
    # Test different time ranges
    time_ranges = [1, 6, 24, 48]
    
    for hours in time_ranges:
        print(f"\nLooking for resumes in the last {hours} hours:")
        try:
            s3_links = endpoint.get_recent_resumes_s3_links(hours_back=hours)
            print(f"  Found {len(s3_links)} links")
            
            # Show first few links (truncated)
            for i, link in enumerate(s3_links[:3], 1):
                filename = link.split('/')[-1].split('?')[0]
                print(f"    {i}. {filename}")
            
            if len(s3_links) > 3:
                print(f"    ... and {len(s3_links) - 3} more")
                
        except Exception as e:
            print(f"  Error: {e}")


def show_expected_s3_structure():
    """Show what the expected S3 structure should look like."""
    tracker = ScrapingTracker()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("\n=== Expected S3 Structure ===")
    print("For each job, files should be uploaded to:")
    print(f"  {today}/[clean_job_name]/applicants/resume_file.pdf")
    print(f"  {today}/[clean_job_name]/possible_matches/resume_file.pdf")
    
    if tracker.data["jobs"]:
        print("\nBased on your tracked jobs, expect these paths:")
        for job_name in tracker.data["jobs"].keys():
            clean_name = "".join(c for c in job_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
            print(f"  {today}/{clean_name}/applicants/")
            print(f"  {today}/{clean_name}/possible_matches/")


def main():
    print("Resume Processing Debug Tool")
    print("=" * 50)
    
    inspect_s3_structure()
    show_expected_s3_structure()
    test_s3_link_generation()
    
    print("\n" + "=" * 50)
    print("Debug complete. Use this information to troubleshoot any issues.")


if __name__ == "__main__":
    main()