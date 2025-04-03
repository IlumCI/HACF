import os
import logging
import json
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from io import BytesIO
import zipfile

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

@app.route('/dashboard')
def dashboard():
    # Fetch all projects
    projects = models.Project.query.all()
    return render_template('dashboard.html', projects=projects)

@app.route('/analytics')
def analytics():
    # Get basic stats
    projects = models.Project.query.all()
    completed_projects = models.Project.query.filter_by(layer5_complete=True).count()
    
    stats = {
        'total_projects': len(projects),
        'active_projects': len(projects) - completed_projects,
        'completed_projects': completed_projects,
        'completion_rate': int((completed_projects / len(projects)) * 100) if projects else 0,
        'files_generated': 0,  # Would calculate from actual files
        'avg_files_per_project': 0,  # Would calculate from actual files
        'total_interactions': models.Message.query.count()
    }
    
    # Layer statistics
    layer_stats = {
        'layer1': {'avg_time': 2, 'success_rate': 95, 'common_issue': 'Incomplete specifications'},
        'layer2': {'avg_time': 4, 'success_rate': 88, 'common_issue': 'Incompatible technologies'},
        'layer3': {'avg_time': 10, 'success_rate': 75, 'common_issue': 'Integration errors'},
        'layer4': {'avg_time': 6, 'success_rate': 80, 'common_issue': 'Security vulnerabilities'},
        'layer5': {'avg_time': 1, 'success_rate': 98, 'common_issue': 'File formatting issues'}
    }
    
    # Project timeline data
    timeline_data = {
        'dates': json.dumps(["Apr 1", "Apr 2", "Apr 3", "Apr 4", "Apr 5", "Apr 6", "Apr 7"]),
        'started': json.dumps([3, 2, 5, 1, 4, 2, 3]),
        'completed': json.dumps([1, 0, 2, 1, 1, 3, 2])
    }
    
    # Technology usage data
    tech_data = {
        'labels': json.dumps(["React", "Flask", "Node.js", "PostgreSQL", "MongoDB", "Express", "Vue.js", "Django"]),
        'counts': json.dumps([8, 12, 7, 9, 5, 6, 4, 3])
    }
    
    # Recent activity
    recent_activity = [
        {
            'action': 'Project Completed',
            'timestamp': '10 minutes ago',
            'description': 'Task Management Application successfully completed all HACF layers',
            'project': 'Task Management App'
        },
        {
            'action': 'Layer 3 Processed',
            'timestamp': '25 minutes ago',
            'description': 'Development & Execution layer completed for E-commerce Website',
            'project': 'E-commerce Website'
        },
        {
            'action': 'New Project Created',
            'timestamp': '1 hour ago',
            'description': 'Started a new project: Blog Platform',
            'project': 'Blog Platform'
        },
        {
            'action': 'Code Optimized',
            'timestamp': '2 hours ago',
            'description': 'Security vulnerabilities fixed in authentication module',
            'project': 'Weather App'
        },
        {
            'action': 'Files Generated',
            'timestamp': '3 hours ago',
            'description': '15 files generated and exported as ZIP',
            'project': 'Portfolio Website'
        }
    ]
    
    # Popular technologies
    popular_technologies = [
        {'name': 'Flask', 'count': 12},
        {'name': 'PostgreSQL', 'count': 9},
        {'name': 'React', 'count': 8},
        {'name': 'Node.js', 'count': 7},
        {'name': 'Express', 'count': 6},
        {'name': 'MongoDB', 'count': 5},
        {'name': 'Vue.js', 'count': 4},
        {'name': 'Django', 'count': 3}
    ]
    
    return render_template(
        'analytics.html', 
        stats=stats, 
        layer_stats=layer_stats,
        timeline_data=timeline_data,
        tech_data=tech_data,
        recent_activity=recent_activity,
        popular_technologies=popular_technologies
    )

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Determine the active layer
    active_layer = 1
    if project.layer1_complete and not project.layer2_complete:
        active_layer = 2
    elif project.layer2_complete and not project.layer3_complete:
        active_layer = 3
    elif project.layer3_complete and not project.layer4_complete:
        active_layer = 4
    elif project.layer4_complete and not project.layer5_complete:
        active_layer = 5
    elif project.layer5_complete:
        active_layer = 5
    
    # Parse files if they exist
    if project.files:
        try:
            project.files_list = json.loads(project.files)
        except:
            project.files_list = []
    else:
        project.files_list = []
    
    return render_template('project_detail.html', project=project, active_layer=active_layer)

@app.route('/create_project', methods=['POST'])
def create_project():
    # Handle both form data and JSON data
    if request.is_json:
        data = request.json
        title = data.get('title')
        description = data.get('description', '')
        project_type = data.get('project_type', 'web-app')
        tech_stack = data.get('tech_stack', 'auto')
        priority = data.get('priority', 'quality')
    else:
        title = request.form.get('title')
        description = request.form.get('description', '')
        project_type = request.form.get('project_type', 'web-app')
        tech_stack = request.form.get('tech_stack', 'auto')
        priority = request.form.get('priority', 'quality')
    
    if not title:
        if request.is_json:
            return jsonify({
                "status": "error",
                "message": "Project title is required"
            }), 400
        else:
            # Flash an error message
            return redirect(url_for('dashboard'))
    
    # Create new project
    project = models.Project(
        title=title,
        description=description,
        created_at=datetime.datetime.utcnow()
    )
    
    # Store project type and tech stack preferences in task_definition as JSON
    project_metadata = {
        "project_type": project_type,
        "tech_stack": tech_stack,
        "priority": priority
    }
    project.task_definition = json.dumps(project_metadata)
    
    db.session.add(project)
    db.session.commit()
    
    if request.is_json:
        return jsonify({
            "status": "success",
            "message": "Project created successfully",
            "project_id": project.id
        })
    else:
        return redirect(url_for('project_detail', project_id=project.id))

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        project.title = request.form.get('title')
        project.description = request.form.get('description', '')
        
        db.session.commit()
        return redirect(url_for('project_detail', project_id=project.id))
    
    return render_template('edit_project.html', project=project)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    db.session.delete(project)
    db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/process_layer/<int:project_id>/<int:layer_num>', methods=['POST'])
def process_layer(project_id, layer_num):
    project = models.Project.query.get_or_404(project_id)
    data = request.json or {}
    input_data = data.get('input', '')
    
    try:
        # Process through Puter.js HACF layer (this would be done client-side in reality)
        # Here we're just simulating the layer processing
        
        output = f"Processed layer {layer_num} for project {project_id}"
        
        # Update project based on layer
        if layer_num == 1:
            project.task_definition = input_data
            project.layer1_complete = True
        elif layer_num == 2:
            project.refined_structure = input_data
            project.layer2_complete = True
        elif layer_num == 3:
            project.development_code = input_data
            project.layer3_complete = True
        elif layer_num == 4:
            project.optimized_code = input_data
            project.layer4_complete = True
        elif layer_num == 5:
            # For final layer, we'd generate files
            files = [
                {"name": "index.html", "content": "<html><body><h1>Hello World</h1></body></html>"},
                {"name": "style.css", "content": "body { font-family: Arial; }"},
                {"name": "script.js", "content": "console.log('Hello from HACF!');"}
            ]
            project.files = json.dumps(files)
            project.layer5_complete = True
            project.completed_at = datetime.datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Layer {layer_num} processed successfully",
            "output": output
        })
    except Exception as e:
        logger.error(f"Error processing layer {layer_num} for project {project_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/project_file/<int:project_id>/<path:filename>')
def project_file(project_id, filename):
    project = models.Project.query.get_or_404(project_id)
    
    if not project.files:
        return "File not found", 404
    
    try:
        files = json.loads(project.files)
        for file in files:
            if file['name'] == filename:
                return file['content']
        
        return "File not found", 404
    except:
        return "Error retrieving file", 500

@app.route('/project_zip/<int:project_id>')
def project_zip(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    if not project.files:
        return "No files to download", 404
    
    try:
        # Create a ZIP file in memory
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            files = json.loads(project.files)
            for file in files:
                zf.writestr(file['name'], file['content'])
        
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{project.title.replace(' ', '_')}_HACF_Project.zip"
        )
    except Exception as e:
        logger.error(f"Error creating ZIP file for project {project_id}: {str(e)}")
        return "Error creating ZIP file", 500

@app.route('/project_json/<int:project_id>')
def project_json(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Create a JSON representation of the project
    project_data = {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "task_definition": project.task_definition,
        "refined_structure": project.refined_structure,
        "development_code": project.development_code,
        "optimized_code": project.optimized_code,
        "files": json.loads(project.files) if project.files else [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "progress": project.progress
    }
    
    return jsonify(project_data)

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
