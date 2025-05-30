import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import traceback # For detailed error traceback

# --- Configuration ---
RESULTS_URL = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
FIXTURES_URL = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
OUTPUT_CSV_FILE = "super_league_data_output.csv" # Changed name slightly

# Target CSV Headers based on super-league-2025.csv
TARGET_CSV_HEADERS = ["Round", "Date", "Time", "Home", "Away", "HG", "AG", "Venue"]

def scrape_page(url, is_results_page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    print(f"Attempting to fetch {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        print(f"Successfully fetched {url}, status {response.status_code}")

        # --- SAVE HTML CONTENT TO A FILE FOR INSPECTION ---
        # Creates filenames like 'results_output.html' or 'fixtures_output.html'
        # by taking the second to last part of the URL path.
        path_components = [comp for comp in url.split('/') if comp] # Get non-empty path components
        if len(path_components) > 1:
            filename_base = path_components[-1] # Usually 'results' or 'fixtures'
        else:
            filename_base = "unknown_page"
        html_filename = f"{filename_base}_raw_output.html"

        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved raw HTML content for {url} to {html_filename}")
        # --- END OF HTML SAVING BLOCK ---

        if not response.text.strip():
            print(f"Warning: Response text for {url} is empty or whitespace only! No data to parse.")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        if soup is None: # Should not happen with BeautifulSoup normally
            print(f"Critical Error: BeautifulSoup returned None when parsing {url}!")
            return []

        # You can uncomment this to print a snippet of the parsed HTML (might be very long)
        # print(f"First 1000 chars of parsed HTML for {url}:\n{soup.prettify()[:1000]}")

        matches_data = []
        
        # Placeholder for current_round and current_date_str
        # These would ideally be extracted from page section headers if available
        current_round_placeholder = "Round N/A"
        current_date_placeholder = "Date N/A" # This needs to be updated when parsing actual date elements

        # Attempt to find match rows - This is where your main selectors go.
        # The lambda function below tries to find elements with 'event__match' AND one of the status classes.
        # This is still a guess; you MUST verify actual class names from the saved HTML if data is present there.
        match_rows_selector = lambda x: x and \
                                    'event__match' in x and \
                                    ('event__match--scheduled' in x or \
                                     'event__match--live' in x or \
                                     'event__match--finished' in x)
        
        match_rows = soup.find_all('div', class_=match_rows_selector)
        print(f"Found {len(match_rows)} potential match rows using specific selector on {url}.")

        if not match_rows:
            # Try a broader selector as a fallback diagnostic
            broader_match_rows_selector = lambda x: x and 'event__match' in x
            broader_match_rows = soup.find_all('div', class_=broader_match_rows_selector)
            print(f"Using a broader selector, found {len(broader_match_rows)} elements with 'event__match' in class.")
            if not broader_match_rows:
                 print("Still no elements found even with a very broad 'event__match' selector. " \
                       "Check the saved HTML file to confirm if match data is present in the initial download, " \
                       "or if it's loaded by JavaScript.")
            # If you want to proceed with broader_match_rows if specific one fails:
            # match_rows = broader_match_rows


        for i, row_element in enumerate(match_rows):
            if row_element is None: # Should not happen if match_rows is from find_all
                print(f"Row {i} in match_rows is None! Skipping.")
                continue

            # Initialize with placeholders, especially for Round, Date, Venue
            match_details = {
                "Round": current_round_placeholder, # Needs logic to find actual round
                "Date": current_date_placeholder,   # Needs logic to find actual date
                "Time": "N/A",
                "Home": "N/A",
                "Away": "N/A",
                "HG": "",
                "AG": "",
                "Venue": "N/A" # Venue is often not on the list page
            }
            try:
                # --- Extraction logic for each field ---
                # This requires you to inspect the saved HTML and find correct selectors
                # The class names used below are HYPOTHETICAL based on common patterns.

                # Example: Time (often in a div with class containing 'event__time')
                time_div = row_element.find('div', class_=lambda c: c and 'event__time' in c)
                if time_div:
                    match_details["Time"] = time_div.text.strip()
                
                # Example: Home Team
                home_team_div = row_element.find('div', class_=lambda c: c and 'event__participant--home' in c)
                if home_team_div:
                    match_details["Home"] = home_team_div.text.strip()

                # Example: Away Team
                away_team_div = row_element.find('div', class_=lambda c: c and 'event__participant--away' in c)
                if away_team_div:
                    match_details["Away"] = away_team_div.text.strip()

                if is_results_page:
                    home_score_div = row_element.find('div', class_=lambda c: c and 'event__score--home' in c)
                    if home_score_div and home_score_div.text.strip().isdigit():
                        match_details["HG"] = home_score_div.text.strip()
                    
                    away_score_div = row_element.find('div', class_=lambda c: c and 'event__score--away' in c)
                    if away_score_div and away_score_div.text.strip().isdigit():
                        match_details["AG"] = away_score_div.text.strip()
                
                # Add to list if essential data like team names was found
                if match_details["Home"] != "N/A" and match_details["Away"] != "N/A":
                    matches_data.append(match_details)
                # else:
                #     print(f"Skipping row {i} due to missing Home/Away team. Row: {str(row_element)[:100]}")

            except AttributeError as ae:
                print(f"AttributeError processing a match row on {url}: {ae}. Row HTML (snippet): {str(row_element)[:100]}")
                continue 
            except Exception as e_row: # Catch other errors during row processing
                print(f"Unexpected error processing a match row on {url}: {e_row}. Row HTML (snippet): {str(row_element)[:100]}")
                traceback.print_exc()
                continue
        
        return matches_data
    
    except requests.exceptions.RequestException as e_req:
        print(f"RequestException (network issue or bad HTTP status) for {url}: {e_req}")
        return []
    except Exception as e_general:
        print(f"An unexpected general error occurred with {url}: {e_general} (Type: {type(e_general)})")
        traceback.print_exc() # Print full traceback for unexpected errors
        return []

def main():
    print("Starting scraper...")
    results_data = scrape_page(RESULTS_URL, is_results_page=True)
    print(f"Found {len(results_data)} matches on results page.")

    print(f"\nScraping fixtures from: {FIXTURES_URL}")
    fixtures_data = scrape_page(FIXTURES_URL, is_results_page=False)
    print(f"Found {len(fixtures_data)} matches on fixtures page.")
    
    all_matches = results_data + fixtures_data
    
    if not all_matches:
        print("\nNo matches found in total. CSV file will be empty or not created. Exiting.")
        return

    # --- Sorting Logic (Relies on Date and Time being parsed correctly) ---
    # This is a placeholder sort key. You'll need to ensure "Date" and "Time"
    # are extracted and formatted consistently in scrape_page for this to work.
    def sort_key_matches(match):
        try:
            date_str = match.get('Date', '')
            time_str = match.get('Time', '00:00') # Default time if missing

            # Handle placeholder dates/times for sorting
            if date_str in ["Date N/A", "NEEDS_FROM_HEADER", ""] or time_str == "N/A":
                return datetime.max # Put items with invalid dates/times at the end

            # Adjust this format string to match your actual extracted date and time
            # Example assumes Date: "dd.mm.yyyy" and Time: "HH:MM"
            return datetime.strptime(f"{date_str} {time_str}", '%d.%m.%Y %H:%M')
        except (ValueError, TypeError) as e:
            # print(f"Warning: Could not parse date/time for sorting: {match.get('Date')} {match.get('Time')} - Error: {e}")
            return datetime.max # Fallback for unparseable date/times

    all_matches.sort(key=sort_key_matches)
    print(f"\nTotal matches scraped and sorted: {len(all_matches)}")

    # --- Write to CSV file ---
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            # Using DictWriter for robustness with headers
            writer = csv.DictWriter(csvfile, fieldnames=TARGET_CSV_HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_matches)
        print(f"Data successfully written to {OUTPUT_CSV_FILE}")
    except IOError:
        print(f"I/O error writing to {OUTPUT_CSV_FILE}")
    except Exception as e_csv:
        print(f"An error occurred during CSV writing: {e_csv}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
    
