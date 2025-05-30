import csv
import time
from datetime import datetime
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.firefox.service import Service as FirefoxService # Uncomment for Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium_v2.csv"

TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

# --- WebDriver Path (IMPORTANT: Configure if not in system PATH) ---
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'  # Example for Chrome
# GECKODRIVER_PATH = '/path/to/your/geckodriver'    # Example for Firefox

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # If providing path:
    # service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=options)
    # If driver is in PATH:
    driver = webdriver.Chrome(options=options)
    return driver

def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"Attempting to fetch {url} with Selenium...")
    processed_matches_data = [] # Use this list for the new structured parsing
    try:
        driver.get(url)
        wait_timeout = 20
        print(f"Waiting up to {wait_timeout} seconds for main content container to load...")
        
        # --- YOU MUST IDENTIFY A STABLE PARENT CONTAINER FOR ALL EVENTS ---
        # This could be '.sportNameSoccer' as used on Livesport, or similar.
        # Inspect your _rendered_output.html to find this.
        main_event_container_selector = "div.sportNameSoccer" # HYPOTHETICAL - REPLACE
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, main_event_container_selector))
        )
        print("Main event container likely loaded.")
        
        # Optional: small sleep for any final rendering tweaks
        # time.sleep(2)

        html_content = driver.page_source
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        rendered_html_filename = f"{filename_base}_rendered_output_v2.html"
        with open(rendered_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved JS-rendered HTML for {url} to {rendered_html_filename}")

        soup = BeautifulSoup(html_content, 'html.parser')

        # --- NEW STRUCTURED PARSING LOGIC ---
        # Select the main container that holds all date headers, round headers, and matches
        # This selector is CRITICAL and must be identified from your rendered HTML.
        event_area = soup.select_one(main_event_container_selector) # Re-select the waited container
        
        if not event_area:
            print(f"Could not find the main event container ('{main_event_container_selector}') in the page source for {url}. No data to parse.")
            return []

        # Iterate over all direct children or relevant descendant elements within the event_area.
        # This selector needs to capture date headers, round headers, AND match containers in their display order.
        # Often, these are direct children `divs` of a specific wrapper.
        # Example: `event_area.select("> div")` or a more specific `event_area.select("div.eventAndHeaderWrapper")`
        # For Livesport, often a sequence of divs directly under a 'sportName[SPORT]' div.
        
        # HYPOTHETICAL: Assuming elements are direct children divs of the event_area. Adjust as needed.
        # elements_in_sequence = event_area.find_all('div', recursive=False) # Get only direct children
        # OR a more specific selector if there's an intermediate wrapper for each item:
        elements_in_sequence_selector = "div[class*='event__round'], div[class*='event__header'], div[class*='event__match']" # HYPOTHETICAL - REPLACE
        elements_in_sequence = event_area.select(elements_in_sequence_selector)

        print(f"Found {len(elements_in_sequence)} potential elements (headers/matches) in sequence for {url} using selector: '{elements_in_sequence_selector}' on container '{main_event_container_selector}'")


        current_date_from_page = "Date N/A"
        current_round_from_page = "Round N/A"

        for element in elements_in_sequence:
            # --- 1. Check if this element is a DATE HEADER ---
            # Replace with actual selector for date headers from _rendered_output.html
            # Example: class might contain 'event__header--Date' or similar
            date_header_selector = "div[class*='event__header--Date'], div[class*='event__header'][class*='--Date']" # HYPOTHETICAL - REPLACE
            date_node = element.select_one(date_header_selector)
            if date_node: # Check if the current element *is* the date header itself
                 current_date_from_page = date_node.text.strip()
                 print(f"  New Date Header Found: {current_date_from_page}")
                 continue # This element was a header, move to the next element in sequence

            # --- 2. Check if this element is a ROUND HEADER ---
            # Replace with actual selector for round headers
            round_header_selector = "div[class*='event__round']" # HYPOTHETICAL - REPLACE
            round_node = element.select_one(round_header_selector)
            if round_node: # Check if the current element *is* the round header itself
                current_round_from_page = round_node.text.strip()
                print(f"  New Round Header Found: {current_round_from_page}")
                continue # This element was a header, move to the next element

            # --- 3. Check if this element is a MATCH ROW ---
            # This check should be specific enough to identify a match row.
            # Using the presence of home/away participant divs is a good indicator.
            # Ensure these selectors are relative to `element` (which is the potential match row here)
            home_team_node_for_check = element.select_one("div[class*='event__participant--home']")
            away_team_node_for_check = element.select_one("div[class*='event__participant--away']")

            if home_team_node_for_check and away_team_node_for_check:
                # This element is considered a match row
                match_details = {
                    "Round": current_round_from_page, "Date": current_date_from_page,
                    "Time": "N/A", "Home": "N/A", "Away": "N/A",
                    "HG": "", "AG": "", "Venue": "N/A"
                }
                try:
                    time_div = element.select_one("div[class*='event__time']")
                    if time_div: match_details["Time"] = time_div.text.strip()
                    
                    match_details["Home"] = home_team_node_for_check.text.strip()
                    match_details["Away"] = away_team_node_for_check.text.strip()

                    if is_results_page:
                        home_score_div = element.select_one("div[class*='event__score--home']")
                        # Check if text is a digit, but also handle potential non-score text
                        if home_score_div and home_score_div.text.strip().replace('-', '').isdigit(): # Allow negative for point diff if applicable
                            match_details["HG"] = home_score_div.text.strip()
                        
                        away_score_div = element.select_one("div[class*='event__score--away']")
                        if away_score_div and away_score_div.text.strip().replace('-', '').isdigit():
                            match_details["AG"] = away_score_div.text.strip()
                    
                    # Venue: Livesport often doesn't show venue on these list pages directly.
                    # If it does, you'll need to find its selector within the 'element'
                    # venue_node = element.select_one("YOUR_VENUE_SELECTOR_HERE")
                    # if venue_node: match_details["Venue"] = venue_node.text.strip()

                    if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                        processed_matches_data.append(match_details)
                
                except Exception as e_row_proc:
                    print(f"Error processing a specific match row: {e_row_proc}. Row HTML: {str(element)[:200]}")
                    traceback.print_exc()
                    continue # Skip this match row if there's an error
            # else:
                # print(f"Element skipped (not a date, round, or recognized match): {str(element)[:100]}") # Optional: for debugging non-matching elements
        
        print(f"Processed {len(processed_matches_data)} matches from {url}")
        return processed_matches_data

    except TimeoutException:
        print(f"Timeout waiting for page elements on {url}.")
        return []
    except WebDriverException as e_wd:
        print(f"WebDriverException with {url}: {e_wd}")
        return []
    except Exception as e_general:
        print(f"Unexpected error during Selenium/BeautifulSoup processing for {url}: {e_general}")
        traceback.print_exc()
        return []

def main():
    driver = None
    try:
        driver = setup_driver()
        print("WebDriver initialized.")

        print("\nScraping results...")
        results_data = scrape_page_with_selenium(driver, RESULTS_URL, is_results_page=True)
        
        print(f"\nScraping fixtures...")
        fixtures_data = scrape_page_with_selenium(driver, FIXTURES_URL, is_results_page=False)
        
        all_matches = results_data + fixtures_data
        
        if not all_matches:
            print("\nNo matches found in total. CSV file will be empty. Exiting.")
            return

        def sort_key_matches(match):
            try:
                date_str = match.get('Date', '01.01.1900') # Default for sorting if missing
                time_str = match.get('Time', '00:00')
                
                # Attempt to parse known date formats from Livesport
                # Common: "14.05." (current year implied), "14.05.2024", "Tomorrow", "Today" + Time
                # This parsing needs to be robust based on actual extracted date_str format
                # For now, assuming date_str will be cleaned to dd.mm.yyyy or dd.mm.
                
                # Basic handling if year is missing from "dd.mm."
                if date_str.count('.') == 1 and date_str.endswith('.'):
                     date_str = date_str + str(datetime.now().year) # Append current year
                elif date_str.count('.') == 1 and not date_str.endswith('.'): # e.g. "14.05"
                     parts = date_str.split('.')
                     if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                         date_str = f"{parts[0]}.{parts[1]}.{datetime.now().year}"


                # This will require careful adjustment based on how you standardize 'date_str'
                # For "Round N/A", "Date N/A" this will fail, hence the broad except
                return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
            except (ValueError, TypeError) as e:
                # print(f"Warning: Could not parse date/time for sorting: D='{match.get('Date')}' T='{match.get('Time')}' - Error: {e}")
                return datetime.max # Put unparseable entries at the end
        
        all_matches.sort(key=sort_key_matches)
        print(f"\nTotal matches scraped and sorted: {len(all_matches)}")

        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"Data successfully written to {OUTPUT_CSV_FILE}")

    finally:
        if driver:
            print("\nQuitting WebDriver.")
            driver.quit()

if __name__ == '__main__':
    main()
    
