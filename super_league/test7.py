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
OUTPUT_CSV_FILE = "super_league_data_selenium_v3.csv" # Incremented version

TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

# --- WebDriver Path (IMPORTANT: Configure if not in system PATH) ---
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'
# GECKODRIVER_PATH = '/path/to/your/geckodriver'

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
    processed_matches_data = []
    try:
        driver.get(url)
        wait_timeout = 20 # seconds
        
        # IMPORTANT: Replace with the correct selector for the main container of all events for this sport/league.
        # For rugby league on Livesport, this is very likely 'div.sportNameRUGBYLEAGUE'
        # Inspect your _rendered_output_v2.html to confirm.
        main_event_container_selector = "div.sportNameRUGBYLEAGUE" # YOUR_SELECTOR_HERE (Likely correct for Livesport)
        
        print(f"Waiting up to {wait_timeout} seconds for main content container ('{main_event_container_selector}') to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, main_event_container_selector))
        )
        print("Main event container likely loaded.")
        
        # time.sleep(1) # Optional small delay if content still rendering

        html_content = driver.page_source
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        rendered_html_filename = f"{filename_base}_rendered_output_v3.html" # Save new version
        with open(rendered_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved JS-rendered HTML for {url} to {rendered_html_filename}")

        soup = BeautifulSoup(html_content, 'html.parser')
        
        event_area = soup.select_one(main_event_container_selector)
        if not event_area:
            print(f"CRITICAL: Could not find the main event container ('{main_event_container_selector}') in the page source for {url}. Cannot parse data.")
            return []

        # IMPORTANT: This selector needs to get all direct child elements within event_area that are
        # EITHER a date header, a round header, OR a match container, in page order.
        # Option 1: If they are all direct children divs:
        # elements_in_sequence = event_area.select(":scope > div") # ':scope' refers to event_area itself
        # Option 2: If they have distinct classes allowing them to be selected together:
        elements_in_sequence_selector = "div[class*='event__header'], div[class*='event__round'], div[class*='event__match']" # YOUR_SELECTOR_HERE (Educated guess)
        elements_in_sequence = event_area.select(elements_in_sequence_selector)
        # Option 3 (if results page has different match class, e.g. 'results__event'):
        # if is_results_page:
        #     elements_in_sequence_selector = "div[class*='event__header'], div[class*='event__round'], div[class*='results__event']" # YOUR_SELECTOR_HERE
        # elements_in_sequence = event_area.select(elements_in_sequence_selector)


        print(f"Found {len(elements_in_sequence)} potential elements (headers/matches) in sequence from '{main_event_container_selector}' using '{elements_in_sequence_selector}'.")

        current_date_from_page = "Date N/A"
        current_round_from_page = "Round N/A"

        for element_idx, element in enumerate(elements_in_sequence):
            # --- 1. Check if this element is a DATE HEADER ---
            # IMPORTANT: Inspect your HTML. Date headers might have classes like 'event__header--main' or 'event__header--Date'.
            # They might contain the full date or relative terms like "TODAY", "TOMORROW".
            date_header_selector = "div[class*='event__header--Date'], div.event__header[class*='--Date']" # YOUR_SELECTOR_HERE (Educated guess)
            # Check if the current 'element' itself matches the date_header_selector
            is_date_header = element.matches(date_header_selector)
            if is_date_header:
                 # Sometimes the text is in a child, sometimes direct.
                 date_text_node = element.select_one(".event__title--name, .event__title--date") or element # Get text from child or self
                 current_date_from_page = date_text_node.text.strip()
                 print(f"  [Elem {element_idx}] Date Header: {current_date_from_page}")
                 continue

            # --- 2. Check if this element is a ROUND HEADER ---
            # IMPORTANT: Inspect your HTML. Round headers might have a class like 'event__round'.
            round_header_selector = "div[class*='event__round']" # YOUR_SELECTOR_HERE (Educated guess)
            is_round_header = element.matches(round_header_selector)
            if is_round_header:
                current_round_from_page = element.text.strip()
                print(f"  [Elem {element_idx}] Round Header: {current_round_from_page}")
                continue

            # --- 3. Check if this element is a MATCH ROW ---
            # IMPORTANT: This must reliably identify a match row.
            # For the RESULTS page (which previously found 0), pay close attention to its match row classes.
            # The check for home/away participants is a good way to confirm.
            # Ensure these participant selectors are correct for BOTH fixtures and results pages.
            home_team_node_for_check = element.select_one("div[class*='event__participant--home']")
            away_team_node_for_check = element.select_one("div[class*='event__participant--away']")

            if home_team_node_for_check and away_team_node_for_check:
                # This element is considered a match row
                # print(f"  [Elem {element_idx}] Potential Match Found") # Debug
                match_details = {
                    "Round": current_round_from_page, "Date": current_date_from_page,
                    "Time": "N/A", "Home": "N/A", "Away": "N/A",
                    "HG": "", "AG": "", "Venue": "N/A" # Venue usually not on list pages
                }
                try:
                    time_div = element.select_one("div[class*='event__time']")
                    if time_div: match_details["Time"] = time_div.text.strip()
                    
                    match_details["Home"] = home_team_node_for_check.text.strip()
                    match_details["Away"] = away_team_node_for_check.text.strip()

                    if is_results_page:
                        home_score_div = element.select_one("div[class*='event__score--home'], span[class*='event__score--home']") # Also check span
                        if home_score_div:
                            score_text = home_score_div.text.strip()
                            if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                                match_details["HG"] = score_text
                        
                        away_score_div = element.select_one("div[class*='event__score--away'], span[class*='event__score--away']") # Also check span
                        if away_score_div:
                            score_text = away_score_div.text.strip()
                            if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                                match_details["AG"] = score_text
                    
                    if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                        processed_matches_data.append(match_details)
                
                except Exception as e_row_proc:
                    print(f"Error processing a specific match row [Elem {element_idx}]: {e_row_proc}. Row HTML: {str(element)[:200]}")
                    # traceback.print_exc() # Can be very verbose
                    continue
            # else:
                # print(f"  [Elem {element_idx}] Element skipped (not a date, round, or recognized match): {str(element.get('class', 'NoClass'))}") # Debug
        
        print(f"Processed {len(processed_matches_data)} matches from {url}")
        return processed_matches_data

    except TimeoutException:
        print(f"Timeout waiting for page elements on {url}.")
        return []
    except WebDriverException as e_wd:
        print(f"WebDriverException with {url}: {e_wd}")
        traceback.print_exc() # Show WebDriver errors
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
            # This date/time parsing needs to be robust based on actual extracted formats
            # For now, it's a placeholder.
            try:
                date_str = match.get('Date', '') 
                time_str = match.get('Time', '00:00')

                # Placeholder: You'll need to parse dates like "14.05.", "TODAY", "YESTERDAY", etc.
                # And combine them with time to create a full datetime object.
                # This current parsing is very basic and likely to fail for many Livesport date formats.
                if "N/A" in date_str or not date_str or "N/A" in time_str:
                    return datetime.max # Put unparseable/placeholder entries at the end
                
                # Attempt to handle "dd.mm." format by adding current year
                if date_str.count('.') == 1 and date_str.endswith('.'): # e.g. "14.05."
                    date_str = date_str + str(datetime.now().year)
                elif date_str.count('.') == 1: # e.g. "14.05"
                    parts = date_str.split('.')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                         date_str = f"{parts[0]}.{parts[1]}.{datetime.now().year}"
                
                # Default format, you WILL need to adjust this based on what `current_date_from_page` becomes.
                # Consider handling relative dates like "Yesterday", "Today", "Tomorrow" separately.
                return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
            except Exception: # Catch broad exception as date formats can vary wildly
                # print(f"Warning: Could not parse date/time for sorting: D='{match.get('Date')}' T='{match.get('Time')}'")
                return datetime.max 
        
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
    
