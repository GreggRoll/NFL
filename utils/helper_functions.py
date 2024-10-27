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
from .helper_data import animals, colors, no_data
import sqlite3

logger = setup_logger(__name__)

def insert_data_to_db(df, conn):
    try:
        df.to_sql('nfl_data', conn, if_exists='append', index=False)
    except Exception as e:
        logger.exception("insert_data_to_db")


def log_data_if_changed(current_df):
    try:
        with sqlite3.connect('data-log.db') as conn:
            cursor = conn.cursor()

            # Initialize an empty list to collect DataFrames for concatenation
            games_to_insert_list = []

            # Iterate over each game in the current DataFrame
            for index, game in current_df.iterrows():
                game_id = game['game_id']

                # Fetch the corresponding game data from the database by game_id
                cursor.execute("SELECT * FROM nfl_data WHERE game_id = ?", (game_id,))
                db_game = cursor.fetchone()
                columns = ['datetime', 'game_id', 'date', 'home_team', 'away_team', 'home_win', 'away_win', 'points']

                if db_game:
                    # Convert db_game to DataFrame for comparison
                    db_game_df = pd.DataFrame([db_game], columns=columns)

                    # Prepare current game data for comparison
                    current_game_df = pd.DataFrame([game], columns=columns)
                    current_game_df['datetime'] = datetime.now().isoformat()

                    # Compare with current game data
                    if not current_game_df.equals(db_game_df):
                        # Add to the list for bulk insertion
                        games_to_insert_list.append(current_game_df)
                else:
                    # If there is no entry for this game in the database, prepare for insertion
                    game['datetime'] = datetime.now().isoformat()
                    games_to_insert_list.append(pd.DataFrame([game], columns=columns))

            # Concatenate all DataFrames in the list for bulk insertion
            if games_to_insert_list:
                games_to_insert = pd.concat(games_to_insert_list, ignore_index=True)
                insert_data_to_db(games_to_insert, conn)
    except Exception as e:
        logger.exception("log_data_if_changed")

def get_username_by_ip(ip_address):
    try:
        conn = sqlite3.connect('data-log.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM chat_messages WHERE ip = ?", (ip_address,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.exception("get_username_by_ip")

def generate_username(ip_address):
    random_animal = random.choice(animals)
    random_color = random.choice(colors)
    return f"{random_animal}-{random_color}"

def append_message_to_log(ip_address, username, message):
    conn = sqlite3.connect('data-log.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_messages (ip, username, message, timestamp) VALUES (?, ?, ?, ?)",
                   (ip_address, username, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def read_chat_log():
    conn = sqlite3.connect('data-log.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_messages")
    messages = cursor.fetchall()
    conn.close()
    return messages

def plot_no_data():
    data = pd.DataFrame(no_data)
    # Create the line plot
    return px.line(data, color='letter', x='x', y='y', line_shape='linear')

def generate_game_id(row):
    try:
        # Example: Use a combination of date, home team, and away team to generate a unique ID
        identifier = f"{row['date']}_{row['home_team']}_{row['away_team']}"
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
    try:
        logger.info(f"fetching data for {start_date}-{end_date}")
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
        columns = ["date", "time", "bets", "home_team", "away_team", "home_win", "away_win", "home_spread", "away_spread", "total_over", "total_under"]
        df.columns = columns

        #remove plus from bets
        df['bets'] = df['bets'].apply(lambda x: x[2:])

        #date operations
        #filter data for date
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')  # Adjust the format if needed
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')  # Adjust the format if needed
            # Ensure the 'date' column in df is of type datetime.date
        
        # Ensure the 'date' column in df is of type datetime
        df['date'] = pd.to_datetime(df['date'])

        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        #create day of the week column
        df["day"] = df['date'].dt.strftime('%A')
        #set back to string
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        df.reset_index(inplace=True, drop=True)

        # Applying the conversion to the 'win_home' and "Away Win" columns
        df['home_win'] = df['home_win'].apply(convert_to_int)
        df["away_win"] = df["away_win"].apply(convert_to_int)
        #ranking
        home = df[["home_team", 'home_win']].rename(columns={'home_team': 'team', 'home_win': 'odds'})
        away = df[['away_team', "away_win"]].rename(columns={'away_team': 'team', "away_win": 'odds'})
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
        current_df = current_df[['date', 'day', 'time', 'bets', 'home_team', 'away_team', 'points', 'home_win', 'away_win', 'home_spread', 'away_spread', 'total_over', 'total_under', 'game_id']]
        log_data = current_df[['game_id', 'date', 'home_team', 'away_team', 'home_win', 'away_win', 'points']]
        log_data_if_changed(log_data)

        return current_df
    except Exception as e:
        logger.exception("get data")

def load_historical_data(start_date, end_date):
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('data-log.db')

        # Convert start and end dates to datetime objects if they are not
        if not isinstance(start_date, datetime):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if not isinstance(end_date, datetime):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Format dates for SQL query
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        # SQL query to load data between start_date and end_date
        query = f'''
        SELECT datetime, game_id, date, home_team, away_team, home_win, away_win, points 
        FROM nfl_data 
        WHERE datetime BETWEEN '{start_date_str}' AND '{end_date_str}'
        '''

        # Execute query and fetch data
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Process data to determine which team has the lower win odds
        plot_data = []
        for _, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            home_win = row['home_win']
            away_win = row['away_win']
            points = row['points']

            if home_win < away_win:
                home_points = points
                away_points = -points
            else:
                home_points = -points
                away_points = points

            plot_data.append({
                'DateTime': row['datetime'],
                'Team': home_team,
                'Win': home_win,
                'Type': 'Home Win',
                'points': home_points
            })
            plot_data.append({
                'DateTime': row['datetime'],
                'Team': away_team,
                'Win': away_win,
                'Type': 'Away Win',
                'points': away_points
            })

        return pd.DataFrame(plot_data)
    except Exception as e:
        logger.exception("get historical data")


def generate_picks_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df = df[df['points'] > 0]
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
        return fig
    except Exception as e:
        logger.exception("ERROR generating picks graph")
        return plot_no_data()

def generate_points_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        # df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        # Check if the required columns are present
        if not {'DateTime', 'points', 'Team', 'Type'}.issubset(df.columns):
            raise ValueError("Dataframe is missing one or more required columns.")
        # Getting the latest entry for each team
        latest_entries = df.sort_values(by='DateTime').groupby('Team').last().reset_index()
        # Sorting these entries by 'points'
        sorted_teams = latest_entries.sort_values(by='points', ascending=False)['Team']
        # Create the line chart
        fig = px.line(df, x='DateTime', y='points', color='Team', line_group='Type', 
                      title=f'Points for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}')
        # Reordering the legend
        fig.update_layout(
            title=f'Generated Points for {datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %d")} - {datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %d")}',
            xaxis_title="Date Time",
            yaxis_title="Generated points",
            legend_title="Teams",
            legend={'traceorder': 'normal'}
            )
        fig.data = tuple(sorted(fig.data, key=lambda trace: sorted_teams.tolist().index(trace.name)))

        return fig
    except Exception as e:
        logger.exception("ERROR generating points graph")
        return plot_no_data()

def generate_odds_graph(df, start_date, end_date):
    try:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        # df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        latest_entries = df.sort_values(by='DateTime').groupby('Team').last().reset_index()
        # Sorting these entries by 'points'
        sorted_teams = latest_entries.sort_values(by='points', ascending=False)['Team']
        fig = px.line(df, x='DateTime', y='Win', color='Team', line_group='Type',
                    labels={'Win': 'Winning Points', 'DateTime': 'DateTime', 'Team': 'Team'},
                    range_y=[df['Win'].max(), df['Win'].min()])
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
        logger.exception("ERROR generating odds graph")
        return plot_no_data()

def generate_matchups(df):
    try:
        # Ensure DateTime is properly formatted
        df['DateTime'] = pd.to_datetime(df['DateTime'])

        # Sort the DataFrame by DateTime to get matchups from soonest to latest
        sorted_df = df.sort_values(by='DateTime')

        # Prepare data for the DataTable
        matchups_data = []

        for _, row in sorted_df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            points = row['points']

            # Determine the favored team
            projected_winner = home_team if row['home_win'] > row['away_win'] else away_team

            # Add row data
            matchups_data.append({
                "matchup": f"{home_team} vs {away_team}",
                "time": row['DateTime'].strftime('%H:%M %p'),
                "projected_winner": projected_winner,
                "ranking": points
            })

        return matchups_data

    except Exception as e:
        logger.exception("Error preparing matchups data for table")
        return plot_no_data()

