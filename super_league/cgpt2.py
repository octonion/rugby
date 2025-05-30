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
options.add_argument("--no-sandbox") # Bypass OS security model, REQUIRED for Heroku
options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
# It's good practice to specify the executable_path if chromedriver is not in PATH,
# but often not needed if installed correctly.
# Example: driver = webdriver.Chrome(executable_path='/path/to/chromedriver', options=options)


# --- Main script logic ---
try:
    # Initialize the WebDriver
    # Ensure chromedriver is in your PATH or specify executable_path
    driver = webdriver.Chrome(options=options)
    
    # Navigate to the target URL
    driver.get('https://www.livesport.com/en/rugby-league/england/super-league/results/')

    # Wait for the match elements to be present on the page
    # This ensures the page is loaded enough for scraping
    WebDriverWait(driver, 20).until( # Increased wait time for potentially slower connections
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'event__match')) # Wait for all, not just one
    )

    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all match containers
    matches = soup.find_all('div', class_='event__match')

    # Hardcoded year for the results.
    # Consider making this dynamic if scraping results from different years or if the site changes.
    year = 2025 # You might want to make this dynamic, e.g., datetime.now().year
    rows = [] # List to store data for CSV

    # Iterate over each match found
    for match in matches:
        # Find the elements containing date, teams, and scores
        date_div = match.find('div', class_='event__time')
        home_team_el = match.find('div', class_='event__participant--home')
        away_team_el = match.find('div', class_='event__participant--away')
        home_score_el = match.find('span', class_='event__score--home') # Main score
        away_score_el = match.find('span', class_='event__score--away') # Main score
        
        # Find elements for half-time scores
        home_half1_el = match.find('div', class_='event__part--home event__part--1')
        away_half1_el = match.find('div', class_='event__part--away event__part--1')
        
        # Find elements for second-half scores (assuming event__part--2 is second half or full time for some sports)
        # Note: For rugby league, event__part--2 might be the second half score *added* to first, or just the second half score.
        # The example output suggests the latter.
        home_half2_el = match.find('div', class_='event__part--home event__part--2')
        away_half2_el = match.find('div', class_='event__part--away event__part--2')

        # Find elements for Overtime (OT) scores
        home_ot_el = match.find('div', class_='event__part--home event__part--OT')
        away_ot_el = match.find('div', class_=['event__part--away event__part--OT', 'event__part--away event__part--PEN']) # Also check for PEN for penalties
        
        # Fallback for OT if specific OT class isn't found, some sites use event__part--3, event__part--4 etc.
        if not home_ot_el: 
            home_ot_el = match.find('div', class_='event__part--home event__part--3')
        if not away_ot_el: 
            away_ot_el = match.find('div', class_=['event__part--away event__part--3', 'event__part--away event__part--PEN'])


        # Ensure essential elements are found before proceeding
        if date_div and home_team_el and away_team_el:
            time_str_raw = date_div.text.strip() 
            
            parts = time_str_raw.split(maxsplit=1) 
            
            date_part_raw = ""
            time_part_raw = ""
            match_status = "" 

            if len(parts) == 2:
                date_part_raw, time_part_raw = parts
            elif len(parts) == 1: 
                time_match_re = re.match(r"(\d{2}:\d{2})([a-zA-Z]*)", parts[0])
                if time_match_re:
                    time_part_raw = parts[0]
                else: 
                    date_part_raw = parts[0] # Could be a status like "Finished", "Postponed"
            else:
                # This case means time_str_raw was empty or only whitespace
                print(f"Skipping match due to empty or unexpected date/time string: '{time_str_raw}'")
                continue

            # Clean date_part_raw: remove trailing dot if it exists
            if date_part_raw.endswith('.'):
                date_part_clean = date_part_raw[:-1]
            else:
                date_part_clean = date_part_raw

            # Process time_part_raw to separate HH:MM from suffixes like AET
            time_components_match = re.match(r"(\d{1,2}:\d{2})([a-zA-Z]*)", time_part_raw)
            
            time_clean_for_parsing = ""

            if time_components_match:
                time_clean_for_parsing = time_components_match.group(1) 
                match_status = time_components_match.group(2)      
            elif re.match(r"\d{1,2}:\d{2}", time_part_raw): # If it's just HH:MM without suffix
                 time_clean_for_parsing = time_part_raw
            else:
                # If time_part_raw doesn't contain a recognizable time
                if not date_part_clean: 
                    print(f"Skipping match, unclear date/time: Date='{date_part_clean}', TimeRaw='{time_part_raw}'")
                    continue
                # If date exists, but time is not parsable (e.g. "Finished", "Cancelled")
                # We need a valid time to parse. If not, we skip.
                if not time_clean_for_parsing: # Check if time could be parsed
                     print(f"Skipping match due to unparsable or missing time component: '{time_part_raw}' from '{time_str_raw}'")
                     continue

            # Ensure date_part_clean is not empty and looks like a date part
            if not date_part_clean or not re.match(r"\d{1,2}\.\d{1,2}", date_part_clean): 
                print(f"Skipping match due to missing or invalid date part: '{date_part_clean}'. Original string: {time_str_raw}")
                continue
            
            # Ensure time_clean_for_parsing is not empty
            if not time_clean_for_parsing:
                print(f"Skipping match due to missing time for parsing. Original string: {time_str_raw}, Date part: {date_part_clean}")
                continue
                
            full_date_str = f"{date_part_clean}.{year} {time_clean_for_parsing}"
            
            try:
                full_date = datetime.strptime(full_date_str, "%d.%m.%Y %H:%M")
                formatted_date = full_date.strftime("%d.%m.%Y %H:%M")
            except ValueError as e:
                print(f"Error parsing date string: '{full_date_str}' (from raw: '{time_str_raw}'). Error: {e}")
                continue # Skip this match if date cannot be parsed

            # Extract team names
            home_team = home_team_el.text.strip()
            away_team = away_team_el.text.strip()
            
            # Extract scores, using "?" if not found (e.g., for future matches)
            home_score = home_score_el.text.strip() if home_score_el else "?"
            away_score = away_score_el.text.strip() if away_score_el else "?"
            
            # Extract half-time scores
            half1_home = home_half1_el.text.strip() if home_half1_el else ""
            half1_away = away_half1_el.text.strip() if away_half1_el else ""
            
            # Extract second-half scores
            half2_home = home_half2_el.text.strip() if home_half2_el else "" 
            half2_away = away_half2_el.text.strip() if away_half2_el else ""

            # Extract Overtime scores
            ot_home_score_val = home_ot_el.text.strip() if home_ot_el else None
            ot_away_score_val = away_ot_el.text.strip() if away_ot_el else None

            # Logic for OT scores based on match_status and presence of OT elements
            if match_status: # e.g., AET, PEN
                ot_home_score = ot_home_score_val if ot_home_score_val is not None else "0"
                ot_away_score = ot_away_score_val if ot_away_score_val is not None else "0"
            else: # No specific status like AET
                ot_home_score = ot_home_score_val if ot_home_score_val is not None else ""
                ot_away_score = ot_away_score_val if ot_away_score_val is not None else ""


            rows.append([
                year,
                formatted_date,
                home_team,
                away_team,
                home_score,
                away_score,
                half1_home,
                half1_away,
                half2_home, 
                half2_away, 
                ot_home_score, 
                ot_away_score, 
                match_status   
            ])
        else:
            # If crucial elements like date or team names are missing
            # print("Skipping a match entry due to missing essential data (date or teams).")
            pass

finally:
    # Always quit the driver to close the browser and free resources
    if 'driver' in locals() and driver is not None:
        driver.quit()

# Define the CSV file path
csv_file_path = "super_league_results_selenium.csv"

# Write the collected data to a CSV file
with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    # Write a header row
    writer.writerow([
        "Year", "Date Time", "Home Team", "Away Team", 
        "Home Score", "Away Score", 
        "Home Half 1", "Away Half 1", 
        "Home Half 2", "Away Half 2", # Or Full Time if structure differs
        "Home OT", "Away OT", "Status"
    ])
    for row_data in rows:
        writer.writerow(row_data)

print(f"Saved {len(rows)} match results to {csv_file_path}")

# --- To demonstrate the output (optional, if you want to see it in console) ---
# print("\n--- CSV Content (first 5 rows) ---")
# try:
#     with open(csv_file_path, "r", encoding="utf-8") as f:
#         reader = csv.reader(f)
#         for i, row in enumerate(reader):
#             if i < 6: # Print header + 5 data rows
#                 print(row)
#             else:
#                 break
# except Exception as e:
#     print(f"Could not read CSV for demonstration: {e}")
# --- End of demonstration print ---
