import csv
import time
from datetime import datetime
import traceback
import re # For parsing scores like (HT 10-6)

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
OUTPUT_CSV_FILE = "super_league_data_selenium_v7.csv"
TARGET_SEASON = "2025" # Assuming based on super-league-2025.csv example

# Updated Headers
TARGET_CSV_HEADERS = ["Season", "Round", "Date", "Time", "Home", "Away", "HG", "AG", "HTHG", "HTAG", "Venue"]

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
    ]
    for i, selector in enumerate(cookie_accept_selectors):
        try:
            print(f"Looking for overlay button with selector: {selector}")
            button = WebDriverWait(driver, 3).until( # Shorter wait for overlays
                EC.element_to_be_clickable((By.XPATH if selector.startswith("//") else By.CSS_SELECTOR, selector))
            )
            button.click()
            print(f"Clicked overlay/cookie button with selector: {selector}")
            time.sleep(1) 
            return True 
        except:
            print(f"Overlay button not found/clickable or error with selector {i+1}: {selector}")
    print("No common overlay buttons handled.")
    return False

def parse_halftime_scores(element):
    """
    Attempts to parse half-time scores.
    Livesport often shows them as (XX - YY) within a score details element.
    YOU MUST INSPECT THE HTML AND ADJUST SELECTORS.
    """
    hthg, htag = "", ""
    # Example selector: look for a div/span containing parentheses and a hyphen
    # This is a VERY common pattern but classes will vary.
    # Try to find a specific element for period scores if possible.
    period_score_selector = "div[class*='event__part'], span[class*='event__part'], div[class*='subscore']" # YOUR_SELECTOR_HERE
    
    # Often, HT score is the first period score, or specifically marked.
    # Look for text like "1st Half" or "HT" if present.
    # For this example, we'll look for a score in parentheses.
    score_detail_elements = element.select(period_score_selector) # Find all potential period containers
    
    # Common pattern: HT scores are often in parentheses like (10-6)
    # We can also look for specific elements if they exist.
    # Example: first element containing '(' and '-' might be HT.
    for detail_element in score_detail_elements:
        text_content = detail_element.text.strip()
        match = re.search(r'\((\d+)\s*-\s*(\d+)\)', text_content) # Looks for (XX-YY)
        if match:
            hthg = match.group(1)
            htag = match.group(2)
            print(f"    Found HT scores: {hthg}-{htag} from text: {text_content}")
            break # Assume first one found is what we want for HT
        # Add more specific logic if HT scores are marked differently, e.g., by a preceding "1st Half" label.

    # If not found by parentheses, you might need another selector:
    # if not hthg:
    #    ht_home_specific_selector = "YOUR_HT_HOME_SCORE_SELECTOR"
    #    ht_away_specific_selector = "YOUR_HT_AWAY_SCORE_SELECTOR"
    #    ht_home_node = element.select_one(ht_home_specific_selector)
    #    ht_away_node = element.select_one(ht_away_specific_selector)
    #    if ht_home_node and ht_away_node:
    #        hthg = ht_home_node.text.strip()
    #        htag = ht_away_node.text.strip()

    return hthg, htag


def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"\nAttempting to fetch {url} with Selenium...")
    processed_matches_data = []
    html_content = ""
    
    try:
        driver.get(url)
        print(f"Page {url} loaded initially.")
        time.sleep(1) # Small pause after initial load
        handle_overlays(driver)

        wait_timeout = 25 # Increased slightly
        wait_for_match_presence_selector = "div[class*='event__match']"
        
        print(f"Waiting up to {wait_timeout} seconds for elements matching '{wait_for_match_presence_selector}' to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, wait_for_match_presence_selector))
        )
        print("Match elements likely loaded.")
        html_content = driver.page_source
        
    except TimeoutException:
        print(f"TIMEOUT waiting for elements matching '{wait_for_match_presence_selector}' on {url}.")
        html_content = driver.page_source
    except Exception as e_initial:
        print(f"Error during initial load/wait for {url}: {e_initial}")
        traceback.print_exc()
        html_content = driver.page_source 

    if html_content:
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        debug_html_filename = f"{filename_base}_debug_rendered_output_v7.html"
        try:
            with open(debug_html_filename, 'w', encoding='utf-8') as f: f.write(html_content)
            print(f"Saved HTML for {url} to {debug_html_filename}.")
        except Exception as e_save: print(f"Error saving debug HTML: {e_save}")
    else:
        print(f"No HTML content for {url}. Cannot parse.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Main Event Area ---
    # IMPORTANT: Verify this selector. For rugby league, it's usually 'div.sportNameRUGBYLEAGUE'
    main_event_container_selector = "div.sportNameRUGBYLEAGUE" # YOUR_SELECTOR_HERE
    event_area = soup.select_one(main_event_container_selector)
    
    if not event_area:
        print(f"WARNING: Main event container ('{main_event_container_selector}') NOT found. Parsing from whole page.")
        event_area = soup # Fallback

    # --- Iterate through elements to find headers and matches ---
    # IMPORTANT: This selector must grab all date headers, round headers, and match containers in order.
    # Test this selector carefully on your saved HTML.
    elements_in_sequence_selector = "div[class*='event__header'], div[class*='event__round'], div[class*='event__match']" # YOUR_SELECTOR_HERE
    elements_in_sequence = event_area.select(elements_in_sequence_selector)
    print(f"Found {len(elements_in_sequence)} potential elements (headers/matches) using '{elements_in_sequence_selector}'.")

    current_date_from_page = "Date N/A"
    current_round_from_page = "Round N/A"

    for element_idx, element in enumerate(elements_in_sequence):
        # Check for Date Header
        # IMPORTANT: Verify selector for date headers. Text might be in child spans.
        date_header_selector = "div[class*='event__header--Date'], div.event__header[class*='--Date']" # YOUR_SELECTOR_HERE
        if element.matches(date_header_selector):
             date_text_node = element.select_one(".event__title--name, .event__title--date") or element
             current_date_from_page = date_text_node.text.strip()
             print(f"  [Elem {element_idx}] Date Header: {current_date_from_page}")
             continue

        # Check for Round Header
        # IMPORTANT: Verify selector for round headers.
        round_header_selector = "div[class*='event__round']" # YOUR_SELECTOR_HERE
        if element.matches(round_header_selector):
            current_round_from_page = element.text.strip()
            # Clean up "Round X" if it's like "Round 15 results"
            if " results" in current_round_from_page.lower() or " fixtures" in current_round_from_page.lower():
                current_round_from_page = current_round_from_page.split(" ")[0] + " " + current_round_from_page.split(" ")[1] # e.g. "Round 15"
            print(f"  [Elem {element_idx}] Round Header: {current_round_from_page}")
            continue

        # Check if it's a Match Row
        # IMPORTANT: Verify these participant selectors for BOTH fixtures and results pages.
        home_team_node = element.select_one("div[class*='event__participant--home']")
        away_team_node = element.select_one("div[class*='event__participant--away']")

        if home_team_node and away_team_node:
            match_details = {
                "Season": TARGET_SEASON, # Add season
                "Round": current_round_from_page, "Date": current_date_from_page, # Use captured date/round
                "Time": "N/A", "Home": "N/A", "Away": "N/A",
                "HG": "", "AG": "", "HTHG": "", "HTAG": "", "Venue": "N/A"
            }
            try:
                time_div = element.select_one("div[class*='event__time']")
                if time_div: match_details["Time"] = time_div.text.strip()
                
                match_details["Home"] = home_team_node.text.strip()
                match_details["Away"] = away_team_node.text.strip()

                if is_results_page:
                    # Final Scores
                    home_score_div = element.select_one("div[class*='event__score--home'], span[class*='event__score--home']")
                    if home_score_div:
                        score_text = home_score_div.text.strip()
                        if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                            match_details["HG"] = score_text
                    
                    away_score_div = element.select_one("div[class*='event__score--away'], span[class*='event__score--away']")
                    if away_score_div:
                        score_text = away_score_div.text.strip()
                        if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                            match_details["AG"] = score_text
                    
                    # Half-Time Scores (or other period scores)
                    # This requires specific selectors from inspecting completed matches in _debug_rendered_output_v7.html
                    match_details["HTHG"], match_details["HTAG"] = parse_halftime_scores(element)
                
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    processed_matches_data.append(match_details)
            
            except Exception as e_row_proc:
                print(f"Error processing match row [Elem {element_idx}]: {e_row_proc}.")
                continue
    
    print(f"Processed {len(processed_matches_data)} matches from {url}")
    return processed_matches_data

def normalize_and_format_date(date_str, time_str, year_to_use_str):
    """
    Attempts to parse various date formats from Livesport and returns dd.mm.yyyy.
    This needs to be quite robust.
    """
    if not date_str or "N/A" in date_str:
        return "Date N/A"

    # Handle "Today", "Tomorrow", "Yesterday"
    # Note: This depends on the script's current date.
    today = datetime.now()
    if "today" in date_str.lower():
        dt_obj = today
    elif "tomorrow" in date_str.lower():
        dt_obj = today + timedelta(days=1)
    elif "yesterday" in date_str.lower():
        dt_obj = today - timedelta(days=1)
    else:
        # Try parsing formats like "14.05." or "14.05.2024" or "SAT, 14.05."
        # Remove day names like "SAT, " if present
        date_str_cleaned = re.sub(r"^[A-Za-z]{2,3},?\s*", "", date_str).strip()

        if date_str_cleaned.count('.') == 1 and date_str_cleaned.endswith('.'): # "14.05."
            date_str_cleaned = date_str_cleaned + year_to_use_str
        elif date_str_cleaned.count('.') == 1: # "14.05" (no trailing dot)
             parts = date_str_cleaned.split('.')
             if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                 date_str_cleaned = f"{parts[0]}.{parts[1]}.{year_to_use_str}"
        # If year is already present, e.g., "14.05.2024"
        # No change needed if date_str_cleaned is already "dd.mm.yyyy"
        
        try:
            # Try common formats
            if date_str_cleaned.count('.') == 2:
                 dt_obj = datetime.strptime(date_str_cleaned, '%d.%m.%Y')
            else: # If parsing fails, fallback or log error
                print(f"    Could not parse date string: {date_str} (cleaned: {date_str_cleaned})")
                return date_str # Return original if unparseable for now
        except ValueError:
            print(f"    ValueError parsing date string: {date_str} (cleaned: {date_str_cleaned})")
            return date_str # Return original

    return dt_obj.strftime('%d.%m.%Y')


def main():
    driver = None
    try:
        driver = setup_driver()
        print("WebDriver initialized.")

        results_data_raw = scrape_page_with_selenium(driver, RESULTS_URL, is_results_page=True)
        fixtures_data_raw = scrape_page_with_selenium(driver, FIXTURES_URL, is_results_page=False)
        
        all_matches_raw = results_data_raw + fixtures_data_raw
        
        if not all_matches_raw:
            print("\nNo matches found. CSV will be empty or not created.")
            return

        all_matches_processed = []
        for match in all_matches_raw:
            # Normalize date here before sorting and writing
            match["Date"] = normalize_and_format_date(match["Date"], match["Time"], TARGET_SEASON)
            all_matches_processed.append(match)

        def sort_key_matches(match):
            try:
                # Now Date should be in dd.mm.yyyy format from normalize_and_format_date
                # If it failed, it might still be original string or "Date N/A"
                if "N/A" in match.get('Date', '') or not match.get('Date', '') or \
                   "N/A" in match.get('Time', '') or not match.get('Time', ''):
                    return datetime.max 
                return datetime.strptime(f"{match['Date']} {match['Time']}", '%d.%m.%Y %H:%M')
            except ValueError: # Catch if date is still not in expected format
                return datetime.max 
        
        all_matches_processed.sort(key=sort_key_matches)
        print(f"\nTotal matches processed and sorted: {len(all_matches_processed)}")

        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_matches_processed)
        print(f"Data written to {OUTPUT_CSV_FILE}")

    finally:
        if driver:
            print("\nQuitting WebDriver.")
            driver.quit()

if __name__ == '__main__':
    # Import timedelta if using it in normalize_and_format_date
    from datetime import timedelta 
    main()
