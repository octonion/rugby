import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

# Consider making these constants for easier changes
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "rugby_league_matches_improved.csv" # Suggesting a new name
# Define target headers based on super-league-2025.csv
TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]


def scrape_page(url, is_results_page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        matches_data = [] # Changed to store dicts
        
        # --- CRITICAL AREA: Date, Round, and Match Grouping ---
        # Livesport pages often group matches under date headers or round headers.
        # You need to iterate through the page structure to find these headers first,
        # then process the matches under them.

        # This is a simplified conceptual loop. You'll need to inspect your HTML
        # to find how dates/rounds and their associated matches are structured.
        # Elements could be divs that act as containers for a date and its matches.
        # Or, date/round headers might be siblings to match groups.

        # Example: Find all date/round sections (these selectors are HYPOTHETICAL)
        # page_sections = soup.find_all('div', class_='sportNameSoccer') # Or whatever main container
        
        current_round = "N/A" # Initialize / reset per appropriate scope
        current_date_str = "N/A" # Initialize / reset per appropriate scope

        # You'll likely need to find elements that denote a new date or round
        # For example, elements with class like 'event__header' or similar for dates/rounds
        # And then find all 'event__match' elements that fall under that header.
        # This part requires careful HTML inspection.

        # The provided 'match_rows = soup.find_all('div', class_='event__match')'
        # processes all matches flatly, losing the context of their date/round header.

        # Let's assume you have a way to get the correct date/round for a group of matches.
        # The following part would be *inside* a loop that correctly identifies
        # the date and round for the 'row' being processed.

        match_rows = soup.find_all('div', class_=lambda x: x and 'event__match' in x and 'event__match--scheduled' in x or 'event__match--live' in x or 'event__match--finished' in x) # Made class selector more specific / flexible
        if not match_rows:
            print(f"Warning: No elements found with class 'event__match...' on {url}. Check selectors.")

        # Placeholder for date/round - this needs to be determined by iterating sections
        # This logic needs significant revision based on HTML structure.
        # The original `find_previous` is very likely not robust enough.
        # You need to find the common parent or preceding header that defines the date/round.

        # For now, I'll adapt your existing loop but highlight its limitations.
        for row in match_rows:
            match_details = {}
            try:
                # --- Date, Time, Round Extraction (NEEDS REWORK) ---
                # This is the most complex part. Livesport might have a date like "14.05.2025"
                # as a header, and then multiple matches below it, each with just a time.
                # "Round X" might be another header.
                # The 'event__time' div might just contain the time or "Cancelled", "Postponed".

                time_element = row.find('div', class_=lambda x: x and 'event__time' in x)
                time_str = time_element.text.strip() if time_element else "N/A"

                # Placeholder: Date and Round need to be extracted from a higher-level element
                # associated with this 'row'. For this example, I'll use placeholders.
                # In a real implementation, you'd get this from the current section's header.
                # Let's simulate it being extracted earlier.
                # You would need to find, for example, the `div.event__round` or `div.event__header`
                # that applies to this match.

                # How to get the actual Date for the match?
                # If the time_str is like "14.05. 15:00", then parse it.
                # If time_str is just "15:00", you need to find the date from a parent/preceding header.
                # This example cannot fully solve this without seeing the live HTML structure
                # and how you choose to iterate. Let's assume for now `date_str_from_header` exists.
                
                # FAKE date_str_from_header for demonstration of parsing.
                # You'll need to find the actual date element.
                # e.g. date_header = row.find_previous_sibling('div', class_='event__header--date') # Hypothetical
                # date_str_from_header = date_header.text.strip() if date_header else "UnknownDate"
                
                # This part needs careful implementation based on actual HTML:
                date_parts = time_str.split(" ")
                if len(date_parts) > 1 and "." in date_parts[0] and ":" in date_parts[1] : # e.g., "15.05. 10:00"
                    actual_date_str = date_parts[0]
                    actual_time_str = date_parts[1]
                elif ":" in time_str: # Just time, e.g. "10:00" or "Postponed 10:00"
                    actual_date_str = "NEEDS_FROM_HEADER" # You must get this from a shared date header
                    actual_time_str = time_str # Or parse time out if "Postponed" etc.
                else: # "Finished", "Cancelled"
                    actual_date_str = "NEEDS_FROM_HEADER"
                    actual_time_str = "N/A" # Or the status itself

                # Simplified: Assume you have 'current_round' and 'current_date_str' from a higher context
                match_details["Round"] = current_round # Placeholder - needs real extraction
                match_details["Date"] = actual_date_str # Needs real extraction & formatting
                match_details["Time"] = actual_time_str # Needs real extraction & formatting

                home_team_div = row.find('div', class_=lambda x: x and ('event__participant--home' in x))
                match_details["Home"] = home_team_div.text.strip() if home_team_div else "N/A"
                
                away_team_div = row.find('div', class_=lambda x: x and ('event__participant--away' in x))
                match_details["Away"] = away_team_div.text.strip() if away_team_div else "N/A"

                if is_results_page:
                    home_score_div = row.find('div', class_=lambda x: x and 'event__score--home' in x)
                    match_details["HG"] = home_score_div.text.strip() if home_score_div and home_score_div.text.strip().isdigit() else ""
                    
                    away_score_div = row.find('div', class_=lambda x: x and 'event__score--away' in x)
                    match_details["AG"] = away_score_div.text.strip() if away_score_div and away_score_div.text.strip().isdigit() else ""
                    
                    # Handle cases like "Awrd." (awarded) or "-" if scores aren't purely numeric
                    if not match_details["HG"].isdigit(): match_details["HG"] = "" # Or "N/A"
                    if not match_details["AG"].isdigit(): match_details["AG"] = "" # Or "N/A"

                else: # Fixtures page
                    match_details["HG"] = ""
                    match_details["AG"] = ""
                
                match_details["Venue"] = "N/A" # Venue often not on list page, may need detail page scrape

                # Ensure essential fields are present
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    matches_data.append(match_details)
            
            except Exception as e: # More specific exceptions are better
                print(f"Error processing a match row on {url}: {e}. Row HTML (first 100 chars): {str(row)[:100]}")
                continue
        
        return matches_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred with {url}: {e}")
        return []

def main():
    print("Starting scraper...")
    # Scrape both pages
    print(f"Scraping results from: {RESULTS_URL}")
    results = scrape_page(RESULTS_URL, is_results_page=True)
    print(f"Found {len(results)} matches on results page.")

    print(f"Scraping fixtures from: {FIXTURES_URL}")
    fixtures = scrape_page(FIXTURES_URL, is_results_page=False)
    print(f"Found {len(fixtures)} matches on fixtures page.")
    
    all_matches = results + fixtures
    
    if not all_matches:
        print("No matches found. Exiting.")
        return

    # Sort by date and time (more robustly)
    # You'll need to ensure Date and Time are consistently parsed into sortable formats
    # This sort key is an EXAMPLE and depends heavily on how you parse Date and Time.
    # It assumes Date is 'dd.mm.yyyy' and Time is 'HH:MM'.
    def sort_key(match):
        try:
            # Handle cases where date might not be standard, or time is N/A
            if match.get("Date") == "NEEDS_FROM_HEADER" or match.get("Time") == "N/A":
                return datetime.min # Put problematic items at the beginning or end
            return datetime.strptime(f"{match['Date']} {match['Time']}", '%d.%m.%Y %H:%M') # Adjust format string
        except (ValueError, TypeError):
            print(f"Warning: Could not parse date/time for sorting: {match.get('Date')} {match.get('Time')}")
            return datetime.min # Or datetime.max to sort them differently

    all_matches.sort(key=sort_key, reverse=False) # Ascending by date/time usually makes more sense
    
    print(f"Total matches scraped: {len(all_matches)}")
    # Write to CSV file using DictWriter
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS)
            writer.writeheader()
            for match_dict in all_matches:
                # Ensure all keys in TARGET_CSV_HEADERS exist in match_dict
                row_to_write = {header: match_dict.get(header, "") for header in TARGET_CSV_HEADERS}
                writer.writerow(row_to_write)
        print(f"Data successfully written to {OUTPUT_CSV_FILE}")
    except IOError:
        print(f"I/O error writing to {OUTPUT_CSV_FILE}")

if __name__ == '__main__':
    main()
