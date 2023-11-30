import dash
from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import json
from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import hashlib

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

# Layout of the app
app.layout = html.Div([
    dcc.Interval(
        id='interval-component',
        interval=5*60*1000,  # 5 mins in milliseconds
        n_intervals=0
    ),
    html.H1("Bovada odds table", style={'textAlign': 'center'}),
    dbc.Row(
        [
        dash_table.DataTable(id='data-table',
            tooltip_data=[],
            style_data={'color': 'black', 'backgroundColor': 'white', 'justify': 'center'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(220, 220, 220)',}],
            style_header={'backgroundColor': 'rgb(210, 210, 210)', 'color': 'black', 'fontWeight': 'bold'}
            )
        ],
        justify="center",  # This centers the Row contents
        className="p-5"  # Adds padding; you can adjust the number (1-5) for different padding sizes
    )
])

def generate_game_id(row):
    # Example: Use a combination of date, home team, and away team to generate a unique ID
    identifier = f"{row['date']}_{row['home']}_{row['away']}"
    return hashlib.md5(identifier.encode()).hexdigest()
# Function to convert the betting odds to integers while handling the signs
def convert_to_int(value):
    if value == 'EVEN':
        return 0
    if value.startswith('+'):
        return int(value[1:])
    elif value.startswith('-'):
        return int(value)
    else:
        return int(value)
    
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
        except:
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
    #current_df = current_df["date", "time", "bets", "home", "away", "points", "Home Win", "Away Win", "Home Spread", "Away Spread", "Total Over", "Total Under" , "game_id"]
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
        log_new_data = True

    # Log the new data if it's different from the last entry
    if log_new_data:
        log_entry = {"datetime": datetime.now().isoformat(), "data": current_df[["game_id", "Home Win", "Away Win", "points"]].to_dict()}
        with open("data_log.jsonl", "a") as f:
            json.dump(log_entry, f)
            f.write("\n")

    return current_df

@app.callback(
    Output('data-table', 'data'),
    Output('data-table', 'tooltip_data'),
    Input('interval-component', 'n_intervals')
)
def update_table(n):
    # Fetch the latest data
    df = get_data()

    # Read the log file to get historical data and create a mapping
    historical_data = {}

    with open("data_log.json", "r") as f:
        for line in f:
            entry = json.loads(line)
            data = entry['data']
            for index, game_id in data['game_id'].items():
                if game_id not in historical_data:
                    historical_data[game_id] = {'Home Win': [], 'Away Win': [], 'points': []}

                # Append historical values for this game_id
                historical_data[game_id]['Home Win'].append(data['Home Win'][index])
                historical_data[game_id]['Away Win'].append(data['Away Win'][index])
                historical_data[game_id]['points'].append(data['points'][index])

    # Prepare tooltip data
    tooltip_data = []
    for index, row in df.iterrows():
        game_id = row['game_id']
        hist_values = historical_data.get(game_id, {})
        row_tooltip = {
            col: f"{col}: {str(row[col])}\nHistory: {', '.join(map(str, hist_values.get(col, ['N/A'])))}"
            for col in df.columns if col in ['Home Win', 'Away Win', 'points']
        }
        tooltip_data.append(row_tooltip)

    # Update the data and tooltips for the table
    return df.to_dict('records'), tooltip_data

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
