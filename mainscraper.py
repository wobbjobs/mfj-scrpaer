from services.playwright import setup_browser, login_to_portal, get_job_listings, navigate_back_to_listings, cleanup_and_save, process_search_results, search_for_job
from services.tracker import ScrapingTracker
from playwright.sync_api import sync_playwright


tracker = ScrapingTracker()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=0)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    try:
        login_to_portal(page)
        job_cards, job_count = get_job_listings(page)
        search_term = input("Enter job title to search for: ").strip()
        search_for_job(page, search_term)
        process_search_results(page)

        
    except Exception as e:
        print(f"\nAn unrecoverable error occurred: {e}")
        page.screenshot(path="error_screenshot.png")
        print("An error screenshot has been saved as 'error_screenshot.png'")
    finally:
        cleanup_and_save(tracker, browser)
        
