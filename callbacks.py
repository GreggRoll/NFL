from app import app
from logger import setup_logger
from dash import Output, Input
import json
import pandas as pd
import plotly.express as px
from utils.helper_functions import get_data, generate_line_graph, load_historical_data

logger = setup_logger(__name__)

@app.callback(
    Output('data-table', 'data'),
    Output('data-table', 'tooltip_data'),
    Input('interval-component', 'n_intervals')
)
def update_table(n):
    # Fetch the latest data
    try:
        df = get_data()
    except Exception as e:
        logger.exception("Failed to fetch or parse data in get_data()")
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
        row_tooltip = {
            col: f"{col}: {str(row[col])}\nHistory: {', '.join(map(str, hist_values.get(col, ['N/A'])))}"
            for col in df.columns if col in ['Home Win', 'Away Win', 'points']
        }
        tooltip_data.append(row_tooltip)

    # Update the data and tooltips for the table
    logger.info(f"Table updated")
    return df.to_dict('records'), tooltip_data

@app.callback(
    Output('line-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    historical_data = load_historical_data()  # Reload historical data
    #if fails data_log empty
    try:
        logger.info(f"Graph updated")
        fig = generate_line_graph(historical_data)
        return fig
    except Exception as e:
        logger.exception("An error occurred")
        # Define coordinates for the letter 'N'
        data = pd.DataFrame([
            {"letter": 'N', "x": 0, "y":0},
            {"letter": 'N', "x": 0, "y":1},
            {"letter": 'N', "x": 0, "y":2},
            {"letter": 'N', "x": 0, "y":3},
            {"letter": 'N', "x": 1, "y":2},
            {"letter": 'N', "x": 2, "y":1},
            {"letter": 'N', "x": 3, "y":0},
            {"letter": 'N', "x": 3, "y":1},
            {"letter": 'N', "x": 3, "y":2},
            {"letter": 'N', "x": 3, "y":3},
            #O
            {"letter": 'O', "x": 5, "y":0},
            {"letter": 'O', "x": 4, "y":1.5},
            {"letter": 'O', "x": 5, "y":3},
            {"letter": 'O', "x": 6, "y":1.5},
            {"letter": 'O', "x": 5, "y":0},
            #D
            {"letter": 'D', "x": 8, "y":0},
            {"letter": 'D', "x": 8, "y":3},
            {"letter": 'D', "x": 9, "y":1.5},
            {"letter": 'D', "x": 8, "y":0},
            #A
            {"letter": 'A', "x": 10, "y":0},
            {"letter": 'A', "x": 11, "y":3},
            {"letter": 'A', "x": 12, "y":0},
            {"letter": 'A1', "x": 10.5, "y":1.5},
            {"letter": 'A1', "x": 11.5, "y":1.5},
            #T
            {"letter": 'T', "x": 14, "y":0},
            {"letter": 'T', "x": 14, "y":3},
            {"letter": 'T', "x": 12.5, "y":3},
            {"letter": 'T', "x": 15.5, "y":3},
            #A
            {"letter": 'A2', "x": 16, "y":0},
            {"letter": 'A2', "x": 17, "y":3},
            {"letter": 'A2', "x": 18, "y":0},
            {"letter": 'A3', "x": 16.5, "y":1.5},
            {"letter": 'A3', "x": 17.5, "y":1.5},
        ])

        # Create the line plot
        return px.line(data, color='letter', x='x', y='y', line_shape='linear')
