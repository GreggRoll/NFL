from app import app
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

today = datetime.now()
weekday = today.weekday()  # Monday is 0 and Sunday is 6
if weekday == 1:  # If today is Tuesday
    start_date = today
else:
    days_since_tuesday = (weekday - 1) % 7
    start_date = today - timedelta(days=days_since_tuesday)
if weekday == 0:  # If today is Monday
    end_date = today
else:
    days_until_monday = (7 - weekday) % 7
    end_date = today + timedelta(days=days_until_monday)
start_date = start_date.date()
end_date = end_date.date()

header_row = dbc.Row([
    dbc.Col(html.H1("NFL Pick'em Pool Odds", className="title"), width=12, align="center"),
    dbc.Col(
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=start_date,
            end_date=end_date,
            display_format='YYYY-MM-DD',
            style={'display': 'none'}#className='datepicker'  # Add a custom class
        ),
        width=4,
        align="center",
        className="text-right"
    )
], className="mb-3")

interval = dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # 5 mins in milliseconds
            n_intervals=0
        )

chat_layout = html.Div([
    dcc.Interval(id='chat-interval', interval=5000, n_intervals=0),
    html.Div(id='chat-box', className='chat-box'),
    html.Div([
        dcc.Input(id='chat-message', type='text', className='chat-input'),
        html.Button('Send', id='send-button', className='chat-send')
    ], className='chat-input-container'),  # Container for input and button
], className='chat-layout')

table = dbc.Row([
    dbc.Col(
        dash_table.DataTable(
            id='data-table',
            tooltip_data=[],
            style_data={
                'color': 'black', 
                'backgroundColor': 'white', 
                'justify': 'center'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'}, 
                    'backgroundColor': 'rgb(220, 220, 220)'
                }
            ],
            style_header={
                'color': 'black', 
                'fontWeight': 'bold'
            },
            style_table={'overflowX': 'auto'},  # Enable horizontal scroll
        ),
        # width=12
    )
], className="data-table")

points_graph = dbc.Row(dcc.Graph(id='lower-odds-points-graph'),
            justify="center",
            className="line-graph")

picks_graph = dbc.Row(dcc.Graph(id='picks-graph'),
            justify="center",
            className="line-graph")

odds_graph = dbc.Row(dcc.Graph(id='odds-graph'),
            justify="center",
            className="line-graph")

footer = dbc.Row(
    dbc.Col(
        [
            html.P(
                [
                    "Special thanks to ",
                    html.A("Bovada", href="https://www.bovada.lv", target="_blank"),
                    " for the data."
                ]
            ),
            html.P("© 2024 Greg Adams"),
            html.P(["Follow me on Twitter:  ", html.A("@AGregRoll", href="https://x.com/AGregRoll", target="_blank")]),
            html.P(["Follow me on Github:  ", html.A("@GreggRoll", href="https://github.com/GreggRoll", target="_blank")]),
        ],
        className="footer-text"
    ),
    className="footer"
)

def get_main_layout():
    layout = html.Div([
        interval, 
        header_row,
        dbc.Row([
            dbc.Col([
                # Assuming picks_graph is a component for top picks
                picks_graph
            ], width=8),  # Half width of the row for top picks
            dbc.Col([
                chat_layout
            ], width=4),  # Half width of the row for chat
        ]),
        dbc.Row([
            table, points_graph, odds_graph
        ]),
        footer
    ])
    return layout