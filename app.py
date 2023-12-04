# app.py
from dash import Dash

app = Dash(__name__)
server = app.server  # Expose the server variable for deployment
