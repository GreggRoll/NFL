from app import app
from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc

# layouts.py
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

def get_main_layout():
    return dbc.Container([
        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # 5 mins in milliseconds
            n_intervals=0
        ),
        dbc.Row([html.H1("Bovada odds table", style={'textAlign': 'center'})],
            className='header-bar'),
        dbc.Row([
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
                        'backgroundColor': 'rgb(210, 210, 210)', 
                        'color': 'black', 
                        'fontWeight': 'bold'
                    },
                    style_table={'overflowX': 'auto'},  # Enable horizontal scroll
                ),
                width=12
            )
        ], className="data-table"),
        dbc.Row(dcc.Graph(id='line-graph'),
            justify="center",
            className="line-graph")
    ])
