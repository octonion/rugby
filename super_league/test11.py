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
from bs4 import BeautifulSoup, NavigableString # Import NavigableString

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium_v8.csv"
TARGET_SEASON = "2025"

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
        except:
            print(f"Overlay button not found or error with selector {i+1}: {selector}")
    print("No common overlay buttons handled.")
    return False

def parse_period_scores(match_element):
    """
    Attempts to parse period scores (e.g., half-time).
    YOU MUST INSPECT THE RENDERED HTML AND ADJUST SELECTORS.
    Livesport often shows them in parentheses like (10-6), or with specific labels/classes.
    """
    hthg, htag = "", ""
    
    # Strategy 1: Look for scores in parentheses within specific score detail elements
    # Example: <span class="event__part">(10 - 6)</span>
    #          <span class="event__part event__part--2">(12 - 8)</span>
    #          <span class="event__part event__part--HT">(10 - 6)</span>
    
    # YOUR_PERIOD_SCORE_CONTAINER_SELECTOR: Selector for elements containing period scores
    # e.g., "span[class*='event__part']", "div.matchSummaryScore__period"
    period_score_elements = match_element.select("span[class*='event__part'], div[class*='subscore']") # YOUR_SELECTOR_HERE

    for score_node in period_score_elements:
        text = score_node.text.strip()
        # Look for scores in parentheses like (XX-YY)
        # This regex is for two numbers separated by a hyphen, enclosed in parentheses.
        period_match = re.search(r'\((\d+)\s*-\s*(\d+)\)', text)
        if period_match:
            # Check if this is specifically the HT score by looking for "HT", "1st Half", or if it's the first one.
            # This part needs to be robust based on how Livesport marks HT scores.
            # For simplicity, if we find one, we'll assume it's HT for now if no other indicator.
            # A more robust way is to check a sibling/parent for text like "1st Half" or "HT"
            # Or if a specific class like 'event__part--HT' exists on score_node
            if "HT" in text.upper() or "1ST HALF" in text.upper() or \
               (not hthg and period_score_elements.index(score_node) == 0): # Simple: take first parenthesized score as HT
                hthg = period_match.group(1)
                htag = period_match.group(2)
                print(f"    Found HT scores: ({hthg}-{htag}) from '{text}'")
                break # Found HT scores

    if not hthg and not htag: # If still not found, try another common pattern if any
        # Sometimes scores are just listed without explicit HT, e.g. for different periods
        # This part would require more specific selectors if the (XX-YY) pattern isn't used for HT
        pass

    return hthg, htag


def find_preceding_header_text(current_element, header_selector_css):
    """
    Traverses previous siblings of current_element until it finds one matching header_selector_css.
    Returns the text of that header or None.
    """
    prev_sibling = current_element.find_previous_sibling()
    while prev_sibling:
        if isinstance(prev_sibling, NavigableString): # Skip over NavigableString objects
            prev_sibling = prev_sibling.find_previous_sibling()
            continue
        # Check if this sibling matches the header_selector_css
        # The .matches() method is for BeautifulSoup Tag objects.
        if prev_sibling.matches(header_selector_css):
            # Extract text appropriately (might be direct or in a child span)
            text_node = prev_sibling.select_one(".event__title--name, .event__title--date") or prev_sibling
            return text_node.text.strip()
        prev_sibling = prev_sibling.find_previous_sibling()
    return None


def scrape_page_with_selenium(driver, url, is_results_page):
    print(f"\nAttempting to fetch {url} with Selenium...")
    matches_data = []
    html_content = ""
    
    try:
        driver.get(url)
        print(f"Page {url} loaded initially.")
        time.sleep(1)
        handle_overlays(driver)

        wait_timeout = 25
        wait_for_match_presence_selector = "div[class*='event__match']" # General selector
        
        print(f"Waiting up to {wait_timeout} seconds for elements matching '{wait_for_match_presence_selector}'...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, wait_for_match_presence_selector))
        )
        print("Match elements likely loaded.")
        html_content = driver.page_source
        
    except TimeoutException:
        print(f"TIMEOUT waiting for '{wait_for_match_presence_selector}' on {url}.")
        html_content = driver.page_source
    except Exception as e_initial:
        print(f"Error during initial load/wait for {url}: {e_initial}")
        traceback.print_exc()
        html_content = driver.page_source 

    if html_content:
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        debug_html_filename = f"{filename_base}_debug_rendered_output_v8.html"
        try:
            with open(debug_html_filename, 'w', encoding='utf-8') as f: f.write(html_content)
            print(f"Saved HTML for {url} to {debug_html_filename}.")
        except Exception as e_save: print(f"Error saving debug HTML: {e_save}")
    else:
        print(f"No HTML content for {url}. Cannot parse.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Global Match Row Selection ---
    # IMPORTANT: For RESULTS, verify/adjust this selector from your _debug_rendered_output_v8.html
    match_row_selector = "div[class*='event__match']" # General selector that worked for fixtures
    # If results use a different top-level class for matches, e.g., 'result__match', you might need:
    # if is_results_page:
    #     match_row_selector = "div[class*='result__match'], div[class*='event__match--finished']" # YOUR_SELECTOR_HERE
    
    all_match_elements = soup.select(match_row_selector)
    print(f"Found {len(all_match_elements)} potential match row elements using selector '{match_row_selector}'.")

    # --- Define selectors for Date and Round Headers ---
    # YOU MUST VERIFY THESE FROM YOUR RENDERED HTML
    date_header_css_selector = "div[class*='event__header--Date'], div.event__header[class*='--Date']" # YOUR_SELECTOR_HERE
    round_header_css_selector = "div[class*='event__round']" # YOUR_SELECTOR_HERE

    for idx, match_element in enumerate(all_match_elements):
        # Attempt to find preceding Date and Round headers for *each* match
        # This can be inefficient if headers are far apart, but more robust than a single pass if structure is messy
        current_date = find_preceding_header_text(match_element, date_header_css_selector) or "Date N/A"
        current_round = find_preceding_header_text(match_element, round_header_css_selector) or "Round N/A"
        
        # Clean up round text if needed
        if " results" in current_round.lower() or " fixtures" in current_round.lower():
             current_round = ' '.join(current_round.split(" ")[:2]) # e.g., "Round 15"

        match_details = {
            "Season": TARGET_SEASON, "Round": current_round, "Date": current_date,
            "Time": "N/A", "Home": "N/A", "Away": "N/A",
            "HG": "", "AG": "", "HTHG": "", "HTAG": "", "Venue": "N/A"
        }
        try:
            time_div = match_element.select_one("div[class*='event__time']")
            if time_div: match_details["Time"] = time_div.text.strip()
            
            home_team_div = match_element.select_one("div[class*='event__participant--home']")
            if home_team_div: match_details["Home"] = home_team_div.text.strip()
            
            away_team_div = match_element.select_one("div[class*='event__participant--away']")
            if away_team_div: match_details["Away"] = away_team_div.text.strip()

            if is_results_page or match_details["Time"] in ["FT", "Finished", "AET"]: # Check if it's a completed match
                # Final Scores
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
                
                # Period Scores (e.g., Half-Time)
                match_details["HTHG"], match_details["HTAG"] = parse_period_scores(match_element)
            
            if match_details["Home"] != "N/A" and match_details["Home"] != "": # Ensure home team is found
                matches_data.append(match_details)
        
        except Exception as e_row_proc:
            print(f"Error processing match row {idx}: {e_row_proc}. Row: {str(match_element)[:150]}")
            continue
    
    print(f"Processed {len(matches_data)} matches from {url}")
    return matches_data

def normalize_and_format_date(date_str, year_to_use_str):
    if not date_str or "N/A" in date_str.strip():
        return "Date N/A"

    cleaned_date_str = date_str.strip()
    
    # Handle relative dates like "Today", "Tomorrow", "Yesterday"
    # This requires datetime and timedelta
    today = datetime.now()
    if "today" in cleaned_date_str.lower():
        return today.strftime('%d.%m.%Y')
    elif "tomorrow" in cleaned_date_str.lower():
        return (today + timedelta(days=1)).strftime('%d.%m.%Y')
    elif "yesterday" in cleaned_date_str.lower():
        return (today - timedelta(days=1)).strftime('%d.%m.%Y')

    # Remove day names like "SAT, ", "Sun " etc.
    cleaned_date_str = re.sub(r"^[A-Za-z]{2,4},?\s+", "", cleaned_date_str).strip()

    # Handle formats like "14.05." (append current year)
    if cleaned_date_str.count('.') == 1 and cleaned_date_str.endswith('.'):
        cleaned_date_str = cleaned_date_str + year_to_use_str
    # Handle "14.05" (append current year)
    elif cleaned_date_str.count('.') == 1 and not cleaned_date_str.endswith('.'):
        parts = cleaned_date_str.split('.')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            cleaned_date_str = f"{parts[0]}.{parts[1]}.{year_to_use_str}"
    # Handle "17 May" (append current year, convert month name)
    elif cleaned_date_str.count('.') == 0 and len(cleaned_date_str.split()) == 2:
        try:
            # Try to parse "Day Month" format e.g. "17 May"
            dt_obj = datetime.strptime(f"{cleaned_date_str} {year_to_use_str}", "%d %b %Y") # %b for short month name
            return dt_obj.strftime('%d.%m.%Y')
        except ValueError:
            try:
                dt_obj = datetime.strptime(f"{cleaned_date_str} {year_to_use_str}", "%d %B %Y") # %B for full month name
                return dt_obj.strftime('%d.%m.%Y')
            except ValueError:
                pass # Fall through if month name parsing fails

    # At this point, expect "dd.mm.yyyy" or try to parse it
    try:
        dt_obj = datetime.strptime(cleaned_date_str, '%d.%m.%Y')
        return dt_obj.strftime('%d.%m.%Y')
    except ValueError:
        print(f"    Could not normalize date string: '{date_str}' (cleaned: '{cleaned_date_str}') to dd.mm.yyyy")
        return date_str # Return original or a placeholder if critical formatting failed


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
            # Normalize date here before sorting and writing
            # The date extracted might be like "SAT, 17.05." or "17.05." or "Tomorrow"
            # The normalize_and_format_date function will attempt to convert this to dd.mm.yyyy
            match_raw["Date"] = normalize_and_format_date(match_raw["Date"], TARGET_SEASON)
            all_matches_processed.append(match_raw)


        def sort_key_matches(match):
            try:
                # Date should now be closer to dd.mm.yyyy or the original string if parsing failed
                date_val = match.get('Date', '')
                time_val = match.get('Time', '00:00')

                if "N/A" in date_val or not date_val or "N/A" in time_val or not time_val:
                    return datetime.max 
                
                # Final attempt to parse for sorting
                return datetime.strptime(f"{date_val} {time_val}", '%d.%m.%Y %H:%M')
            except ValueError: # If date_val is still not dd.mm.yyyy
                # print(f"SortKey Warning: D='{match.get('Date')}' T='{match.get('Time')}'")
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
    main()

