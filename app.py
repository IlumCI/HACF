import os
import logging
import json
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
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
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure the PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize SQLAlchemy
db.init_app(app)

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Make sure to import the models here
    import models
    db.create_all()
    
    # Create default admin user for testing purposes
    # Note: This is only for testing and should be changed in production
    default_admin_email = "admin@hacf.com"
    if not models.User.query.filter_by(email=default_admin_email).first():
        logger.info("Creating default admin user for testing")
        admin_user = models.User(
            username="admin",
            email=default_admin_email,
            role="admin"
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        db.session.commit()
        logger.info("Default admin user created successfully")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill out all fields.', 'danger')
            return render_template('login.html')
        
        user = models.User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            # Redirect to requested page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            flash('Please fill out all fields.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        # Check if email or username already exists
        if models.User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        if models.User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html')
        
        # Create new user
        user = models.User(username=username, email=email)
        user.set_password(password)
        
        # First user gets admin privileges
        if models.User.query.count() == 0:
            user.role = 'admin'
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    # Get teams the user is a member of
    teams = models.TeamMember.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', teams=teams)

@app.route('/advanced_hacf')
@login_required
def advanced_hacf():
    """
    Display information about the advanced HACF framework including:
    - Adaptive Layer Sequencing
    - Cross-Layer Memory
    - Proprietary Evaluation System
    - Domain Specialization
    - Human-AI Collaboration Checkpoints
    """
    # Get available domains for the domain specialization section
    import advanced_hacf
    domains = advanced_hacf.DomainSpecializationEngine.get_available_domains()
    
    # Get available networks for the adaptive sequencing section
    networks = {
        'standard': 'Linear progression through layers',
        'agile': 'Flexible layer sequence with iterative development',
        'research': 'Research-oriented with multiple exploration paths',
        'security_focused': 'Security-focused with enhanced validation',
        'iterative_development': 'Rapid iteration on development and optimization'
    }
    
    # Memory types for the cross-layer memory section
    memory_types = advanced_hacf.CrossLayerMemory.MEMORY_TYPES
    
    # Evaluation dimensions for the proprietary evaluation section
    evaluation_dimensions = advanced_hacf.ProprietaryEvaluation.EVALUATION_DIMENSIONS
    
    # Checkpoint types for the human-AI collaboration section
    checkpoint_types = advanced_hacf.HumanAICollaborationManager.CHECKPOINT_TYPES
    
    return render_template(
        'advanced_hacf.html',
        domains=domains,
        networks=networks,
        memory_types=memory_types,
        evaluation_dimensions=evaluation_dimensions,
        checkpoint_types=checkpoint_types
    )

@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch all projects for the current user
    if current_user.role == 'admin':
        # Admins can see all projects
        projects = models.Project.query.all()
    else:
        # Regular users only see their own projects
        projects = models.Project.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', projects=projects)

@app.route('/analytics')
@login_required
def analytics():
    # Restrict analytics to admins and managers
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access analytics.', 'danger')
        return redirect(url_for('dashboard'))
    
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
@login_required
def project_detail(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to view this project
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        flash('You do not have permission to view this project.', 'danger')
        return redirect(url_for('dashboard'))
    
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
@login_required
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
    
    # Create new project and associate with current user
    project = models.Project(
        title=title,
        description=description,
        user_id=current_user.id,
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
@login_required
def edit_project(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to edit this project
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        flash('You do not have permission to edit this project.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        project.title = request.form.get('title')
        project.description = request.form.get('description', '')
        
        db.session.commit()
        return redirect(url_for('project_detail', project_id=project.id))
    
    return render_template('edit_project.html', project=project)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to delete this project
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        flash('You do not have permission to delete this project.', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Project deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/process_layer/<int:project_id>/<int:layer_num>', methods=['POST'])
@login_required
def process_layer(project_id, layer_num):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to process this project
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "message": "You do not have permission to process this project."
        }), 403
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
@login_required
def project_file(project_id, filename):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to access this project's files
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        return "Access denied", 403
    
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
@login_required
def project_zip(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to download this project's files
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        return "Access denied", 403
    
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
@login_required
def project_json(project_id):
    project = models.Project.query.get_or_404(project_id)
    
    # Check if user is authorized to access this project's data
    if not current_user.role == 'admin' and project.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "message": "Access denied"
        }), 403
    
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
@login_required
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
@login_required
def get_conversation():
    conversation = session.get('conversation', [])
    return jsonify({
        "conversation": conversation
    })

@app.route('/clear_conversation', methods=['POST'])
@login_required
def clear_conversation():
    if 'conversation' in session:
        session.pop('conversation')
    return jsonify({
        "status": "success",
        "message": "Conversation cleared"
    })

# Profile Management Routes
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        # Update user profile information
        current_user.profile_picture = request.form.get('profile_picture', current_user.profile_picture)
        current_user.bio = request.form.get('bio', current_user.bio)
        current_user.job_title = request.form.get('job_title', current_user.job_title)
        current_user.company = request.form.get('company', current_user.company)
        current_user.website = request.form.get('website', current_user.website)
        current_user.location = request.form.get('location', current_user.location)
        
        db.session.commit()
        
        flash('Profile updated successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error updating profile: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    try:
        # Update user preferences
        current_user.theme_preference = request.form.get('theme_preference', 'dark')
        current_user.email_notifications = 'email_notifications' in request.form
        
        # Handle preferred technologies (comes as a list from form)
        tech_list = request.form.getlist('preferred_technologies[]')
        if tech_list:
            current_user.preferred_technologies = json.dumps(tech_list)
        
        db.session.commit()
        
        flash('Preferences updated successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error updating preferences: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('profile'))
        
        # Validate new password match
        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('profile'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error changing password: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/generate_api_key', methods=['POST'])
@login_required
def generate_api_key():
    try:
        import secrets
        # Generate a random API key
        api_key = secrets.token_hex(32)
        
        current_user.api_key = api_key
        db.session.commit()
        
        flash('API key generated successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error generating API key: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/regenerate_api_key', methods=['POST'])
@login_required
def regenerate_api_key():
    try:
        import secrets
        # Generate a new random API key
        api_key = secrets.token_hex(32)
        
        current_user.api_key = api_key
        db.session.commit()
        
        flash('API key regenerated successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error regenerating API key: {str(e)}")
    
    return redirect(url_for('profile'))

# Team Management Routes
@app.route('/create_team', methods=['POST'])
@login_required
def create_team():
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        avatar = request.form.get('avatar', '')
        
        if not name:
            flash('Team name is required.', 'danger')
            return redirect(url_for('profile'))
        
        # Create new team
        team = models.Team(
            name=name,
            description=description,
            avatar=avatar,
            owner_id=current_user.id
        )
        db.session.add(team)
        db.session.flush()  # Flush to get the team ID
        
        # Add current user as owner
        team_member = models.TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role='owner'
        )
        db.session.add(team_member)
        
        db.session.commit()
        
        flash(f'Team "{name}" created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error creating team: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/team/<int:team_id>')
@login_required
def team_detail(team_id):
    # Get team information
    team = models.Team.query.get_or_404(team_id)
    
    # Check if user is a member of the team
    team_member = models.TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    
    if not team_member and team.owner_id != current_user.id and current_user.role != 'admin':
        flash('You are not a member of this team.', 'danger')
        return redirect(url_for('profile'))
    
    # Get team members
    members = models.TeamMember.query.filter_by(team_id=team_id).all()
    
    # Get team projects
    team_projects = models.TeamProject.query.filter_by(team_id=team_id).all()
    
    return render_template('team_detail.html', team=team, members=members, team_projects=team_projects, current_member=team_member)

@app.route('/team/<int:team_id>/invite', methods=['POST'])
@login_required
def invite_team_member(team_id):
    team = models.Team.query.get_or_404(team_id)
    
    # Check if user is authorized to invite members
    team_member = models.TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    
    if not team_member or team_member.role not in ['owner', 'admin']:
        flash('You do not have permission to invite members to this team.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    email = request.form.get('email')
    role = request.form.get('role', 'member')
    
    if not email:
        flash('Email is required.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Find user by email
    user = models.User.query.filter_by(email=email).first()
    
    if not user:
        flash(f'No user found with email {email}.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Check if user is already a member
    existing_member = models.TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first()
    
    if existing_member:
        flash(f'User {user.username} is already a member of this team.', 'warning')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Add user to team
    new_member = models.TeamMember(
        team_id=team_id,
        user_id=user.id,
        role=role
    )
    db.session.add(new_member)
    db.session.commit()
    
    flash(f'User {user.username} invited to the team successfully.', 'success')
    return redirect(url_for('team_detail', team_id=team_id))

@app.route('/team/<int:team_id>/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_team_member(team_id, user_id):
    team = models.Team.query.get_or_404(team_id)
    
    # Check if user is authorized to remove members
    team_member = models.TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    
    if not team_member or team_member.role not in ['owner', 'admin']:
        flash('You do not have permission to remove members from this team.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Cannot remove the owner
    if user_id == team.owner_id:
        flash('Cannot remove the team owner.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Find the member to remove
    member_to_remove = models.TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
    
    if not member_to_remove:
        flash('Member not found.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    db.session.delete(member_to_remove)
    db.session.commit()
    
    flash('Member removed successfully.', 'success')
    return redirect(url_for('team_detail', team_id=team_id))

# Project Template Routes
@app.route('/templates')
@login_required
def project_templates():
    # Get public templates and user's own templates
    public_templates = models.ProjectTemplate.query.filter_by(is_public=True).all()
    user_templates = models.ProjectTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template('templates.html', public_templates=public_templates, user_templates=user_templates)

@app.route('/create_template', methods=['POST'])
@login_required
def create_template():
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        configuration = request.form.get('configuration', '{}')
        is_public = 'is_public' in request.form
        category = request.form.get('category', 'general')
        tags = request.form.get('tags', '')
        
        if not name:
            flash('Template name is required.', 'danger')
            return redirect(url_for('project_templates'))
        
        # Create new template
        template = models.ProjectTemplate(
            name=name,
            description=description,
            configuration=configuration,
            is_public=is_public,
            category=category,
            tags=json.dumps(tags.split(',')) if tags else '[]',
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        
        flash(f'Template "{name}" created successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error creating template: {str(e)}")
    
    return redirect(url_for('project_templates'))

@app.route('/use_template/<int:template_id>', methods=['POST'])
@login_required
def use_template(template_id):
    try:
        template = models.ProjectTemplate.query.get_or_404(template_id)
        
        # Check if user has access to this template
        if not template.is_public and template.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have access to this template.', 'danger')
            return redirect(url_for('project_templates'))
        
        # Create new project from template
        project_title = request.form.get('title', template.name)
        project_description = request.form.get('description', template.description)
        
        project = models.Project(
            title=project_title,
            description=project_description,
            user_id=current_user.id,
            created_at=datetime.datetime.utcnow()
        )
        
        # Set task definition from template configuration
        project.task_definition = template.configuration
        
        db.session.add(project)
        
        # Increment the template usage count
        template.use_count += 1
        
        db.session.commit()
        
        flash(f'Project created from template "{template.name}".', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error using template: {str(e)}")
    
    return redirect(url_for('project_templates'))

@app.route('/edit_template/<int:template_id>', methods=['POST'])
@login_required
def edit_template(template_id):
    try:
        template = models.ProjectTemplate.query.get_or_404(template_id)
        
        # Check if user is authorized to edit this template
        if template.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have permission to edit this template.', 'danger')
            return redirect(url_for('project_templates'))
        
        template.name = request.form.get('name')
        template.description = request.form.get('description', '')
        template.configuration = request.form.get('configuration', '{}')
        template.is_public = 'is_public' in request.form
        template.category = request.form.get('category', 'general')
        
        # Handle tags
        tags = request.form.get('tags', '')
        template.tags = json.dumps(tags.split(',')) if tags else '[]'
        
        db.session.commit()
        
        flash(f'Template "{template.name}" updated successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error updating template: {str(e)}")
    
    return redirect(url_for('project_templates'))

@app.route('/delete_template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    try:
        template = models.ProjectTemplate.query.get_or_404(template_id)
        
        # Check if user is authorized to delete this template
        if template.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have permission to delete this template.', 'danger')
            return redirect(url_for('project_templates'))
        
        db.session.delete(template)
        db.session.commit()
        
        flash('Template deleted successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        logger.error(f"Error deleting template: {str(e)}")
    
    return redirect(url_for('project_templates'))

@app.route('/team/<int:team_id>/add_project', methods=['POST'])
@login_required
def add_project_to_team(team_id):
    team = models.Team.query.get_or_404(team_id)
    
    # Check if user is a member of the team
    team_member = models.TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    
    if not team_member:
        flash('You are not a member of this team.', 'danger')
        return redirect(url_for('profile'))
    
    project_id = request.form.get('project_id')
    
    if not project_id:
        flash('Project ID is required.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Verify project exists and user owns it
    project = models.Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to share this project.', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Check if project is already added to the team
    existing_team_project = models.TeamProject.query.filter_by(team_id=team_id, project_id=project_id).first()
    
    if existing_team_project:
        flash('This project is already part of the team.', 'warning')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Add project to team
    team_project = models.TeamProject(
        team_id=team_id,
        project_id=project_id
    )
    db.session.add(team_project)
    db.session.commit()
    
    flash('Project added to team successfully.', 'success')
    return redirect(url_for('team_detail', team_id=team_id))

# Import and register API blueprint
try:
    from api import api as api_blueprint
    app.register_blueprint(api_blueprint)
    logger.info("API Blueprint registered successfully")
except ImportError as e:
    logger.error(f"Error importing API blueprint: {str(e)}")

# Import and register Google OAuth blueprint
try:
    from google_auth import google_auth as google_auth_blueprint
    app.register_blueprint(google_auth_blueprint)
    logger.info("Google Auth Blueprint registered successfully")
except ImportError as e:
    logger.error(f"Error importing Google Auth blueprint: {str(e)}")

# Import and register SSO blueprint
try:
    from sso import sso as sso_blueprint
    app.register_blueprint(sso_blueprint)
    logger.info("SSO Blueprint registered successfully")
except ImportError as e:
    logger.error(f"Error importing SSO blueprint: {str(e)}")

# Add SSO login data to the login context
@app.context_processor
def inject_sso_providers():
    try:
        from sso import get_available_sso_providers
        return {'sso_providers': get_available_sso_providers()}
    except ImportError:
        return {'sso_providers': []}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
