import os
from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # socketio.run (y no app.run) para que funcionen los WebSockets
    socketio.run(app, debug=os.getenv("FLASK_DEBUG", "1") == "1")
