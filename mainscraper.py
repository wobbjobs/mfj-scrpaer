from services.playwright import setup_browser, login_to_portal, get_job_listings, navigate_back_to_listings, cleanup_and_save, process_search_results, search_for_job, is_logged_in
from services.tracker import ScrapingTracker
from playwright.sync_api import sync_playwright
from services import google_service

tracker = ScrapingTracker()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=0)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    try: 
        # job post must be same because it is case sensitive
        gs = google_service.GoogleServices()
        sheet_jobs = gs.read_from_sheet()
        login_to_portal(page)
        job_cards, job_count = get_job_listings(page)
        
        resume_state = tracker.get_resume_state()
        if resume_state:
            start_index = resume_state.get("job_index", 0)
            print(f"Resuming from job index {start_index}")
        else:
            start_index = 0

        for i in range(0, len(sheet_jobs[:1])):
            job = sheet_jobs[i]["job"]
            id = sheet_jobs[i]["id"]
            tracker.set_resume_state(i, job, "", 1, 0)
            tracker.save_tracker()
            if not is_logged_in(page):
                print("Session expired, logging in again")
                login_to_portal(page)
            search_for_job(page, job)
            process_search_results(page, job, i)
            navigate_back_to_listings(page)
            gs.writetotrackersheet(jobid=id)
        
        # Clear resume state after completing all jobs
        tracker.clear_resume_state()
        print("Scraping completed successfully. Resume state cleared.")
        
    except Exception as e:
        print(f"\nAn unrecoverable error occurred: {e}")
        page.screenshot(path="error_screenshot.png")
        print("An error screenshot has been saved as 'error_screenshot.png'")
    finally:
        cleanup_and_save(tracker, browser)
