#!/usr/bin/env python3
"""
Process previously uploaded resumes from S3.
"""

import argparse
from services.ec2endpoint import mfjendpoint
from services.tracker import ScrapingTracker


def main():
    parser = argparse.ArgumentParser(description='Process uploaded resumes from S3')
    parser.add_argument('--hours', type=int, default=24, 
                       help='Hours back to look for resumes (default: 24)')
    parser.add_argument('--job', type=str, 
                       help='Specific job title to process')
    parser.add_argument('--list-jobs', action='store_true',
                       help='List available jobs')
    
    args = parser.parse_args()
    
    endpoint = mfjendpoint()
    tracker = ScrapingTracker()
    
    if args.list_jobs:
        for job_name in tracker.data["jobs"].keys():
            print(job_name)
        return
    
    if args.job:
        result = endpoint.process_specific_job_resumes(args.job)
    else:
        result = endpoint.process_recent_resumes(hours_back=args.hours)
    
    print(f"Processed: {result.get('processed_count', 0)} resumes")
    if result.get('message'):
        print(result['message'])


if __name__ == "__main__":
    main()