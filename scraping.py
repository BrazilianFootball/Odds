import requests
import pandas as pd

from tqdm import tqdm
from glob import glob
from bs4 import BeautifulSoup

HEADER = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
  "X-Requested-With": "XMLHttpRequest"
}

def get_soup_from_url(url):
    response = requests.get(url, headers = HEADER)
    return BeautifulSoup(response.text, 'html.parser')

def get_soup_from_string(html):
    html = f'<html><body>{html}</body></html>'
    return BeautifulSoup(html, 'html.parser')

def catch_tables(soup, replace_str):
    tblehead_divs = soup.find_all('div', class_='tblehead')
    tables = dict()
    for div in tblehead_divs:
        header = div.get_text(strip=True).replace(f'{replace_str}', '')
        table = div.find_next('table')
        if table: tables[header] = table
    
    return tables

def catch_game_url(tables):
    for header in tables:
        new_soup = get_soup_from_string(tables[header])
        internal_tables = new_soup.find_all('table', class_='tble')
        tables[header] = dict()
        count = 0
        for table in internal_tables:
            links = table.find_all('a', href=True)
            for link in links:
                href = link['href']
                text = link.get_text(strip=True)
                if text in tables[header]: text += ' (playoff)'
                tables[header][text] = f'https://checkbestodds.com{href}'
                count += 1
        
        if count != len(tables[header]):
            print(f'{header} with inconsistency. Collected {count} games, but saved only {len(tables[header])}.')

    return tables

def catch_odds_table(game_soup):
    game_tables = dict()
    tblehead_divs = game_soup.find_all('div', class_='tblehead')
    for div in tblehead_divs:
        header = div.get_text(strip=True)
        table = div.find_next('table')
        if table: game_tables[header] = table

    return game_tables

def catch_odds(game_tables):
    for header in game_tables:
        new_soup = get_soup_from_string(game_tables[header])
        internal_tables = new_soup.find_all('table', class_='tble sort6')
        game_tables[header] = dict()
        for table in internal_tables:
            rows = table.find_all('tr')[1:]
            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 3:
                    bookmaker = columns[0].get_text(strip=True)
                    if bookmaker == 'Best odds': continue
                    home_team_odd = columns[1].find('span', class_='toSort noDsp').get_text(strip=True)
                    draw_odd = columns[2].find('span', class_='toSort noDsp').get_text(strip=True)
                    away_team_odd = columns[3].find('span', class_='toSort noDsp').get_text(strip=True)
                    game_tables[header][bookmaker] = [home_team_odd, draw_odd, away_team_odd]

    return game_tables

def save_odds(odds, year):
    df = pd.DataFrame(columns = ['Year', 'Competition', 'Game', 'Odd group', 'House', 'Home', 'Draw', 'Away'])
    for competition in odds:
        for game in odds[competition]:
            for odd_group in odds[competition][game]:
                for house in odds[competition][game][odd_group]:
                    df.loc[len(df)] = [year, competition, game, odd_group, house] + odds[competition][game][odd_group][house]

    df.to_csv(f'odds/{year}.csv', index = False)

def extract_odds(year):
    odds = dict()
    url = f'https://checkbestodds.com/football-odds/archive-brazil/{year}'
    soup = get_soup_from_url(url)
    odds = catch_tables(soup, 'Best odds')
    odds = catch_game_url(odds)
    for competition in odds:
        for game in tqdm(odds[competition]):
            game_soup = get_soup_from_url(odds[competition][game])
            odds[competition][game] = catch_odds_table(game_soup)
            odds[competition][game] = catch_odds(odds[competition][game])
    
    save_odds(odds, year)

if __name__ == '__main__':
    INITIAL_YEAR = 2023
    FINAL_YEAR = 2024
    for year in range(INITIAL_YEAR, FINAL_YEAR):
        if f'odds/{year}.csv' in glob('odds/*.csv'): continue
        print(year)
        extract_odds(year)
