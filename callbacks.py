from app import app
from logger import setup_logger
from dash import Output, Input, State, html
from flask import request
import sqlite3
from itertools import groupby
import pandas as pd
import plotly.express as px
from utils.helper_functions import get_username_by_ip, read_chat_log, append_message_to_log, generate_username, get_data, generate_odds_graph, load_historical_data, generate_points_graph, generate_matchups, plot_no_data, generate_picks_graph

logger = setup_logger(__name__)

# Callback to display chat messages
@app.callback(
    Output('chat-box', 'children'),
    Input('chat-interval', 'n_intervals')
)
def update_chat(n):
    messages = read_chat_log()
    return [html.Div(f"{msg[2]}: {msg[3]}", style={"color": msg[2].split('-')[1]}) for msg in messages]

# Callback to send a new chat message
@app.callback(
    Output('chat-message', 'value'),
    [Input('send-button', 'n_clicks'), Input('chat-message', 'n_submit')],
    State('chat-message', 'value'),
    prevent_initial_call=True
)
def send_message(n_clicks, n_submit, message):
    if n_clicks or n_submit:
        if message != ''.strip():
            ip_address = request.remote_addr  # Get user IP address
            username = get_username_by_ip(ip_address)
            if not username:
                username = generate_username(ip_address)
            append_message_to_log(ip_address, username, message)
            return ''  # Clear input field after sending message
        return ''
    return message

@app.callback(
    Output('picks-graph', 'figure'),
    Output('data-table', 'data'),
    Output('data-table', 'tooltip_data'),
    Output('matchups-table', 'data'),
    Output('lower-odds-points-graph', 'figure'),
    Output('odds-graph', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_all(n, start_date, end_date):
    #graphs and things
    historical_data = load_historical_data(start_date, end_date)
    picks_fig = generate_picks_graph(historical_data, start_date, end_date)
    logger.info(f"Picks Graph updated")
    
    points_fig = generate_points_graph(historical_data, start_date, end_date)
    logger.info(f"Points Graph updated")
    odds_fig = generate_odds_graph(historical_data, start_date, end_date)
    logger.info(f"Odds Graph updated")
    # Fetch the latest data using the get_data function
    df = get_data(start_date, end_date)
    df_display = df.drop(columns=['game_id'])
    matchup_tbl = generate_matchups(df)

    # Connect to SQLite database to get historical data
    with sqlite3.connect('data-log.db') as conn:
        # Prepare tooltip data
        tooltip_data = []
        for index, row in df.iterrows():
            game_id = row['game_id']
            hist_query = f"SELECT * FROM nfl_data WHERE game_id = '{game_id}' ORDER BY datetime DESC"
            hist_df = pd.read_sql_query(hist_query, conn)
            row_tooltip = {}
            for col in ['home_win', 'away_win', 'points']:
                if col in df.columns:
                    current_value = row[col]
                    history = hist_df[col].tolist()
                    distinct_changes = [str(k) for k, g in groupby(history) if str(k) != str(current_value)]

                    row_tooltip[col] = f"{col}: {str(current_value)}"
                    if distinct_changes:
                        row_tooltip[col] += f"\nHistory: {', '.join(distinct_changes)}"
                    else:
                        row_tooltip[col] += "\nHistory: No changes"

            tooltip_data.append(row_tooltip)


    # Update the data and tooltips for the table
    logger.info("Table updated")
    return picks_fig, df_display.to_dict('records'), tooltip_data, matchup_tbl, points_fig, odds_fig, 
