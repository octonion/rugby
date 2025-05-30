import csv
import time
from datetime import datetime, timedelta # Added timedelta
import traceback
import re # For parsing scores

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup, Tag, NavigableString # Import Tag and NavigableString

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium_v9.csv"
TARGET_SEASON = "2025" # As per super-league-2025.csv example

TARGET_CSV_HEADERS = ["Season", "Round", "Date", "Time", "Home", "Away", "HG", "AG", "HTHG", "HTAG", "Venue"]

# --- WebDriver Path ---
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run headless
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
            button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH if selector.startswith("//") else By.CSS_SELECTOR, selector))
            )
            button.click()
            print(f"Clicked overlay/cookie button with selector: {selector}")
            time.sleep(1)
            return True
        except: # Broad except for this non-critical part
            # print(f"Overlay button not found or error with selector {i+1}: {selector}")
            pass # Continue trying other selectors
    print("No common overlay buttons handled or necessary.")
    return False

def parse_period_scores_from_text(text_containing_scores):
    """Helper to find (score-score) pattern for periods."""
    hthg, htag = "", ""
    # Regex to find scores like (10-6) or (10 - 6)
    period_match = re.search(r'\((\d+)\s*-\s*(\d+)\)', text_containing_scores)
    if period_match:
        hthg = period_match.group(1)
        htag = period_match.group(2)
    return hthg, htag

def extract_period_scores(match_element):
    """
    Extracts Half-Time scores.
    YOU MUST INSPECT RENDERED HTML from a COMPLETED MATCH in results_debug_rendered_output_v8.html
    to determine the correct selectors or logic.
    """
    hthg, htag = "", ""

    # Strategy 1: Look for a specific element marked for Half-Time (e.g., with "HT" or "1st Half" text or class)
    # This is the most reliable if such an element exists.
    # Example: <div class="event__part event__part--HT">(10 - 6)</div>
    #          <div class="scores__period">1st Half: 10-6</div>
    ht_specific_selector = "span[class*='event__part--HT'], div[class*='event__part--HT']" # YOUR_SELECTOR_HERE
    ht_element = match_element.select_one(ht_specific_selector)
    if ht_element:
        hthg, htag = parse_period_scores_from_text(ht_element.text)
        if hthg: print(f"    Found HT scores via specific HT selector: ({hthg}-{htag})"); return hthg, htag

    # Strategy 2: Look for all period scores and take the first one as HT, or one explicitly containing "1st half"
    # Example: <span class="event__part">(10 - 6)</span> <span class="event__part">(12 - 8)</span>
    #          <div class="someContainer"><span class="label">1st Half</span> <span class="score">10-6</span></div>
    
    # General selector for any element that might contain period scores
    # This needs to be identified from your HTML for completed matches.
    all_period_score_containers_selector = "span[class*='event__part'], div[class*='event__part'], div[class*='subscore__item']" # YOUR_SELECTOR_HERE
    period_elements = match_element.select(all_period_score_containers_selector)

    for period_el in period_elements:
        period_text = period_el.text.strip()
        # Check if this element's text explicitly indicates it's the first half or HT
        if "1st half" in period_text.lower() or "half-time" in period_text.lower() or "ht" == period_text.lower().strip("() "): # Check common HT indicators
            hthg_temp, htag_temp = parse_period_scores_from_text(period_text)
            if hthg_temp: # Ensure scores were actually parsed from this element
                hthg, htag = hthg_temp, htag_temp
                print(f"    Found HT scores via text indicator: ({hthg}-{htag}) from '{period_text}'")
                break # Found it

    # Strategy 3: If still no HT score, and we have period elements, take the first parenthesized score
    if not hthg and period_elements:
        for period_el in period_elements: # Iterate again if specific text indicator wasn't found
            hthg_temp, htag_temp = parse_period_scores_from_text(period_el.text)
            if hthg_temp: # Take the first valid parenthesized score as a guess for HT
                hthg, htag = hthg_temp, htag_temp
                print(f"    Found potential HT scores (first parenthesized): ({hthg}-{htag}) from '{period_el.text.strip()}'")
                break
    
    if not hthg:
        # print(f"    HT scores not found with current selectors for match.")
        pass

    return hthg, htag


def find_closest_preceding_header(current_element, header_css_selector):
    """
    Finds the text of the closest preceding sibling that matches the header_css_selector.
    Skips NavigableString objects.
    """
    prev_sibling = current_element.find_previous_sibling()
    header_text = None
    while prev_sibling:
        if isinstance(prev_sibling, Tag): # Ensure it's a Tag object
            if prev_sibling.select_one(header_css_selector): # Check if the sibling itself IS the header
                # Extract text: Livesport often has text in child spans or directly
                text_node = prev_sibling.select_one(".event__title--name, .event__title--date") or \
                            prev_sibling.select_one("span") or \
                            prev_sibling # Try common children or the element itself
                if text_node:
                    header_text = text_node.text.strip()
                    break # Found the header
        prev_sibling = prev_sibling.find_previous_sibling()
    return header_text


def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"\nAttempting to fetch {url} with Selenium...")
    matches_data = []
    html_content = ""
    
    try:
        driver.get(url)
        print(f"Page {url} loaded initially.")
        time.sleep(1) # Allow a moment for any immediate scripts
        handle_overlays(driver)

        wait_timeout = 25
        # Wait for any generic match element. This was successful for fixtures previously.
        wait_for_match_presence_selector = "div[class*='event__match']"
        
        print(f"Waiting up to {wait_timeout} seconds for elements matching '{wait_for_match_presence_selector}'...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, wait_for_match_presence_selector))
        )
        print("Match elements likely loaded.")
        html_content = driver.page_source
        
    except TimeoutException:
        print(f"TIMEOUT waiting for '{wait_for_match_presence_selector}' on {url}.")
        html_content = driver.page_source # Get source anyway for debugging
    except Exception as e_initial:
        print(f"Error during initial load/wait for {url}: {e_initial}")
        traceback.print_exc()
        html_content = driver.page_source 

    if html_content:
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        debug_html_filename = f"{filename_base}_debug_rendered_output_v9.html"
        try:
            with open(debug_html_filename, 'w', encoding='utf-8') as f: f.write(html_content)
            print(f"Saved HTML for {url} to {debug_html_filename}.")
        except Exception as e_save: print(f"Error saving debug HTML: {e_save}")
    else:
        print(f"No HTML content for {url}. Cannot parse.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Global Match Row Selection ---
    # IMPORTANT: For the RESULTS page, you MUST inspect your debug_rendered_output_v9.html
    # to confirm or find the correct class names if this selector doesn't work.
    # The script `test5.py` likely used something similar to `div[class*='event__match']` successfully for fixtures.
    
    # General selector for any match type (scheduled, live, finished)
    match_row_selector = "div[class*='event__match']" 
    # If results page has very different top-level class for match items, handle here:
    # if is_results_page:
    #     match_row_selector = "YOUR_RESULTS_PAGE_MATCH_ROW_SELECTOR" # e.g., "div.resultItem"
    
    all_match_elements = soup.select(match_row_selector)
    print(f"Found {len(all_match_elements)} potential match row elements using selector '{match_row_selector}'.")

    # --- Define CSS selectors for Date and Round Headers ---
    # YOU MUST VERIFY/UPDATE THESE FROM YOUR RENDERED HTML
    # These selectors are used by find_closest_preceding_header
    date_header_css = "div[class*='event__header--Date'], div.event__header[class*='--Date']" # YOUR_SELECTOR_HERE
    round_header_css = "div[class*='event__round']" # YOUR_SELECTOR_HERE

    for idx, match_element in enumerate(all_match_elements):
        # Get Date and Round by looking at preceding siblings
        current_date = find_closest_preceding_header(match_element, date_header_css) or "Date N/A"
        current_round = find_closest_preceding_header(match_element, round_header_css) or "Round N/A"
        
        if " results" in current_round.lower() or " fixtures" in current_round.lower():
             current_round = ' '.join(current_round.split(" ")[:2]) # e.g., "Round 15"

        match_details = {
            "Season": TARGET_SEASON, "Round": current_round, "Date": current_date,
            "Time": "N/A", "Home": "N/A", "Away": "N/A",
            "HG": "", "AG": "", "HTHG": "", "HTAG": "", "Venue": "N/A" # Venue typically not on list pages
        }
        try:
            time_div = match_element.select_one("div[class*='event__time']")
            if time_div: match_details["Time"] = time_div.text.strip()
            
            home_team_div = match_element.select_one("div[class*='event__participant--home']")
            if home_team_div: match_details["Home"] = home_team_div.text.strip()
            
            away_team_div = match_element.select_one("div[class*='event__participant--away']")
            if away_team_div: match_details["Away"] = away_team_div.text.strip()

            # Check for final scores (typically for results page, or if time is FT for fixtures)
            is_completed_match = is_results_page or match_details["Time"] in ["FT", "Finished", "AET", "Ended"]
            if is_completed_match:
                home_score_div = match_element.select_one("div[class*='event__score--home'], span[class*='event__score--home']")
                if home_score_div:
                    score_text = home_score_div.text.strip()
                    if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                        match_details["HG"] = score_text
                
                away_score_div = match_element.select_one("div[class*='event__score--away'], span[class*='event__score--away']")
                if away_score_div:
                    score_text = away_score_div.text.strip()
                    if score_text.isdigit() or (score_text.startswith('-') and score_text[1:].isdigit()):
                        match_details["AG"] = score_text
                
                # Extract Period Scores (e.g., Half-Time)
                match_details["HTHG"], match_details["HTAG"] = extract_period_scores(match_element)
            
            if match_details["Home"] and match_details["Home"] != "N/A": # Check if at least home team is found
                matches_data.append(match_details)
        
        except Exception as e_row_proc:
            print(f"Error processing match row {idx} ({match_details.get('Home')} vs {match_details.get('Away')}): {e_row_proc}")
            # traceback.print_exc() # Uncomment for full traceback for row errors
            continue # Skip to next match if this one has an error
    
    print(f"Successfully processed {len(matches_data)} matches from {url}")
    return matches_data

def normalize_and_format_date(date_str, year_to_use_str):
    if not date_str or "N/A" in date_str or not isinstance(date_str, str):
        return "Date N/A"

    cleaned_date_str = date_str.strip()
    dt_obj = None

    if "today" in cleaned_date_str.lower():
        dt_obj = datetime.now()
    elif "tomorrow" in cleaned_date_str.lower():
        dt_obj = datetime.now() + timedelta(days=1)
    elif "yesterday" in cleaned_date_str.lower():
        dt_obj = datetime.now() - timedelta(days=1)
    else:
        # Remove day names like "SAT, ", "Sun " etc.
        # And any extra text like "results", "fixtures"
        cleaned_date_str = re.sub(r"^[A-Za-z]{2,10},?\s+", "", cleaned_date_str).strip()
        cleaned_date_str = re.sub(r"\s+(?:results|fixtures)", "", cleaned_date_str, flags=re.IGNORECASE).strip()


        # Try "14.05." or "14.05" (append target year)
        if cleaned_date_str.count('.') == 1:
            if cleaned_date_str.endswith('.'): # "14.05."
                cleaned_date_str = cleaned_date_str + year_to_use_str
            else: # "14.05"
                parts = cleaned_date_str.split('.')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    cleaned_date_str = f"{parts[0]}.{parts[1]}.{year_to_use_str}"
            try:
                dt_obj = datetime.strptime(cleaned_date_str, '%d.%m.%Y')
            except ValueError:
                pass # Continue to other formats

        # Try "17 May" (append target year, convert month name)
        if not dt_obj and cleaned_date_str.count('.') == 0 and len(cleaned_date_str.split()) == 2:
            try:
                dt_obj = datetime.strptime(f"{cleaned_date_str} {year_to_use_str}", "%d %b %Y")
            except ValueError:
                try:
                    dt_obj = datetime.strptime(f"{cleaned_date_str} {year_to_use_str}", "%d %B %Y")
                except ValueError:
                     pass # Continue to other formats
        
        # Try "dd.mm.yyyy" directly if not already parsed
        if not dt_obj and cleaned_date_str.count('.') == 2:
            try:
                dt_obj = datetime.strptime(cleaned_date_str, '%d.%m.%Y')
            except ValueError:
                pass
    
    if dt_obj:
        return dt_obj.strftime('%d.%m.%Y')
    else:
        print(f"    WARNING: Could not normalize date string: '{date_str}' (cleaned to: '{cleaned_date_str}')")
        return date_str # Return original cleaned string if complex parsing failed, for manual review

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
        for match_raw in all_matches_raw:
            match_raw["Date"] = normalize_and_format_date(match_raw["Date"], TARGET_SEASON)
            all_matches_processed.append(match_raw)

        def sort_key_matches(match):
            try:
                date_val = match.get('Date', '')
                time_val = match.get('Time', '00:00')
                if "N/A" in date_val or not date_val or "N/A" in time_val or not time_val:
                    return datetime(1900, 1, 1) # Sort unparseable dates very early
                return datetime.strptime(f"{date_val} {time_val}", '%d.%m.%Y %H:%M')
            except ValueError:
                # print(f"SortKey Warning: D='{match.get('Date')}' T='{match.get('Time')}'")
                return datetime(1900, 1, 1) # Fallback for unparseable dates during sort
        
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
    main()
