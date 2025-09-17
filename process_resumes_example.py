#!/usr/bin/env python3
"""
Example script showing how to retrieve S3 links for recently saved resumes
and call the s3linktoprocess function.
"""

from services.ec2endpoint import mfjendpoint
from services.tracker import ScrapingTracker
from services.aws import S3Services


def main():
    """
    Demonstrates different ways to process recently uploaded resumes.
    """
    
    # Initialize the endpoint handler
    endpoint = mfjendpoint()
    
    print("=== Resume Processing Examples ===\n")
    
    # Example 1: Process all resumes uploaded in the last 24 hours
    print("1. Processing all resumes from the last 24 hours:")
    try:
        result = endpoint.process_recent_resumes(hours_back=24)
        print(f"   Status: {result.get('status', 'success')}")
        print(f"   Processed: {result.get('processed_count', 0)} resumes")
        if result.get('message'):
            print(f"   Message: {result['message']}")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 2: Process resumes from the last 6 hours only
    print("2. Processing resumes from the last 6 hours:")
    try:
        result = endpoint.process_recent_resumes(hours_back=6)
        print(f"   Status: {result.get('status', 'success')}")
        print(f"   Processed: {result.get('processed_count', 0)} resumes")
        if result.get('message'):
            print(f"   Message: {result['message']}")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 3: Process resumes for a specific job title
    job_title = "Software Engineer"  # Replace with actual job title
    print(f"3. Processing resumes for specific job: '{job_title}'")
    try:
        result = endpoint.process_specific_job_resumes(job_title)
        print(f"   Status: {result.get('status', 'success')}")
        print(f"   Processed: {result.get('processed_count', 0)} resumes")
        if result.get('message'):
            print(f"   Message: {result['message']}")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 4: Just get the S3 links without processing (for inspection)
    print("4. Getting S3 links for inspection (last 24 hours):")
    try:
        s3_links = endpoint.get_recent_resumes_s3_links(hours_back=24)
        print(f"   Found {len(s3_links)} resume(s)")
        for i, link in enumerate(s3_links[:5], 1):  # Show first 5 links
            print(f"   {i}. {link[:100]}...")  # Truncate for readability
        if len(s3_links) > 5:
            print(f"   ... and {len(s3_links) - 5} more")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 5: Manual processing with custom S3 links
    print("5. Manual processing with custom S3 links:")
    try:
        # Get links manually
        s3_links = endpoint.get_recent_resumes_s3_links(hours_back=48)
        
        if s3_links:
            # Filter or modify the list as needed
            selected_links = s3_links[:10]  # Process only first 10
            
            print(f"   Processing {len(selected_links)} selected resumes...")
            result = endpoint.s3linktoprocess(selected_links)
            print(f"   Processing completed successfully")
            print(f"   Response: {result}")
        else:
            print("   No S3 links found to process")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")


def process_by_job_selection():
    """
    Interactive function to let user select which jobs to process.
    """
    tracker = ScrapingTracker()
    endpoint = mfjendpoint()
    
    print("=== Interactive Job Selection ===")
    
    # Show available jobs
    jobs = list(tracker.data["jobs"].keys())
    if not jobs:
        print("No jobs found in tracker. Run the scraper first.")
        return
    
    print("\nAvailable jobs:")
    for i, job in enumerate(jobs, 1):
        job_info = tracker.data["jobs"][job]
        last_processed = job_info.get("last_processed", "Never")
        print(f"{i}. {job} (Last processed: {last_processed})")
    
    print(f"{len(jobs) + 1}. Process all jobs")
    print("0. Exit")
    
    try:
        choice = int(input("\nSelect job to process (enter number): "))
        
        if choice == 0:
            return
        elif choice == len(jobs) + 1:
            # Process all jobs
            result = endpoint.process_recent_resumes()
            print(f"\nProcessed {result.get('processed_count', 0)} resumes from all jobs")
        elif 1 <= choice <= len(jobs):
            # Process specific job
            selected_job = jobs[choice - 1]
            result = endpoint.process_specific_job_resumes(selected_job)
            print(f"\nProcessed {result.get('processed_count', 0)} resumes for '{selected_job}'")
        else:
            print("Invalid selection")
            
    except ValueError:
        print("Please enter a valid number")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run the main examples
    main()
    
    # Uncomment to run interactive selection
    # process_by_job_selection()