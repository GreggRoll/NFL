from app import app
from logger import setup_logger
from dash import Output, Input, State, html
from flask import request
import json
from itertools import groupby
import pandas as pd
import plotly.express as px
from utils.helper_functions import get_username_by_ip, read_chat_log, append_message_to_log, generate_username, get_data, generate_odds_graph, load_historical_data, generate_points_graph, plot_no_data, generate_picks_graph

logger = setup_logger(__name__)

# Callback to display chat messages
@app.callback(
    Output('chat-box', 'children'),
    Input('chat-interval', 'n_intervals')
)
def update_chat(n):
    messages = read_chat_log()
    return [html.Div(f"{msg['username']}: {msg['message']}", style={"color": msg['username'].split('-')[1]}) for msg in messages]

# Callback to send a new chat message
@app.callback(
    Output('chat-message', 'value'),
    Input('send-button', 'n_clicks'),
    State('chat-message', 'value'),
    prevent_initial_call=True
)
def send_message(n_clicks, message):
    ip_address = request.remote_addr  # Get user IP address
    username = get_username_by_ip(ip_address)
    if not username:
        username = generate_username(ip_address)
    append_message_to_log(ip_address, username, message)
    return ''  # Clear input field after sending message

@app.callback(
    Output('data-table', 'data'),
    Output('data-table', 'tooltip_data'),
    Input('interval-component', 'n_intervals'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)

def update_table(n, start_date, end_date):
    # Fetch the latest data
    try:
        df = get_data(start_date, end_date)
        # Remove game_id from the DataFrame for display
        df_display = df.drop(columns=['game_id'])

        # Read the log file to get historical data and create a mapping
        historical_data = {}

        with open("data_log.jsonl", "r") as f:
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
            row_tooltip = {}

            for col in ['Home Win', 'Away Win', 'points']:
                if col in df.columns:
                    current_value = row[col]
                    history = hist_values.get(col, [])
                    # Filter to show only distinct changes
                    distinct_changes = [str(k) for k, g in groupby(history) if str(k) != str(current_value)]

                    row_tooltip[col] = f"{col}: {str(current_value)}"
                    if distinct_changes:
                        row_tooltip[col] += f"\nHistory: {', '.join(distinct_changes)}"
                    else:
                        row_tooltip[col] += "\nHistory: No changes"

            tooltip_data.append(row_tooltip)

        # Update the data and tooltips for the table
        logger.info("Table updated")
        return df_display.to_dict('records'), tooltip_data

    except Exception as e:
        logger.exception("Failed to fetch or parse data in get_data()")
        return None, None


@app.callback(
    Output('picks-graph', 'figure'),
    Output('lower-odds-points-graph', 'figure'),
    Output('odds-graph', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_graphs(n, start_date, end_date):
    historical_data = load_historical_data()
    picks_fig = generate_picks_graph(historical_data, start_date, end_date)
    logger.info(f"Points Graph updated")
    points_fig = generate_points_graph(historical_data, start_date, end_date)
    logger.info(f"Points Graph updated")
    historical_data = load_historical_data()  # Reload historical data
    odds_fig = generate_odds_graph(historical_data, start_date, end_date)
    logger.info(f"Odds Graph updated")
    return picks_fig, points_fig, odds_fig