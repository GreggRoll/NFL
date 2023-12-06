# app.py
from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server  # Expose the server variable for deployment
