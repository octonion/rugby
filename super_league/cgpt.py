from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import csv

# Setup Chrome options for headless browsing
options = Options()
options.headless = True # Run Chrome in headless mode (no UI)
# It's good practice to specify the executable_path if chromedriver is not in PATH,
# but often not needed if installed correctly.
# Example: driver = webdriver.Chrome(executable_path='/path/to/chromedriver', options=options)
driver = webdriver.Chrome(options=options)

try:
    # Navigate to the target URL
    driver.get('https://www.livesport.com/en/rugby-league/england/super-league/results/')

    # Wait for the match elements to be present on the page
    # This ensures the page is loaded enough for scraping
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'event__match'))
    )

    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all match containers
    matches = soup.find_all('div', class_='event__match')

    # Hardcoded year for the results.
    # Consider making this dynamic if scraping results from different years or if the site changes.
    year = 2025
    rows = [] # List to store data for CSV

    # Iterate over each match found
    for match in matches:
        # Find the elements containing date, teams, and scores
        date_div = match.find('div', class_='event__time')
        home_team_el = match.find('div', class_='event__participant--home')
        away_team_el = match.find('div', class_='event__participant--away')
        home_score_el = match.find('span', class_='event__score--home')
        away_score_el = match.find('span', class_='event__score--away')
        
        # Find elements for half-time scores
        home_half1 = match.find('div', class_='event__part--home event__part--1')
        away_half1 = match.find('div', class_='event__part--away event__part--1')
        home_half2 = match.find('div', class_='event__part--home event__part--2') # Typically full time, not second half score
        away_half2 = match.find('div', class_='event__part--away event__part--2') # Typically full time, not second half score

        # Ensure essential elements are found before proceeding
        if date_div and home_team_el and away_team_el:
            time_str = date_div.text.strip() # Get the date/time text, e.g., "04.05. 12:30"
            
            # Split the string into date and time parts
            # Assumes format "DD.MM.[ ]HH:MM" or "DD.MM[ ]HH:MM"
            parts = time_str.split()
            if len(parts) == 2:
                date_part, time_part = parts # date_part might be "DD.MM." or "DD.MM"
            else:
                # If the format is not as expected (e.g., only time, or malformed), skip this entry
                print(f"Skipping match due to unexpected date/time format: {time_str}")
                continue

            # --- FIX APPLIED HERE ---
            # Remove trailing dot from date_part if it exists to prevent "DD.MM..YYYY"
            if date_part.endswith('.'):
                date_part = date_part[:-1] # Strips the last character if it's a dot

            # Construct the full date string for parsing
            full_date_str = f"{date_part}.{year} {time_part}" # Should now be "DD.MM.YYYY HH:MM"
            
            try:
                # Parse the date string into a datetime object
                full_date = datetime.strptime(full_date_str, "%d.%m.%Y %H:%M")
                # Format the datetime object back into a desired string format
                formatted_date = full_date.strftime("%d.%m.%Y %H:%M")
            except ValueError as e:
                # If parsing fails, print an error and skip this match
                print(f"Error parsing date string: '{full_date_str}' for match. Error: {e}")
                print(f"Original time_str from website: '{time_str}'")
                continue

            # Extract team names
            home = home_team_el.text.strip()
            away = away_team_el.text.strip()
            
            # Extract scores, using "?" if not found (e.g., for future matches)
            home_score = home_score_el.text.strip() if home_score_el else "?"
            away_score = away_score_el.text.strip() if away_score_el else "?"
            
            # Extract half-time scores, empty string if not found
            # Note: event__part--1 is usually 1st half, event__part--2 might be 2nd half or full time depending on site
            half1_home = home_half1.text.strip() if home_half1 else ""
            half1_away = away_half1.text.strip() if away_half1 else ""
            
            # These typically represent full-time scores again in some contexts, or second half.
            # If you need specific second-half scores, you might need to calculate them
            # or find different elements if the site provides them directly.
            half2_home = home_half2.text.strip() if home_half2 else "" 
            half2_away = away_half2.text.strip() if away_half2 else ""

            # Append the extracted data as a new row
            rows.append([
                year,
                formatted_date,
                home,
                away,
                home_score,
                away_score,
                half1_home,
                half1_away,
                half2_home, # This might be full-time or 2nd half, verify site structure
                half2_away, # This might be full-time or 2nd half, verify site structure
                "", # Placeholder for additional data if needed
                "", # Placeholder
                ""  # Placeholder
            ])
        else:
            # If crucial elements like date or team names are missing, log it (optional)
            # print("Skipping a match entry due to missing essential data (date or teams).")
            pass


finally:
    # Always quit the driver to close the browser and free resources
    driver.quit()

# Define the CSV file path
csv_file_path = "super_league_results.csv"

# Write the collected data to a CSV file
with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    # Optionally, write a header row
    # writer.writerow(["Year", "Date Time", "Home Team", "Away Team", "Home Score", "Away Score", 
    #                  "Home Half 1", "Away Half 1", "Home Half 2/FT", "Away Half 2/FT", 
    #                  "Notes1", "Notes2", "Notes3"])
    for row in rows:
        writer.writerow(row)

print(f"Saved {len(rows)} match results to {csv_file_path}")
