import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

# ... (Keep your constants and TARGET_CSV_HEADERS) ...
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "rugby_league_matches_debugged.csv"
TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]


def scrape_page(url, is_results_page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    print(f"Attempting to fetch {url}...") # DEBUG
    try:
        response = requests.get(url, headers=headers, timeout=15) # Increased timeout slightly
        response.raise_for_status()
        print(f"Successfully fetched {url}, status {response.status_code}") # DEBUG

        if not response.text.strip():
            print(f"Warning: Response text for {url} is empty or whitespace only!") # DEBUG
            return [] # Return empty list if no content

        soup = BeautifulSoup(response.text, 'html.parser')
        if soup is None: # Highly unlikely with BS4, but good to be paranoid
            print(f"Critical Error: BeautifulSoup returned None for {url}!") # DEBUG
            return []
        
        # print(f"First 500 chars of HTML for {url}:\n{soup.prettify()[:500]}") # DEBUG: Uncomment to check HTML

        matches_data = []
        
        # --- DEBUGGING THE CRITICAL AREA ---
        # If you added logic to find overall sections, date headers, or round headers,
        # this is where you need to be careful.
        # Example:
        # date_header_elements = soup.find_all('div', class_='event__header') # find_all is safer
        # print(f"Found {len(date_header_elements)} date_header_elements.") # DEBUG
        # for header_element in date_header_elements:
        #     if header_element is None: # Should not happen in find_all result
        #         print("Found a None in date_header_elements loop!") # DEBUG
        #         continue
        #     # ... process header_element ...
        #     # Now find matches under this header
        #     # match_container = header_element.find_next_sibling('div', class_='matches_under_header_class') # find_next_sibling can be None
        #     # if match_container is None:
        #     #     print("Match container is None") # DEBUG
        #     #     continue
        #     # match_rows_under_header = match_container.find_all('div', class_='event__match')

        # Your current main match finding logic:
        # This selector might be too broad or too specific, or class names might have changed.
        # Test with simpler selectors first if this yields nothing.
        # e.g., just 'event__match' then refine.
        match_rows_selector = lambda x: x and ('event__match--scheduled' in x or 'event__match--live' in x or 'event__match--finished' in x) and 'event__match' in x
        match_rows = soup.find_all('div', class_=match_rows_selector)
        
        print(f"Found {len(match_rows)} potential match_rows using selector on {url}.") # DEBUG
        if not match_rows:
            # Try a broader selector if nothing found, to see if basic elements are there
            broader_match_rows = soup.find_all('div', class_=lambda x: x and 'event__match' in x)
            print(f"Using a broader selector, found {len(broader_match_rows)} elements with 'event__match' in class.") # DEBUG
            if not broader_match_rows:
                 print("Still no 'event__match' elements found even with broader selector. Check HTML structure of the page.")


        # Placeholder for current_round and current_date_str
        # These need to be properly extracted from page headers relative to match_rows
        current_round = "Round N/A"
        current_date_str = "Date N/A"

        for i, row in enumerate(match_rows): # Iterate over the list from find_all
            if row is None: # Should not happen if match_rows is from find_all
                print(f"Row {i} in match_rows is None! Skipping.") # DEBUG
                continue

            match_details = {"Round": current_round, "Date": current_date_str, "Venue": "Venue N/A"}
            try:
                # Time extraction
                time_element = row.find('div', class_=lambda x: x and 'event__time' in x)
                # print(f"Row {i} time_element: {type(time_element)}") # DEBUG
                match_details["Time"] = time_element.text.strip() if time_element else "N/A"
                
                # Home Team
                home_team_div = row.find('div', class_=lambda x: x and 'event__participant--home' in x)
                # print(f"Row {i} home_team_div: {type(home_team_div)}") # DEBUG
                match_details["Home"] = home_team_div.text.strip() if home_team_div else "N/A"
                
                # Away Team
                away_team_div = row.find('div', class_=lambda x: x and 'event__participant--away' in x)
                # print(f"Row {i} away_team_div: {type(away_team_div)}") # DEBUG
                match_details["Away"] = away_team_div.text.strip() if away_team_div else "N/A"

                if is_results_page:
                    home_score_div = row.find('div', class_=lambda x: x and 'event__score--home' in x)
                    match_details["HG"] = home_score_div.text.strip() if home_score_div and home_score_div.text.strip().isdigit() else ""
                    
                    away_score_div = row.find('div', class_=lambda x: x and 'event__score--away' in x)
                    match_details["AG"] = away_score_div.text.strip() if away_score_div and away_score_div.text.strip().isdigit() else ""
                else:
                    match_details["HG"], match_details["AG"] = "", ""
                
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    matches_data.append(match_details)
                # else:
                #     print(f"Skipping row {i} due to missing Home/Away team. Home: {match_details['Home']}, Away: {match_details['Away']}") # DEBUG

            except AttributeError as ae: # More specific error
                print(f"AttributeError processing match row {i} on {url}: {ae}. Row HTML (first 100 chars): {str(row)[:100]}")
                continue # Skip this problematic row
            # The TypeError 'NoneType is not iterable' would be caught by the broader 'except Exception' below if not here.
            # Add more specific try-except for parts where you suspect iteration over a None value.

        return matches_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching or network issue with {url}: {e}")
        return [] # Return empty list on fetch error
    except Exception as e: # This catches errors from within the try block above
        # This is where your "argument of type 'NoneType' is not iterable" error was caught
        print(f"An unexpected error occurred while processing {url}: {e} (Type: {type(e)})")
        import traceback # Import for more detailed error info
        traceback.print_exc() # Print the full traceback to see where in this function it happened
        return [] # Return empty list

# --- main function (mostly as before, but ensure it handles empty lists gracefully) ---
def main():
    print("Starting scraper...")
    results = scrape_page(RESULTS_URL, is_results_page=True)
    print(f"Found {len(results)} matches on results page.")

    print(f"Scraping fixtures from: {FIXTURES_URL}")
    fixtures = scrape_page(FIXTURES_URL, is_results_page=False)
    print(f"Found {len(fixtures)} matches on fixtures page.")
    
    all_matches = results + fixtures # This is fine if results/fixtures are empty lists
    
    if not all_matches:
        print("No matches found in total. Exiting.")
        return

    # ... (rest of your sorting and CSV writing - ensure date/time parsing for sort_key is robust) ...
    def sort_key(match):
        try:
            # Ensure Date and Time are in expected format, handle N/A or missing
            date_str = match.get('Date', '')
            time_str = match.get('Time', '00:00') # Default time if missing, for sorting
            if not date_str or date_str == "Date N/A" or date_str == "NEEDS_FROM_HEADER": # Handle placeholders
                return datetime.max # Put problematic items at the end
            
            # This datetime format needs to match EXACTLY how you store Date and Time
            # E.g., if Date is "14.05.2024" and Time is "15:30"
            return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M') # ADJUST FORMAT IF NEEDED
        except (ValueError, TypeError) as e:
            # print(f"Warning: Could not parse date/time for sorting: {match.get('Date')} {match.get('Time')} - Error: {e}")
            return datetime.max # Sort problematic items at the end

    all_matches.sort(key=sort_key)

    print(f"Total matches scraped and sorted: {len(all_matches)}")
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS, extrasaction='ignore') # ignore extra fields in dict
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"Data successfully written to {OUTPUT_CSV_FILE}")
    except IOError:
        print(f"I/O error writing to {OUTPUT_CSV_FILE}")
    except Exception as e:
        print(f"An error occurred during CSV writing: {e}")

if __name__ == '__main__':
    main()
    
