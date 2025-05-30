from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import re # Import regular expressions for parsing time suffixes

# Setup Chrome options
options = Options()
options.add_argument("--headless") # Run Chrome in headless mode (no UI)
options.add_argument("--no-sandbox") # Bypass OS security model, REQUIRED for Heroku/Docker
options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
options.add_argument("--window-size=1920,1080") # Specify window size
options.add_argument("--disable-gpu") # Applicable to windows os only
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")


# --- Main script logic ---
try:
    # Initialize the WebDriver
    # Ensure chromedriver is in your PATH or specify executable_path
    driver = webdriver.Chrome(options=options)
    
    # Navigate to the target URL
    driver.get('https://www.livesport.com/en/rugby-league/england/super-league/results/')

    # Wait for the match elements to be present on the page
    # This ensures the main containers for match data are loaded.
    WebDriverWait(driver, 20).until( 
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'event__match')) 
    )

    # Parse the page source with BeautifulSoup
    # driver.page_source will contain the HTML after JavaScript has had a chance to modify it,
    # up to the point the WebDriverWait condition was met and execution continued.
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all match containers
    matches = soup.find_all('div', class_='event__match')

    # Hardcoded year for the results.
    year = 2025 # You might want to make this dynamic, e.g., datetime.now().year
    rows = [] # List to store data for CSV

    # Iterate over each match found
    for match in matches:
        date_div = match.find('div', class_='event__time')
        home_team_el = match.find('div', class_='event__participant--home')
        away_team_el = match.find('div', class_='event__participant--away')
        home_score_el = match.find('span', class_='event__score--home') 
        away_score_el = match.find('span', class_='event__score--away') 
        
        # --- Period Score Elements ---
        # The following find calls look for elements containing period scores.
        # If these are blank in the CSV, it means BeautifulSoup did not find these elements
        # with the specified classes, or the elements were found but contained no text.
        # This could be due to:
        # 1. The website structure for these scores has changed (different class names).
        # 2. These scores are loaded by JavaScript later than the main content, and driver.page_source doesn't have them yet.
        # 3. The "results" page simply doesn't display these detailed scores for all matches.
        # Verify the class names and presence of these scores by inspecting the website's HTML.
        
        home_half1_el = match.find('div', class_='event__part--home event__part--1')
        away_half1_el = match.find('div', class_='event__part--away event__part--1')
        home_half2_el = match.find('div', class_='event__part--home event__part--2')
        away_half2_el = match.find('div', class_='event__part--away event__part--2')

        home_ot_el = match.find('div', class_='event__part--home event__part--OT')
        away_ot_el = match.find('div', class_=['event__part--away event__part--OT', 'event__part--away event__part--PEN']) 
        
        # Fallback for OT if specific OT class isn't found
        if not home_ot_el: 
            home_ot_el = match.find('div', class_='event__part--home event__part--3')
        if not away_ot_el: 
            away_ot_el = match.find('div', class_=['event__part--away event__part--3', 'event__part--away event__part--PEN'])

        if date_div and home_team_el and away_team_el:
            time_str_raw = date_div.text.strip() 
            
            parts = time_str_raw.split(maxsplit=1) 
            
            date_part_raw = ""
            time_part_raw = "" 
            match_status = ""  

            if len(parts) == 2:
                date_part_raw, time_part_raw = parts
            elif len(parts) == 1: 
                date_part_raw = parts[0]
            else:
                print(f"Skipping match due to empty or unexpected date/time string: '{time_str_raw}'")
                continue

            if date_part_raw.endswith('.'):
                date_part_clean = date_part_raw[:-1]
            else:
                date_part_clean = date_part_raw

            time_clean_for_parsing = "" 

            if time_part_raw: 
                time_components_match = re.match(r"(\d{1,2}:\d{2})([a-zA-Z]*)", time_part_raw)
                if time_components_match:
                    time_clean_for_parsing = time_components_match.group(1) 
                    match_status = time_components_match.group(2)      
                elif re.match(r"^\d{1,2}:\d{2}$", time_part_raw): 
                     time_clean_for_parsing = time_part_raw
                else:
                    print(f"Warning: Date part '{date_part_clean}' found, but the accompanying time part '{time_part_raw}' is not a recognized time format.")
            
            if not date_part_clean or not re.match(r"^\d{1,2}\.\d{1,2}$", date_part_clean):
                print(f"Skipping match: Date part '{date_part_clean}' is not in expected DD.MM format. Original string: '{time_str_raw}'")
                continue

            if not time_clean_for_parsing:
                # print(f"Info: Valid date '{date_part_clean}' found without a specific time (time part was '{time_part_raw}'). Using '00:00' as default time.")
                time_clean_for_parsing = "00:00" 
            
            full_date_str = f"{date_part_clean}.{year} {time_clean_for_parsing}"
            
            try:
                full_date = datetime.strptime(full_date_str, "%d.%m.%Y %H:%M")
                formatted_date = full_date.strftime("%d.%m.%Y %H:%M")
            except ValueError as e:
                print(f"Error parsing date string: '{full_date_str}' (from raw: '{time_str_raw}'). Error: {e}")
                continue 

            home_team = home_team_el.text.strip()
            away_team = away_team_el.text.strip()
            
            home_score = home_score_el.text.strip() if home_score_el else "?"
            away_score = away_score_el.text.strip() if away_score_el else "?"
            
            # Extract period scores; defaults to "" if element not found or empty
            half1_home = home_half1_el.text.strip() if home_half1_el else ""
            half1_away = away_half1_el.text.strip() if away_half1_el else ""
            half2_home = home_half2_el.text.strip() if home_half2_el else "" 
            half2_away = away_half2_el.text.strip() if away_half2_el else ""

            ot_home_score_val = home_ot_el.text.strip() if home_ot_el else None
            ot_away_score_val = away_ot_el.text.strip() if away_ot_el else None

            if match_status: # If status like "AET" or "PEN"
                ot_home_score = ot_home_score_val if ot_home_score_val is not None else "0" # Default to "0" if element missing but status indicates OT
                ot_away_score = ot_away_score_val if ot_away_score_val is not None else "0"
            else: # No specific match status
                ot_home_score = ot_home_score_val if ot_home_score_val is not None else "" # Default to "" if element missing and no OT status
                ot_away_score = ot_away_score_val if ot_away_score_val is not None else ""

            rows.append([
                year, formatted_date, home_team, away_team,
                home_score, away_score, half1_home, half1_away,
                half2_home, half2_away, ot_home_score, ot_away_score, 
                match_status   
            ])
        else:
            # print("Skipping a match entry due to missing essential data (date_div, home_team_el, or away_team_el).")
            pass

finally:
    if 'driver' in locals() and driver is not None:
        driver.quit()

csv_file_path = "super_league_results_selenium.csv"
with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Year", "Date Time", "Home Team", "Away Team", 
        "Home Score", "Away Score", 
        "Home Half 1", "Away Half 1", 
        "Home Half 2", "Away Half 2", 
        "Home OT", "Away OT", "Status" # Corrected spacing for "Home OT"
    ])
    for row_data in rows:
        writer.writerow(row_data)

print(f"Saved {len(rows)} match results to {csv_file_path}")
