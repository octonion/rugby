import csv
import time
from datetime import datetime
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
from bs4 import BeautifulSoup

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium_v5.csv"

TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

# --- WebDriver Path (Configure if not in system PATH) ---
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'
# GECKODRIVER_PATH = '/path/to/your/geckodriver'

def setup_driver():
    options = webdriver.ChromeOptions()
    # To see what the browser is doing, temporarily comment out the next line:
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=options) # Assumes driver is in PATH
    return driver

def handle_overlays(driver):
    cookie_accept_selectors = [
        "button#onetrust-accept-btn-handler", 
        "button[data-testid='dialog-button-primary']",
        "//button[contains(normalize-space(), 'Accept All') or contains(normalize-space(), 'Allow all')]", # More robust text check
        "//button[contains(normalize-space(), 'I Accept') or contains(normalize-space(), 'Accept')]",
        "//button[contains(normalize-space(), 'Agree')]"
    ]
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
        except TimeoutException:
            print(f"Overlay button not found/clickable with selector {i+1}: {selector}")
        except Exception as e_overlay:
            print(f"Error clicking overlay with selector {i+1} ('{selector}'): {e_overlay}")
    print("No common overlay buttons handled.")
    return False

def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"\nAttempting to fetch {url} with Selenium...")
    processed_matches_data = []
    html_saved_for_debug = False
    html_content = ""
    
    try:
        driver.get(url)
        print(f"Page {url} loaded initially.")
        handle_overlays(driver)

        wait_timeout = 20
        # --- REVERTED WAIT CONDITION: Wait for actual match elements to be present ---
        # This selector worked for fixtures before.
        # For results, if this still fails, the class names for result matches are different.
        match_elements_exist_selector = "div[class*='event__match']" # General selector for any match type
        
        print(f"Waiting up to {wait_timeout} seconds for match elements ('{match_elements_exist_selector}') to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, match_elements_exist_selector))
        )
        print("Match elements likely loaded.")
        html_content = driver.page_source
        
    except TimeoutException:
        print(f"TIMEOUT waiting for match elements ('{match_elements_exist_selector}') on {url}.")
        print("Will save current page source for debugging the timeout issue.")
        html_content = driver.page_source # Get current source even on timeout
    except WebDriverException as e_wd:
        print(f"WebDriverException during page load or initial wait for {url}: {e_wd}")
        traceback.print_exc()
        html_content = driver.page_source # Try to get source if possible
        # return [] # Exit early if WebDriver fails critically
    except Exception as e_initial:
        print(f"Unexpected error during initial page load/wait for {url}: {e_initial}")
        traceback.print_exc()
        html_content = driver.page_source # Try to get source
        # return []

    finally: # Ensure HTML is saved for inspection
        if html_content or not html_saved_for_debug:
            path_components = [comp for comp in url.split('/') if comp]
            filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
            debug_html_filename = f"{filename_base}_debug_rendered_output_v5.html"
            try:
                with open(debug_html_filename, 'w', encoding='utf-8') as f:
                    f.write(html_content if html_content else driver.page_source)
                print(f"Saved current HTML for {url} to {debug_html_filename} for your inspection.")
                html_saved_for_debug = True
            except Exception as e_save:
                print(f"Error saving debug HTML: {e_save}")
    
    if not html_content:
        print(f"No HTML content retrieved for {url}. Aborting parsing.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Attempt to find the main event area for structured parsing ---
    # IMPORTANT: You MUST verify this selector from your _debug_rendered_output_v5.html files
    main_event_container_selector = "div.sportNameRUGBYLEAGUE" # Primary guess for Livesport
    event_area = soup.select_one(main_event_container_selector)
    
    if not event_area:
        print(f"WARNING: Main event container ('{main_event_container_selector}') was NOT found. "
              f"Parsing will proceed by looking for matches globally, which might miss date/round context "
              f"or be less accurate. Please inspect '{debug_html_filename}' to find the correct container.")
        event_area = soup # Fallback to parsing the whole soup if specific container not found

    # --- Structural Parsing Logic ---
    # IMPORTANT: These selectors need YOUR verification from the rendered HTML.
    # This selector attempts to get all headers and matches within the event_area.
    elements_in_sequence_selector = "div[class*='event__header'], div[class*='event__round'], div[class*='event__match']"
    elements_in_sequence = event_area.select(elements_in_sequence_selector)
    print(f"Found {len(elements_in_sequence)} potential elements (headers/matches) using selector '{elements_in_sequence_selector}' (within determined event_area).")

    current_date_from_page = "Date N/A"
    current_round_from_page = "Round N/A"

    for element_idx, element in enumerate(elements_in_sequence):
        # Check if element is a Date Header
        date_header_selector = "div[class*='event__header--Date'], div.event__header[class*='--Date']"
        if element.matches(date_header_selector):
             date_text_node = element.select_one(".event__title--name, .event__title--date") or element
             current_date_from_page = date_text_node.text.strip()
             print(f"  [Elem {element_idx}] Date Header: {current_date_from_page}")
             continue

        # Check if element is a Round Header
        round_header_selector = "div[class*='event__round']"
        if element.matches(round_header_selector):
            current_round_from_page = element.text.strip()
            print(f"  [Elem {element_idx}] Round Header: {current_round_from_page}")
            continue

        # Check if element is a Match Row
        # IMPORTANT: Verify these participant selectors especially for the RESULTS page.
        home_team_node_for_check = element.select_one("div[class*='event__participant--home']")
        away_team_node_for_check = element.select_one("div[class*='event__participant--away']")

        if home_team_node_for_check and away_team_node_for_check:
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
                
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    processed_matches_data.append(match_details)
            
            except Exception as e_row_proc:
                print(f"Error processing match row [Elem {element_idx}]: {e_row_proc}. Row: {str(element)[:150]}")
                continue
    
    print(f"Processed {len(processed_matches_data)} matches from {url}")
    return processed_matches_data

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
            try:
                date_str = match.get('Date', '') 
                time_str = match.get('Time', '00:00')
                if "N/A" in date_str or not date_str or "N/A" in time_str or not time_str: # Added check for empty time_str
                    return datetime.max 
                
                # Basic date normalization (needs improvement for "Today", "Tomorrow", full month names etc.)
                if date_str.count('.') == 1 and date_str.endswith('.'): # "14.05."
                    date_str = date_str + str(datetime.now().year)
                elif date_str.count('.') == 1: # "14.05"
                    parts = date_str.split('.')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                         date_str = f"{parts[0]}.{parts[1]}.{datetime.now().year}"
                # Add more robust date parsing here if `current_date_from_page` is like "SATURDAY, 17 MAY"
                
                return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
            except Exception:
                return datetime.max 
        
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
