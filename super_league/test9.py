import csv
import time
from datetime import datetime
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium_v6.csv" # Version based on successful fixture logic

TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

# --- WebDriver Path (Configure if not in system PATH) ---
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'

def setup_driver():
    options = webdriver.ChromeOptions()
    # To see what the browser is doing, temporarily comment out the next line:
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    return driver

def handle_overlays(driver):
    cookie_accept_selectors = [
        "button#onetrust-accept-btn-handler", 
        "//button[contains(normalize-space(), 'Accept All') or contains(normalize-space(), 'Allow all')]",
        "//button[contains(normalize-space(), 'I Accept') or contains(normalize-space(), 'Accept')]",
    ] # Add more selectors if needed
    for i, selector in enumerate(cookie_accept_selectors):
        try:
            print(f"Looking for overlay button with selector: {selector}")
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH if selector.startswith("//") else By.CSS_SELECTOR, selector))
            )
            button.click()
            print(f"Clicked overlay/cookie button with selector: {selector}")
            time.sleep(2) 
            return True 
        except: # Broad except for this non-critical part
            print(f"Overlay button not found/clickable or error with selector {i+1}: {selector}")
    print("No common overlay buttons handled.")
    return False

def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"\nAttempting to fetch {url} with Selenium...")
    matches_data = []
    html_content = ""
    
    try:
        driver.get(url)
        print(f"Page {url} loaded initially.")
        handle_overlays(driver)

        wait_timeout = 20
        # --- Wait for any match-like element to indicate content might be ready ---
        # This selector should be broad enough to catch various match states.
        # It was successful for fixtures previously.
        wait_for_match_presence_selector = "div[class*='event__match']"
        
        print(f"Waiting up to {wait_timeout} seconds for elements matching '{wait_for_match_presence_selector}' to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, wait_for_match_presence_selector))
        )
        print("Elements matching wait condition are present.")
        html_content = driver.page_source
        
    except TimeoutException:
        print(f"TIMEOUT waiting for elements matching '{wait_for_match_presence_selector}' on {url}.")
        html_content = driver.page_source # Get source anyway for debugging
    except WebDriverException as e_wd:
        print(f"WebDriverException for {url}: {e_wd}")
        traceback.print_exc()
        html_content = driver.page_source 
    except Exception as e_initial:
        print(f"Unexpected error during initial load/wait for {url}: {e_initial}")
        traceback.print_exc()
        html_content = driver.page_source

    # Save HTML for inspection
    if html_content:
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        debug_html_filename = f"{filename_base}_debug_rendered_output_v6.html"
        try:
            with open(debug_html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Saved current HTML for {url} to {debug_html_filename}.")
        except Exception as e_save:
            print(f"Error saving debug HTML: {e_save}")
    else:
        print(f"No HTML content retrieved for {url}. Cannot parse.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Global Match Row Selection - Reverting to simpler approach that worked for fixtures ---
    # IMPORTANT: For the RESULTS page, you MUST inspect its `_debug_rendered_output_v6.html`
    # to find the correct class names if this selector doesn't work.
    # Common pattern for fixtures:
    match_row_selector_fixtures = "div[class*='event__match--scheduled'], div[class*='event__match--live']"
    # Common pattern for results (often includes 'finished'):
    match_row_selector_results = "div[class*='event__match--finished']"
    # General catch-all if the above are too specific:
    match_row_selector_general = "div[class*='event__match']"

    # Choose selector based on page type, or try general if specific fails
    if is_results_page:
        match_rows = soup.select(match_row_selector_results)
        if not match_rows: # Fallback if no finished matches found specifically
            print(f"No matches found with '{match_row_selector_results}', trying general '{match_row_selector_general}' for results page.")
            match_rows = soup.select(match_row_selector_general)
    else: # Fixtures
        match_rows = soup.select(match_row_selector_fixtures)
        if not match_rows: # Fallback for fixtures
            print(f"No matches found with '{match_row_selector_fixtures}', trying general '{match_row_selector_general}' for fixtures page.")
            match_rows = soup.select(match_row_selector_general)

    print(f"Found {len(match_rows)} potential match rows on {url}.")

    # Date/Round will be placeholders for now. We add this logic back once basic data is reliable.
    current_date_placeholder = "Date_Placeholder"
    current_round_placeholder = "Round_Placeholder"

    for idx, row_element in enumerate(match_rows):
        match_details = {
            "Round": current_round_placeholder, "Date": current_date_placeholder,
            "Time": "N/A", "Home": "N/A", "Away": "N/A",
            "HG": "", "AG": "", "Venue": "N/A" # Venue is hard to get from list pages
        }
        try:
            # These selectors worked for fixtures based on your CSV. Verify for results.
            time_div = row_element.select_one("div[class*='event__time']")
            if time_div: match_details["Time"] = time_div.text.strip()
            
            home_team_div = row_element.select_one("div[class*='event__participant--home']")
            if home_team_div: match_details["Home"] = home_team_div.text.strip()
            
            away_team_div = row_element.select_one("div[class*='event__participant--away']")
            if away_team_div: match_details["Away"] = away_team_div.text.strip()

            if is_results_page:
                home_score_div = row_element.select_one("div[class*='event__score--home'], span[class*='event__score--home']")
                if home_score_div:
                    score_text = home_score_div.text.strip()
                    if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                        match_details["HG"] = score_text
                
                away_score_div = row_element.select_one("div[class*='event__score--away'], span[class*='event__score--away']")
                if away_score_div:
                    score_text = away_score_div.text.strip()
                    if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                        match_details["AG"] = score_text
            
            if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                matches_data.append(match_details)
        
        except Exception as e_row_proc:
            print(f"Error processing match row {idx}: {e_row_proc}. Row: {str(row_element)[:150]}")
            continue
    
    print(f"Processed {len(matches_data)} matches from {url}")
    return matches_data

def main():
    driver = None
    try:
        driver = setup_driver()
        print("WebDriver initialized.")

        results_data = scrape_page_with_selenium(driver, RESULTS_URL, is_results_page=True)
        fixtures_data = scrape_page_with_selenium(driver, FIXTURES_URL, is_results_page=False)
        
        all_matches = results_data + fixtures_data
        
        if not all_matches:
            print("\nNo matches found. CSV will be empty or not created.")
            return

        def sort_key_matches(match):
            # Basic sort key, real date/time parsing needed later
            return (match.get('Date', ''), match.get('Time', ''))
        
        all_matches.sort(key=sort_key_matches)
        print(f"\nTotal matches scraped: {len(all_matches)}")

        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"Data written to {OUTPUT_CSV_FILE}")

    finally:
        if driver:
            print("\nQuitting WebDriver.")
            driver.quit()

if __name__ == '__main__':
    main()
