import os
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "hacf-secret-key")

# Configure PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Fix for SQLAlchemy 1.4+ compatibility with Postgres URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    logger.info(f"Using database URL: {urlparse(database_url)._replace(netloc=f'****:****@{urlparse(database_url).hostname}')}")
else:
    logger.warning("DATABASE_URL environment variable not set, using SQLite.")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chatbot.db"

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
        user_message = data.get('message', '')
        bot_response = data.get('response', '')
        
        # Store conversation history in session
        if 'conversation' not in session:
            session['conversation'] = []
        
        # Add user message to conversation history
        session['conversation'].append({"role": "user", "content": user_message})
        
        # If we have a bot response, store that too
        if bot_response:
            session['conversation'].append({"role": "assistant", "content": bot_response})
        
        # Store in database if user is logged in
        try:
            # Get the current conversation or create a new one
            from models import Conversation, Message
            
            # This would reference a real user ID if we had authentication
            # For now, we'll use anonymous conversations
            current_conversation = None
            
            # Check if there's an active conversation ID in the session
            if 'conversation_id' in session:
                current_conversation = Conversation.query.get(session['conversation_id'])
            
            # If no active conversation, create a new one
            if current_conversation is None:
                current_conversation = Conversation(user_id=None)
                db.session.add(current_conversation)
                db.session.commit()
                session['conversation_id'] = current_conversation.id
            
            # Add user message to the database
            user_msg = Message(
                conversation_id=current_conversation.id,
                content=user_message,
                is_user=True
            )
            db.session.add(user_msg)
            
            # Add bot response to the database if present
            if bot_response:
                bot_msg = Message(
                    conversation_id=current_conversation.id,
                    content=bot_response,
                    is_user=False
                )
                db.session.add(bot_msg)
            
            db.session.commit()
            
        except Exception as db_error:
            logger.warning(f"Failed to store message in database: {str(db_error)}")
            # Continue without storing in the database
            pass
        
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

# HACF API Endpoints
@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all HACF projects"""
    try:
        from models import HACFProject
        projects = HACFProject.query.all()
        return jsonify({
            "status": "success",
            "projects": [project.to_dict() for project in projects]
        })
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new HACF project"""
    try:
        data = request.json
        from models import HACFProject
        
        project = HACFProject(
            title=data.get('title', 'Untitled Project'),
            description=data.get('description', '')
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "project": project.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific HACF project"""
    try:
        from models import HACFProject
        project = HACFProject.query.get_or_404(project_id)
        return jsonify({
            "status": "success",
            "project": project.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/projects/<int:project_id>/stages', methods=['POST'])
def add_project_stage(project_id):
    """Add a stage to an HACF project"""
    try:
        data = request.json
        from models import HACFProject, HACFStage
        
        project = HACFProject.query.get_or_404(project_id)
        
        stage = HACFStage(
            project_id=project.id,
            stage_type=data.get('stage_type'),
            content=data.get('content'),
            completed=data.get('completed', False)
        )
        
        db.session.add(stage)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "stage": stage.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding stage to project {project_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/projects/<int:project_id>/files', methods=['POST'])
def add_project_file(project_id):
    """Add a file to an HACF project"""
    try:
        data = request.json
        from models import HACFProject, ProjectFile
        
        project = HACFProject.query.get_or_404(project_id)
        
        file = ProjectFile(
            project_id=project.id,
            filename=data.get('filename'),
            content=data.get('content')
        )
        
        db.session.add(file)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "file": file.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding file to project {project_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
