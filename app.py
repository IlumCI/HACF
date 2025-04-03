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
        response = data.get('response', '')
        metadata = data.get('metadata', None)
        
        # Store conversation history in session
        if 'conversation' not in session:
            session['conversation'] = []
        
        # Add user message to conversation history
        session['conversation'].append({
            "role": "user", 
            "content": message
        })
        
        # Add assistant response to conversation history
        session['conversation'].append({
            "role": "assistant", 
            "content": response,
            "metadata": metadata
        })
        
        # In a real implementation with server-side processing, we could call different AI models here
        # based on the HACF layer required. For now, we're using Puter.js on the client side.
        
        logger.debug(f"Processed message through HACF framework. Metadata: {metadata}")
        
        return jsonify({
            "status": "success",
            "message": "Message received and processed"
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
