import os
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure the SQLite database (can be replaced with proper database in production)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here
    import models
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        # Store conversation history in session
        if 'conversation' not in session:
            session['conversation'] = []
        
        # Add user message to conversation history
        session['conversation'].append({"role": "user", "content": message})
        
        # In a real implementation, this would call Puter.js API
        # For now, we'll simulate this on the frontend since Puter.js is client-side
        
        return jsonify({
            "status": "success",
            "message": "Message received"
        })
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    conversation = session.get('conversation', [])
    return jsonify({
        "conversation": conversation
    })

@app.route('/clear_conversation', methods=['POST'])
def clear_conversation():
    if 'conversation' in session:
        session.pop('conversation')
    return jsonify({
        "status": "success",
        "message": "Conversation cleared"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
