import csv
import time # For potential waits
from datetime import datetime
import traceback # For detailed error traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService # For Chrome
# from selenium.webdriver.firefox.service import Service as FirefoxService # For Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_selenium.csv"

# Target CSV Headers based on super-league-2025.csv
TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

# --- IMPORTANT: Specify the path to your WebDriver executable ---
# If chromedriver/geckodriver is in your PATH, you might not need to specify the path.
# Otherwise, uncomment and set the correct path.
# CHROMEDRIVER_PATH = '/path/to/your/chromedriver'
# GECKODRIVER_PATH = '/path/to/your/geckodriver'

def setup_driver():
    """Sets up and returns a Selenium WebDriver instance."""
    # --- Chrome Example ---
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run Chrome in headless mode (no UI)
    options.add_argument('--disable-gpu') # Recommended for headless
    options.add_argument('--window-size=1920,1080') # Specify window size
    options.add_argument('--log-level=3') # Suppress unnecessary console logs from Chrome
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Uncomment the appropriate service line if you're specifying the path
    # service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(options=options) # Use this if driver is in PATH

    # --- Firefox Example (if you prefer Firefox) ---
    # options = webdriver.FirefoxOptions()
    # options.add_argument('--headless')
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    # service = FirefoxService(executable_path=GECKODRIVER_PATH)
    # driver = webdriver.Firefox(service=service, options=options)
    # driver = webdriver.Firefox(options=options) # Use this if driver is in PATH
    
    return driver

def scrape_page_with_selenium(driver, url, is_results_page):
    """
    Fetches page content using Selenium, then parses with BeautifulSoup.
    """
    print(f"Attempting to fetch {url} with Selenium...")
    matches_data = []
    try:
        driver.get(url)

        # --- Wait for dynamic content to load ---
        # We'll wait for elements that are likely to contain match data.
        # The class name 'event__match' is a common pattern on Livesport.
        # We use a CSS selector that looks for a div whose class attribute *contains* 'event__match'.
        # You might need to adjust the timeout and the selector based on page behavior.
        wait_timeout = 20  # seconds
        print(f"Waiting up to {wait_timeout} seconds for match content to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[class*='event__match']"))
        )
        print("Match content likely loaded.")
        
        # Optional: Give a bit more time for any final JS rendering after elements are present
        # time.sleep(2)

        html_content = driver.page_source

        # --- Save the JS-rendered HTML for inspection (optional, but good for debugging selectors) ---
        path_components = [comp for comp in url.split('/') if comp]
        filename_base = path_components[-1] if len(path_components) > 1 else "unknown_page"
        rendered_html_filename = f"{filename_base}_rendered_output.html"
        with open(rendered_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved JS-rendered HTML for {url} to {rendered_html_filename}")
        # --- End of HTML saving block ---

        soup = BeautifulSoup(html_content, 'html.parser')

        # Placeholder for current_round and current_date_str
        # Logic to find these needs to be implemented by inspecting the rendered HTML structure.
        # Often, these are headers above a group of matches.
        current_round_placeholder = "Round N/A (Selenium)"
        current_date_placeholder = "Date N/A (Selenium)"

        # --- SELECTOR FOR MATCH ROWS ---
        # Now that JS has run, these selectors *should* work if class names are consistent.
        # Adjust this selector based on inspecting the `_rendered_output.html`
        # It looks for divs whose class attribute CONTAINS 'event__match' and also one of the status types.
        match_rows = soup.select("div[class*='event__match--scheduled'], div[class*='event__match--live'], div[class*='event__match--finished']")
        # A slightly broader alternative if the above is too specific:
        # match_rows = soup.select("div[class*='event__match']")
        
        print(f"Found {len(match_rows)} potential match rows using selectors on JS-rendered page.")

        for i, row_element in enumerate(match_rows):
            match_details = {
                "Round": current_round_placeholder, # TODO: Implement actual Round extraction
                "Date": current_date_placeholder,   # TODO: Implement actual Date extraction
                "Time": "N/A", "Home": "N/A", "Away": "N/A",
                "HG": "", "AG": "", "Venue": "N/A" # TODO: Implement actual Venue extraction if available
            }
            try:
                # --- Data Extraction Logic ---
                # YOU MUST INSPECT `_rendered_output.html` TO CONFIRM THESE SELECTORS
                # These are educated guesses based on common Livesport patterns.

                # Time: Often in a div with class containing 'event__time'
                time_div = row_element.select_one("div[class*='event__time']")
                if time_div: match_details["Time"] = time_div.text.strip()
                
                # Home Team: Often in a div with class containing 'event__participant--home'
                home_team_div = row_element.select_one("div[class*='event__participant--home']")
                if home_team_div: match_details["Home"] = home_team_div.text.strip()

                # Away Team: Often in a div with class containing 'event__participant--away'
                away_team_div = row_element.select_one("div[class*='event__participant--away']")
                if away_team_div: match_details["Away"] = away_team_div.text.strip()

                if is_results_page:
                    home_score_div = row_element.select_one("div[class*='event__score--home']")
                    if home_score_div and home_score_div.text.strip().isdigit():
                        match_details["HG"] = home_score_div.text.strip()
                    
                    away_score_div = row_element.select_one("div[class*='event__score--away']")
                    if away_score_div and away_score_div.text.strip().isdigit():
                        match_details["AG"] = away_score_div.text.strip()
                
                # Add to list if essential data like team names was found
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    matches_data.append(match_details)

            except Exception as e_row:
                print(f"Error processing a match row: {e_row}. Row HTML (snippet): {str(row_element)[:200]}")
                continue
        
        return matches_data

    except TimeoutException:
        print(f"Timeout waiting for page elements to load on {url}. Page might be too slow or selectors incorrect.")
        return []
    except WebDriverException as e_wd:
        print(f"WebDriverException occurred with {url}: {e_wd}")
        return []
    except Exception as e_general:
        print(f"An unexpected general error occurred with {url}: {e_general}")
        traceback.print_exc()
        return []

def main():
    driver = None
    try:
        driver = setup_driver() # Initialize WebDriver once
        print("WebDriver initialized.")

        print("\nScraping results...")
        results_data = scrape_page_with_selenium(driver, RESULTS_URL, is_results_page=True)
        print(f"Found {len(results_data)} matches on results page.")

        print(f"\nScraping fixtures...")
        fixtures_data = scrape_page_with_selenium(driver, FIXTURES_URL, is_results_page=False)
        print(f"Found {len(fixtures_data)} matches on fixtures page.")
        
        all_matches = results_data + fixtures_data
        
        if not all_matches:
            print("\nNo matches found in total. CSV file will be empty. Exiting.")
            return

        # --- Sorting Logic ---
        # TODO: This requires "Date" and "Time" to be correctly extracted and formatted.
        # Example: If Date is "14.05.2025" and Time is "19:45"
        def sort_key_matches(match):
            try:
                date_str = match.get('Date', '')
                time_str = match.get('Time', '00:00')
                if date_str in ["Date N/A (Selenium)", ""] or time_str == "N/A":
                    return datetime.max 
                # IMPORTANT: Adjust the format '%d.%m.%Y %H:%M' if your extracted date/time is different
                # This part of the script assumes you will refine date/time extraction.
                # For example, livesport often shows dates as "14.05." for current year, or "14.05.2025".
                # Time is usually "HH:MM".
                # You'll need to parse and combine these correctly.
                # For now, this is a placeholder and will likely fail if Date isn't in dd.mm.yyyy
                return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M') 
            except (ValueError, TypeError) as e:
                # print(f"Warning: Could not parse date/time for sorting: {match.get('Date')} {match.get('Time')} - Error: {e}")
                return datetime.max 

        all_matches.sort(key=sort_key_matches)
        print(f"\nTotal matches scraped and sorted: {len(all_matches)}")

        # --- Write to CSV file ---
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
    
