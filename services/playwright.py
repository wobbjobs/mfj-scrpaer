from services.google_service import GoogleServices
from services.aws import S3Services,get_or_create_job_folder
from config.settings import MYFUTUREJOBS_PASS, MYFUTUREJOBS_USER, MYFUTUREJOBS_URL
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from services.tracker import ScrapingTracker
import time
import os
from services.tracker import ScrapingTracker

tracker = ScrapingTracker()


def make_safe_filename(name):
    """Cleans a string to be a valid filename."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()


def setup_browser():
    """Set up and return a browser instance with appropriate configuration."""
    from playwright.sync_api import sync_playwright
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=50
    )
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    return playwright, browser, page


def login_to_portal(page):
    """
    Log into MyFutureJob portal
    """
    print("Navigating to login page...")
    page.goto(MYFUTUREJOBS_URL)
    page.fill('input[name="username"]', MYFUTUREJOBS_USER)
    page.fill('input[name="password"]', MYFUTUREJOBS_PASS)
    time.sleep(3)
    page.click('input[name="login"]')
    page.wait_for_load_state('networkidle')


def get_job_listings(page):
    """
    Calculate the number of job postings available on the page.
    """
    job_cards = page.locator('[data-test="swipe-vacancySummary-container"]')
    job_count = job_cards.count()
    print(f"Found {job_count} job postings to process.")
    return job_cards, job_count


def search_for_job(page, search_term):
    """Search for a specific job using the search functionality."""
    try:
        print(f"Searching for job: '{search_term}'")
        start_time = time.time()

        search_input = page.locator('[data-test="swipe-autocomplete--input"]').first
        print("Clearing search field...")
        search_input.clear()

        print(f"Typing '{search_term}' into search field...")
        typing_start = time.time()
        search_input.fill(search_term)
        typing_end = time.time()
        print(f"Typing completed in {typing_end - typing_start:.2f} seconds")

        print("Clicking search button...")
        click_start = time.time()
        search_button = page.locator('[data-test="swipe-searchInputs-search"]')
        search_button.click()
        click_end = time.time()
        print(f"Search button clicked in {click_end - click_start:.2f} seconds")

        print("Waiting for search results to load...")
        wait_start = time.time()
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(3)
        wait_end = time.time()
        print(f"Search results loaded in {wait_end - wait_start:.2f} seconds")

        end_time = time.time()
        total_time = end_time - start_time
        print(f"Search completed for: '{search_term}' in {total_time:.2f} seconds total")
        return True
    except Exception as e:
        print(f"Error during search: {e}")
        return False


from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import os, time

def download_cvs_from_section(page, section_name, section_selector, job_title, download_index_start):
    """
    Downloads all CVs from a section to local disk:
      tmp/<job_title>/<section_name>/filename.pdf
    Handles pagination and both Applicants / Possible Matches tables.
    """
    print(f"\n[+] Checking for '{section_name}' section...")

    # local dirs
    job_dir = os.path.join("tmp", make_safe_filename(job_title))
    section_dir = os.path.join(job_dir, section_name.lower().replace(" ", "_"))
    os.makedirs(section_dir, exist_ok=True)

    # quick presence check
    if page.locator(section_selector).count() == 0 or not page.locator(section_selector).is_visible():
        print(f"[-] Section '{section_name}' not found or not visible. Skipping.")
        return download_index_start

    download_index = download_index_start
    current_page_num = 1

    while True:
        # re-select container each loop to avoid stale refs after pagination
        section_container = page.locator(section_selector)
        print(f"  - Scanning Page {current_page_num} in '{section_name}' for '{job_title}'")
        try:
            page.wait_for_load_state('networkidle', timeout=20000)
        except PlaywrightTimeoutError:
            print("    WARN: networkidle timed out; continuing…")

        rows = section_container.locator('[data-test="swipe-table-row"]')
        row_count = rows.count()
        if row_count == 0 and current_page_num == 1:
            print("    No rows found on this page.")
            break

        for i in range(row_count):
            row = rows.nth(i)

            try:
                if section_name == "Applicants":
                    # --- open the attachments menu in the DOWNLOAD column ---
                    download_cell = row.locator('[data-test="swipe-table-cell--download"]').first
                    toggle = download_cell.locator('[data-test="swipe-applicantsOverview-attachments"]').first

                    # ensure in view and close any open menus first
                    try:
                        row.scroll_into_view_if_needed()
                        download_cell.scroll_into_view_if_needed()
                        page.keyboard.press("Escape")
                    except Exception:
                        pass

                    # open dropdown
                    toggle.wait_for(state="attached", timeout=5000)
                    toggle.click()  # aria-expanded toggles to true

                    # wait for the CV item in THIS cell's dropdown
                    cv_item = download_cell.locator('div.dropdown-menu >> button.dropdown-item:has-text("CV")').first
                    cv_item.wait_for(state="visible", timeout=6000)

                    # click CV and capture download
                    with page.expect_download() as di:
                        cv_item.click()
                    d = di.value

                    # build filename from Name column
                    try:
                        name_el = row.locator('[data-test="swipe-table-cell--jobseekerName"] span').first
                        applicant_name = (name_el.inner_text() or "").strip() if name_el.count() else f"applicant_{download_index}"
                    except Exception:
                        applicant_name = f"applicant_{download_index}"

                    filename = f"{make_safe_filename(applicant_name) or f'applicant_{download_index}'}.pdf"
                    local_path = os.path.join(section_dir, filename)

                    # de-dupe + save + track
                    if tracker.is_file_downloaded(job_title, section_name, filename):
                        print(f"    SKIP: {filename} (already downloaded)")
                    else:
                        d.save_as(local_path)
                        print(f"    Downloaded: {local_path}")
                        tracker.mark_file_downloaded(job_title, section_name, filename)
                        download_index += 1

                    # close dropdown for cleanliness
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass

                elif section_name == "Possible Matches":
                    # Prefer the icon inside the CV column
                    cv_cell = row.locator('[data-test="swipe-table-cell--cv"]').first
                    download_btn = cv_cell.locator('.fa-download, .fa-file-pdf-o, [data-test="swipe-download"]').first

                    if download_btn.count() == 0:
                        # Extra fallback: any download icon in the row
                        download_btn = row.locator('.fa-download, .fa-file-pdf-o, [data-test="swipe-download"]').first

                    if download_btn.count() == 0:
                        print(f"    No download button found in row {i+1} (after fallback), skipping…")
                        continue

                    # Make sure the row and CV cell are onscreen, then click forcibly
                    try:
                        row.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        cv_cell.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    with page.expect_download() as di:
                        # Click even if Playwright thinks it's not visible (icon can be within overflow container)
                        download_btn.click(force=True)
                    d = di.value

                    # candidate name (best-effort)
                    candidate_name = None
                    try:
                        name_el = row.locator('[data-test="swipe-table-cell--name"] span').first
                        if name_el.count():
                            candidate_name = (name_el.inner_text() or "").strip()
                    except:
                        pass
                    if not candidate_name:
                        try:
                            guess = row.locator('span.add-ellipsis.cursor-pointer').first
                            candidate_name = (guess.inner_text() or "").strip() if guess.count() else None
                        except:
                            pass
                    if not candidate_name:
                        candidate_name = f"candidate_{download_index}"

                    filename = f"{make_safe_filename(candidate_name) or f'candidate_{download_index}'}_{download_index}.pdf"

                    if tracker.is_file_downloaded(job_title, section_name, filename):
                        print(f"    SKIP: {filename} (already downloaded)")
                        continue

                    local_path = os.path.join(section_dir, filename)
                    d.save_as(local_path)
                    print(f"    Downloaded: {local_path}")

                    tracker.mark_file_downloaded(job_title, section_name, filename)
                    download_index += 1

                    
                time.sleep(3)
                if download_index > 1500:
                    print(f"⚠️ Reached hard limit of 1500 downloads in '{section_name}'. Stopping.")
                    return download_index

            except PlaywrightTimeoutError:
                print(f"    WARN: Timeout while processing row {i+1}.")
                try: page.keyboard.press("Escape")
                except: pass
            except Exception as e:
                print(f"    ERROR row {i+1}: {e}")
                try: page.keyboard.press("Escape")
                except: pass

        # --- pagination: try Next, else next number ---
        pagination = section_container.locator("ul.pagination")
        if pagination.count() == 0:
            print(f"  - Finished all pages for '{section_name}'.")
            break

        # Try Next button first (aria-label or » symbol)
        next_btn = pagination.locator(
            'li.page-item:not(.disabled) a[aria-label="Next"], '
            'li.page-item:not(.disabled) a:has-text("»")'
        ).first

        if next_btn.count() and next_btn.is_visible():
            print("    Navigating to next page via Next…")
            next_btn.click()
            page.wait_for_load_state("networkidle")
            current_page_num += 1
            continue

        # Fallback: numbered pages
        next_number = str(current_page_num + 1)
        next_link = pagination.locator(f'li.page-item a.page-link:has-text("{next_number}")').first

        if not (next_link.count() and next_link.is_visible()):
            print(f"  - Finished all pages for '{section_name}'.")
            break

        print(f"    Navigating to page {next_number}…")
        next_link.click()
        page.wait_for_load_state("networkidle")
        current_page_num += 1

    return download_index


def process_search_results(page):
    """Process the first job from search results."""
    try:
        # Get job cards after search
        job_cards = page.locator('[data-test="swipe-vacancySummary-container"]')
        job_count = job_cards.count()
        
        if job_count == 0:
            print("No jobs found matching your search criteria.")
            return
        
        print(f"Found {job_count} job(s) matching your search.")
        
        # Process the first job in search results
        job = job_cards.nth(0)
        job_title = "Unknown Job"
        
        try:
            job.scroll_into_view_if_needed()
            job_title = " ".join([el.inner_text().strip() for el in job.locator('h5.font-size-big span').all()])

            
            print(f"\n--- Processing SEARCHED Job: {job_title} ---")
            
            job.click()
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            download_index_counter = 1

            if download_index_counter > 1500:
                return download_index_counter

            # Process "Applicants" section
            download_index_counter = download_cvs_from_section(
                page, "Applicants", "#applicants", job_title, download_index_counter
            )

            # Process "Possible Matches" section
            download_index_counter = download_cvs_from_section(
                page, "Possible Matches", "#matchedJobseekers", job_title, download_index_counter
            )
            
            # Update job tracking info
            tracker.update_job_info(job_title)
            
            print(f"\n--- Completed processing: {job_title} ---")
            
        except Exception as e:
            print(f"ERROR: A critical error occurred while processing job '{job_title}': {e}")
            
    except Exception as e:
        print(f"ERROR: Failed to process search results: {e}")


def navigate_back_to_listings(page):
    """Navigate back to the job listings page after processing a job."""
    try:
        page.go_back()
        # Wait for the job list to be present again before the next loop
        page.wait_for_selector('[data-test="swipe-vacancySummary-container"]', timeout=60000)
        page.wait_for_load_state('networkidle', timeout=30000)
    except Exception as nav_error:
        print(f"    Warning: Navigation back failed: {nav_error}")
        print("    Attempting to reload the main page...")
        page.goto(MYFUTUREJOBS_URL.replace('/auth/', '/'))  # Go to main portal
        page.wait_for_load_state('networkidle', timeout=30000)


def cleanup_and_save(tracker, browser, upload_to_s3=True, bucket_name=None, process_resumes=True):
    """Handle cleanup, save tracking data, upload to S3, and optionally process resumes."""
    print("\nScript finished. Closing browser.")
    tracker.save_tracker()
    print("Tracking data saved.")
    
    if upload_to_s3:
        print("\nStarting S3 upload process...")
        try:
            s3_service = S3Services(bucket_name=bucket_name)
            upload_results = s3_service.upload_all_tmp_files_to_s3()
            
            total_uploaded = sum(result['total_uploaded'] for result in upload_results)
            total_failed = sum(result['total_failed'] for result in upload_results)
            
            print(f"\n=== S3 Upload Summary ===")
            print(f"Jobs processed: {len(upload_results)}")
            print(f"Total files uploaded: {total_uploaded}")
            print(f"Total files failed: {total_failed}")
            
            for result in upload_results:
                if result['total_uploaded'] > 0 or result['total_failed'] > 0:
                    print(f"  {result['job_title']}: {result['total_uploaded']} uploaded, {result['total_failed']} failed")
            
            # Process uploaded resumes if requested and files were uploaded
            if process_resumes and total_uploaded > 0:
                try:
                    from services.ec2endpoint import mfjendpoint
                    endpoint = mfjendpoint()
                    result = endpoint.process_recent_resumes(hours_back=1)
                    print(f"Resumes processed: {result.get('processed_count', 0)}")
                except Exception as e:
                    print(f"Resume processing failed: {e}")
            
        except Exception as e:
            print(f"ERROR: S3 upload failed: {e}")
    
    browser.close()