from logger import setup_logger
import pandas as pd
import json
import plotly.express as px
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

logger = setup_logger(__name__)

def generate_game_id(row):
    try:
        # Example: Use a combination of date, home team, and away team to generate a unique ID
        identifier = f"{row['date']}_{row['home']}_{row['away']}"
        return hashlib.md5(identifier.encode()).hexdigest()
    except Exception as e:
        logger.exception("Generate Game error")
# Function to convert the betting odds to integers while handling the signs
def convert_to_int(value):
    try:
        if value == 'EVEN':
            return 0
        if value.startswith('+'):
            return int(value[1:])
        elif value.startswith('-'):
            return int(value)
        else:
            return int(value)
    except Exception as e:
        logger.exception("Convert to int error")
        return -1
    
def concat_values(x, y, z=None):
    if z:
        return f"{x} {y} {z}"
    return f"{x} {y}"
    
def get_data():
    # Configure ChromeOptions for headless browsing
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")  # This line can be important in certain environments
    # Initialize the Chrome WebDriver with the specified options
    driver = webdriver.Chrome(options=options)

    driver.get("https://www.bovada.lv/sports/football/nfl")

    # wait for the page to load
    time.sleep(10)
    driver.implicitly_wait(10)
    # get the HTML source
    html = driver.page_source

    # create a BeautifulSoup object
    soup = BeautifulSoup(html, "html.parser")

    # close the driver
    driver.quit()

    data = []
    sections = soup.find_all("section", {"class":"coupon-content more-info"})#soup.find_all("section", {"class":"coupon-content more-info"})
    for game in sections:
        try:
            item = str(game).split('>')
            info = [x.split('<')[0].strip() for x in item if not x.startswith("<")]
            data.append(info)
        except Exception as e:
            logger.exception("get data section error")
            pass

    df = pd.DataFrame(data)

    df["Home Spread"] = df.apply(lambda row: concat_values(row[10], row[11]), axis=1)
    df["Away Spread"] = df.apply(lambda row: concat_values(row[12], row[13]), axis=1)
    df["total_home"] = df.apply(lambda row: concat_values(row[16], row[17], row[18]), axis=1)
    df["total_away"] = df.apply(lambda row: concat_values(row[19], row[20], row[21]), axis=1)

    df.drop(columns = [3, 4, 5, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22], inplace=True)
    columns = ["date", "time", "bets", "home", "away", "Home Win", "Away Win", "Home Spread", "Away Spread", "Total Over", "Total Under"]
    df.columns = columns

    #filtering to this week
    today = datetime.now()
    #remove plus from bets
    df['bets'] = df['bets'].apply(lambda x: x[2:])

    days_until_next_monday = (7 - today.weekday()) % 7
    if days_until_next_monday == 0:
        days_until_next_monday = 7  # If today is Monday, we take the next Monday
    next_monday = today + timedelta(days=days_until_next_monday)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")
    #filter df to next monday
    df = df[df["date"] <= next_monday]
    #convert date back to str
    df["date"] = df['date'].dt.strftime('%A')
    df.reset_index(inplace=True, drop=True)

    # Applying the conversion to the 'win_home' and "Away Win" columns
    df['Home Win'] = df['Home Win'].apply(convert_to_int)
    df["Away Win"] = df["Away Win"].apply(convert_to_int)
    #ranking
    home = df[["home", 'Home Win']].rename(columns={'home': 'team', 'Home Win': 'odds'})
    away = df[['away', "Away Win"]].rename(columns={'away': 'team', "Away Win": 'odds'})

    combined = pd.concat([home, away]).sort_values('odds', ascending=False)
    combined['index'] = combined.index
    combined.index = range(0, 2*len(combined), 2)
    df['points'] = None

    # Iterating over the combined DataFrame to assign ranks
    for i, x in combined.iterrows():
        df.at[x['index'], 'points'] = (i-len(combined))/2

    current_df = df.sort_values('points', ascending=False)
    current_df["game_id"] = current_df.apply(generate_game_id, axis=1)
    current_df = current_df[['date', 'time', 'bets', 'home', 'away', 'points', 'Home Win', 'Away Win', 'Home Spread', 'Away Spread', 'Total Over', 'Total Under', 'game_id']]
                           
    # Initialize a flag to indicate whether to log the new data
    log_new_data = False

    # Read the last entry from the JSON log file
    try:
        with open("data_log.jsonl", "r") as f:
            lines = f.readlines()
            if lines:
                last_entry = json.loads(lines[-1])
                last_df = pd.DataFrame(last_entry["data"])
                # Compare with current data
                if not current_df.equals(last_df):
                    log_new_data = True
            else:
                # If the file is empty, log the new data
                log_new_data = True
    except FileNotFoundError:
        # If file doesn't exist, create it and log the new data
        logger.exception("log read error")
        log_new_data = True

    # Log the new data if it's different from the last entry
    if log_new_data:
        logger.info(f"added data to logs")
        log_entry = {"datetime": datetime.now().isoformat(), "data": current_df[["game_id", "home", "away", "Home Win", "Away Win", "points"]].to_dict()}
        with open("data_log.jsonl", "a") as f:
            json.dump(log_entry, f)
            f.write("\n")

    return current_df

def load_historical_data():
    plot_data = []
    with open('data_log.jsonl', 'r') as file:
        for line in file:
            entry = json.loads(line)
            datetime = entry['datetime']
            data = entry['data']
            for index, game_id in data['game_id'].items():
                home_team = data['home'][index]
                away_team = data['away'][index]
                plot_data.append({
                    'DateTime': datetime,
                    'Team': home_team,
                    'Win': data['Home Win'][index],
                    'Type': 'Home Win'
                })
                plot_data.append({
                    'DateTime': datetime,
                    'Team': away_team,
                    'Win': data['Away Win'][index],
                    'Type': 'Away Win'
                })
    return pd.DataFrame(plot_data)

def generate_line_graph(df):
    fig = px.line(df, x='DateTime', y='Win', color='Team', line_group='Team', 
                  labels={'Win': 'Winning Points', 'DateTime': 'DateTime', 'Team': 'Team'},
                  title='Winning Points Over Time', range_y=[550, -550])
    return fig