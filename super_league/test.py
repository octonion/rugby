import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

def scrape_page(url, is_results_page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        matches = []
        
        # Find all match rows
        match_rows = soup.find_all('div', class_='event__match')
        
        for row in match_rows:
            # Extract date and time
            date_time_div = row.find_previous('div', class_='event__time')
            if not date_time_div:
                continue
                
            date_str = date_time_div.text.strip()
            
            # Try to parse the date to standardize the format
            try:
                # Handle different date formats (results vs fixtures)
                if is_results_page:
                    parsed_date = datetime.strptime(date_str, '%d.%m.%Y')
                    date_str = parsed_date.strftime('%d.%m.%Y')
                else:
                    parsed_date = datetime.strptime(date_str, '%a %d.%m.%Y %H:%M')
                    date_str = parsed_date.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                # If parsing fails, keep the original string
                pass
            
            # Extract team names
            home_team = row.find('div', class_='event__participant--home').text.strip()
            away_team = row.find('div', class_='event__participant--away').text.strip()
            
            # For results, extract scores; for fixtures, scores will be empty
            if is_results_page:
                score_home = row.find('div', class_='event__score--home').text.strip()
                score_away = row.find('div', class_='event__score--away').text.strip()
                
                # Extract period scores if available
                parts = row.find_all('div', class_='event__part')
                ht_home = parts[0].text.strip() if len(parts) > 0 else ''
                ht_away = parts[1].text.strip() if len(parts) > 1 else ''
                sh_home = parts[2].text.strip() if len(parts) > 2 else ''
                sh_away = parts[3].text.strip() if len(parts) > 3 else ''
                
                # Check for extra time
                extra_time = ''
                if 'AET' in row.text:
                    extra_time = 'AET'
                
                # Get current year (assuming all matches are in current year)
                year = datetime.now().year
                
                matches.append([
                    year,
                    date_str,
                    home_team,
                    away_team,
                    score_home,
                    score_away,
                    ht_home,
                    ht_away,
                    sh_home,
                    sh_away,
                    '',  # Empty columns
                    '',
                    extra_time
                ])
            else:
                # For fixtures, just include the basic info
                year = datetime.now().year
                matches.append([
                    year,
                    date_str,
                    home_team,
                    away_team,
                    '', '', '', '', '', '', '', '', ''
                ])
        
        return matches
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def main():
    results_url = "https://www.livesport.com/en/rugby-league/england/super-league/results/"
    fixtures_url = "https://www.livesport.com/en/rugby-league/england/super-league/fixtures/"
    
    # Scrape both pages
    results = scrape_page(results_url, is_results_page=True)
    fixtures = scrape_page(fixtures_url, is_results_page=False)
    
    # Combine results and fixtures
    all_matches = results + fixtures
    
    # Sort by date (newest first)
    all_matches.sort(key=lambda x: datetime.strptime(x[1].split()[0], '%d.%m.%Y'), reverse=True)
    
    # Write to CSV file
    with open('rugby_league_matches.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Year', 'Date', 'Home Team', 'Away Team', 'Home Score', 'Away Score',
            'HT Home', 'HT Away', 'SH Home', 'SH Away', '', '', 'Extra Time'
        ])
        writer.writerows(all_matches)
    
    print(f"Successfully saved {len(all_matches)} matches to rugby_league_matches.csv")

if __name__ == "__main__":
    main()
