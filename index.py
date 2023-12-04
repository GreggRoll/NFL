# index.py
from app import app
from layouts import get_main_layout
import callbacks  # This will register the callbacks

app.layout = get_main_layout()

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')