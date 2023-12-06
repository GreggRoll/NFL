from logger import setup_logger
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from helper_data import animals, colors, no_data

logger = setup_logger(__name__)

animals = ["Lion", "Tiger", "Bear", "Eagle", "Wolf"]
colors = ["Red", "Blue", "Green", "Yellow", "Purple"]

def get_username_by_ip(ip_address):
    try:
        with open("live-chat.jsonl", "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry['ip_address'] == ip_address:
                    return entry['username']
    except FileNotFoundError:
        pass  # File not found, meaning no messages have been logged yet
    return None  # No username found for this IP

def generate_username(ip_address):
    random_animal = random.choice(animals)
    random_color = random.choice(colors)
    return f"{random_animal}-{random_color}"

def append_message_to_log(ip_address, username, message):
    with open('live-chat.jsonl', 'a') as file:
        entry = {"ip_address": ip_address, "username": username, "message": message, "timestamp": datetime.now().isoformat()}
        file.write(json.dumps(entry) + '\n')

def read_chat_log():
    messages = []
    try:
        with open('live-chat.jsonl', 'r') as file:
            for line in file:
                messages.append(json.loads(line))
    except FileNotFoundError:
        pass  # No chat log exists yet
    return messages

def plot_no_data():
    data = pd.DataFrame(no_data)
    # Create the line plot
    return px.line(data, color='letter', x='x', y='y', line_shape='linear')

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
    
def get_data(start_date, end_date):
    # Configure ChromeOptions for headless browsing
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")  # This line can be important in certain environments
    options.set_capability('goog:loggingPrefs', {'browser': 'SEVERE'})
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
    #drop columns
    df.drop(columns = [3, 4, 5, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22], inplace=True)
    columns = ["date", "time", "bets", "home", "away", "Home Win", "Away Win", "Home Spread", "Away Spread", "Total Over", "Total Under"]
    df.columns = columns

    #remove plus from bets
    df['bets'] = df['bets'].apply(lambda x: x[2:])
    #filter data for date
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    #create day of the week column
    df["day"] = df['date'].dt.strftime('%A')
    #set back to string
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
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
    #add game id
    current_df["game_id"] = current_df.apply(generate_game_id, axis=1)
    #change column order
    current_df = current_df[['date', 'day', 'time', 'bets', 'home', 'away', 'points', 'Home Win', 'Away Win', 'Home Spread', 'Away Spread', 'Total Over', 'Total Under', 'game_id']]
                           
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
        log_entry = {"datetime": datetime.now().isoformat(), "data": current_df[["date", "game_id", "home", "away", "Home Win", "Away Win", "points"]].to_dict()}
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
                home_win = data['Home Win'][index]
                away_win = data['Away Win'][index]

                # Determine which team has the lower win odds
                if home_win < away_win:
                    # Home team has lower odds, so it gets positive points
                    home_points = data['points'][index]
                    away_points = -data['points'][index]
                else:
                    # Away team has lower odds, so it gets positive points
                    home_points = -data['points'][index]
                    away_points = data['points'][index]

                plot_data.append({
                    'DateTime': datetime,
                    'Team': home_team,
                    'Win': home_win,
                    'Type': 'Home Win',
                    'points': home_points
                })
                plot_data.append({
                    'DateTime': datetime,
                    'Team': away_team,
                    'Win': away_win,
                    'Type': 'Away Win',
                    'points': away_points
                })
    df = pd.DataFrame(plot_data)
    return df


def generate_picks_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date) & (df['points'] > 0)]
        # Create an empty figure
        fig = go.Figure()

        # Loop through each team and add a line trace
        for team in df['Team'].unique():
            team_df = df[df['Team'] == team]
            # Adding line trace for the team
            fig.add_trace(go.Scatter(
                x=team_df['DateTime'], 
                y=team_df['points'], 
                mode='lines', 
                name=team,
                hovertemplate="<br>".join([
                    "Date: %{x}",
                    "Points: %{y}"
                ])))

            # Adding team logo as an annotation at the last point
            last_point = team_df.iloc[-1]
            try:
                fig.add_layout_image(
                    dict(
                        source=f"assets/logos/{team}.png",
                        xref="x", yref="y",
                        x=last_point['DateTime'], y=last_point['points'],
                        sizex=0.2, sizey=0.2,  # Adjust size as needed
                        xanchor="center", yanchor="middle"
                    )
                )
            except Exception as e:
                logger.exception("Picks logo error")
                pass

        # Update layout
        fig.update_layout(
            title=f'Top Picks for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}',
            xaxis_title="Date Time",
            yaxis_title="Points",
            legend_title="Teams",
            legend={'traceorder': 'normal'}
        )
        fig
        return fig
    except Exception as e:
        logger.exception("ERROR generating picks graph")
        return plot_no_data()

def generate_odds_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        fig = px.line(df, x='DateTime', y='Win', color='Team', line_group='Team', 
                    labels={'Win': 'Winning Points', 'DateTime': 'DateTime', 'Team': 'Team'},
                    range_y=[550, -550])
        fig.update_layout(
            title=f'Odds for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}',
            xaxis_title="Date Time",
            yaxis_title="Straight Up Win Odds",
            legend_title="Teams",
            legend={'traceorder': 'normal'}
        )
        return fig
    except Exception as e:
        logger.exception("ERROR generating odds graph")
        return plot_no_data()

def generate_points_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        # Check if the required columns are present
        if not {'DateTime', 'points', 'Team', 'Type'}.issubset(df.columns):
            raise ValueError("Dataframe is missing one or more required columns.")
        # Getting the latest entry for each team
        latest_entries = df.sort_values(by='DateTime').groupby('Team').last().reset_index()
        # Sorting these entries by 'points'
        sorted_teams = latest_entries.sort_values(by='points', ascending=False)['Team']
        # Create the line chart
        fig = px.line(df, x='DateTime', y='points', color='Team', line_group='Type', title=f'Points for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}')
        # Reordering the legend
        fig.update_layout(
            title=f'Odds for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}',
            xaxis_title="Date Time",
            yaxis_title="Straight Up Win Odds",
            legend_title="Teams",
            legend={'traceorder': 'normal'}
            )
        fig.data = tuple(sorted(fig.data, key=lambda trace: sorted_teams.tolist().index(trace.name)))

        return fig
    except Exception as e:
        logger.exception("ERROR generating points graph")
        return plot_no_data()

