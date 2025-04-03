import os
import json
import uuid
import hmac
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, g, abort, current_app
from flask_login import current_user

from models import User, Project, ProjectTemplate, Team, TeamMember, ProjectVersion
from models import ApiClient, ApiToken, Webhook, WebhookEvent, Integration
from app import db

# Configure logging
logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api/v1')

# API Authentication decorators
def require_api_key(f):
    """Decorator to require API key for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key is required"}), 401
        
        # Verify API key
        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Check if user has exceeded API quota
        if user.api_usage_count >= user.api_quota:
            return jsonify({"error": "API quota exceeded"}), 429
        
        # Increment API usage counter
        user.api_usage_count += 1
        db.session.commit()
        
        # Store user in g for access in the route
        g.user = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_oauth_token(f):
    """Decorator to require OAuth token for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Bearer token is required"}), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        api_token = ApiToken.query.filter_by(access_token=token, is_revoked=False).first()
        if not api_token:
            return jsonify({"error": "Invalid or revoked token"}), 401
        
        # Check if token is expired
        if api_token.is_expired:
            return jsonify({"error": "Token has expired"}), 401
        
        # Store user and token in g for access in the route
        g.user = User.query.get(api_token.user_id)
        g.token = api_token
        return f(*args, **kwargs)
    
    return decorated_function

# OAuth endpoints
@api.route('/oauth/authorize', methods=['GET'])
def authorize():
    """OAuth 2.0 authorization endpoint"""
    # Required parameters
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    scope = request.args.get('scope', '')
    state = request.args.get('state')  # Optional but recommended
    
    # Validate client and redirect URI
    client = ApiClient.query.filter_by(client_id=client_id, is_active=True).first()
    if not client:
        return jsonify({"error": "Invalid client"}), 400
    
    # TODO: In production, this should redirect to a user consent page
    # For now, auto-approve for the current user if logged in
    if not current_user.is_authenticated:
        return jsonify({"error": "User must be logged in"}), 401
    
    # Generate authorization code
    code = secrets.token_urlsafe(32)
    client.authorization_code = code
    client.code_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    # Redirect to client with code
    redirect_params = f"code={code}"
    if state:
        redirect_params += f"&state={state}"
    
    # In a real implementation, we would redirect; for API testing, return the code
    return jsonify({
        "redirect_uri": f"{redirect_uri}?{redirect_params}",
        "code": code
    })

@api.route('/oauth/token', methods=['POST'])
def token():
    """OAuth 2.0 token endpoint"""
    # Validate grant type
    grant_type = request.form.get('grant_type')
    if grant_type not in ['authorization_code', 'refresh_token']:
        return jsonify({"error": "Unsupported grant type"}), 400
    
    if grant_type == 'authorization_code':
        # Authorization code flow
        client_id = request.form.get('client_id')
        client_secret = request.form.get('client_secret')
        code = request.form.get('code')
        redirect_uri = request.form.get('redirect_uri')
        
        # Validate client credentials
        client = ApiClient.query.filter_by(
            client_id=client_id, 
            client_secret=client_secret,
            is_active=True
        ).first()
        
        if not client or client.authorization_code != code:
            return jsonify({"error": "Invalid client credentials or code"}), 401
        
        # Check if code is expired
        if not client.code_expires_at or client.code_expires_at < datetime.utcnow():
            return jsonify({"error": "Authorization code has expired"}), 401
        
        # Generate tokens
        access_token = secrets.token_urlsafe(64)
        refresh_token = secrets.token_urlsafe(64)
        expires_in = 3600  # 1 hour
        
        # Create token record
        api_token = ApiToken(
            user_id=client.user_id,
            api_client_id=client.id,
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=client.allowed_scopes,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
        )
        
        # Clear authorization code
        client.authorization_code = None
        client.code_expires_at = None
        client.last_used_at = datetime.utcnow()
        
        db.session.add(api_token)
        db.session.commit()
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": refresh_token,
            "scope": client.allowed_scopes
        })
    
    elif grant_type == 'refresh_token':
        # Refresh token flow
        client_id = request.form.get('client_id')
        client_secret = request.form.get('client_secret')
        refresh_token = request.form.get('refresh_token')
        
        # Validate client credentials
        client = ApiClient.query.filter_by(
            client_id=client_id, 
            client_secret=client_secret,
            is_active=True
        ).first()
        
        if not client:
            return jsonify({"error": "Invalid client credentials"}), 401
        
        # Find token
        token = ApiToken.query.filter_by(
            refresh_token=refresh_token,
            api_client_id=client.id,
            is_revoked=False
        ).first()
        
        if not token:
            return jsonify({"error": "Invalid refresh token"}), 401
        
        # Generate new access token
        new_access_token = secrets.token_urlsafe(64)
        expires_in = 3600  # 1 hour
        
        # Update token
        token.access_token = new_access_token
        token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update client last used timestamp
        client.last_used_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": token.scopes
        })

# API Key management
@api.route('/api-keys', methods=['POST'])
@require_api_key
def generate_api_key():
    """Generate a new API key for the current user"""
    # Only allow if user doesn't already have an API key or force flag is set
    user = g.user
    force = request.json.get('force', False)
    
    if user.api_key and not force:
        return jsonify({"error": "API key already exists. Use force=true to regenerate."}), 400
    
    # Generate API key
    api_key = uuid.uuid4().hex
    user.api_key = api_key
    db.session.commit()
    
    return jsonify({
        "api_key": api_key,
        "message": "API key generated successfully"
    })

@api.route('/api-keys', methods=['GET'])
@require_api_key
def get_api_key_info():
    """Get information about the current API key"""
    user = g.user
    
    return jsonify({
        "user_id": user.id,
        "username": user.username,
        "quota": user.api_quota,
        "usage": user.api_usage_count,
        "remaining": max(0, user.api_quota - user.api_usage_count)
    })

# Webhook management
@api.route('/webhooks', methods=['GET'])
@require_api_key
def list_webhooks():
    """List all webhooks for the current user"""
    user = g.user
    webhooks = Webhook.query.filter_by(user_id=user.id).all()
    
    result = []
    for webhook in webhooks:
        result.append({
            "id": webhook.id,
            "name": webhook.name,
            "url": webhook.url,
            "events": json.loads(webhook.events),
            "is_active": webhook.is_active,
            "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
            "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
            "failure_count": webhook.failure_count
        })
    
    return jsonify({"webhooks": result})

@api.route('/webhooks', methods=['POST'])
@require_api_key
def create_webhook():
    """Create a new webhook"""
    user = g.user
    data = request.json
    
    # Validate required fields
    required_fields = ['name', 'url', 'events']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Ensure events is a list
    events = data.get('events', [])
    if not isinstance(events, list):
        return jsonify({"error": "Events must be a list"}), 400
    
    # Create webhook
    webhook = Webhook(
        user_id=user.id,
        name=data['name'],
        url=data['url'],
        events=json.dumps(events),
        description=data.get('description', ''),
        secret=data.get('secret', secrets.token_hex(32)),
        is_active=data.get('is_active', True)
    )
    
    db.session.add(webhook)
    db.session.commit()
    
    return jsonify({
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": events,
        "is_active": webhook.is_active,
        "secret": webhook.secret,
        "message": "Webhook created successfully"
    }), 201

@api.route('/webhooks/<int:webhook_id>', methods=['GET'])
@require_api_key
def get_webhook(webhook_id):
    """Get webhook details"""
    user = g.user
    webhook = Webhook.query.filter_by(id=webhook_id, user_id=user.id).first()
    
    if not webhook:
        return jsonify({"error": "Webhook not found"}), 404
    
    events = []
    try:
        events = json.loads(webhook.events)
    except:
        pass
    
    return jsonify({
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": events,
        "description": webhook.description,
        "is_active": webhook.is_active,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
        "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
        "failure_count": webhook.failure_count
    })

@api.route('/webhooks/<int:webhook_id>', methods=['PUT'])
@require_api_key
def update_webhook(webhook_id):
    """Update webhook details"""
    user = g.user
    webhook = Webhook.query.filter_by(id=webhook_id, user_id=user.id).first()
    
    if not webhook:
        return jsonify({"error": "Webhook not found"}), 404
    
    data = request.json
    
    # Update webhook fields
    if 'name' in data:
        webhook.name = data['name']
    
    if 'url' in data:
        webhook.url = data['url']
    
    if 'description' in data:
        webhook.description = data['description']
    
    if 'events' in data:
        # Ensure events is a list
        events = data['events']
        if not isinstance(events, list):
            return jsonify({"error": "Events must be a list"}), 400
        webhook.events = json.dumps(events)
    
    if 'is_active' in data:
        webhook.is_active = bool(data['is_active'])
    
    if 'secret' in data:
        webhook.secret = data['secret']
    
    db.session.commit()
    
    return jsonify({
        "id": webhook.id,
        "message": "Webhook updated successfully"
    })

@api.route('/webhooks/<int:webhook_id>', methods=['DELETE'])
@require_api_key
def delete_webhook(webhook_id):
    """Delete a webhook"""
    user = g.user
    webhook = Webhook.query.filter_by(id=webhook_id, user_id=user.id).first()
    
    if not webhook:
        return jsonify({"error": "Webhook not found"}), 404
    
    db.session.delete(webhook)
    db.session.commit()
    
    return jsonify({
        "message": "Webhook deleted successfully"
    })

# Helper function to trigger webhooks
def trigger_webhook(user_id, event_type, payload):
    """Trigger webhooks for a specific event type"""
    webhooks = Webhook.query.filter_by(user_id=user_id, is_active=True).all()
    
    for webhook in webhooks:
        try:
            events = json.loads(webhook.events)
            if event_type not in events:
                continue
            
            # Create webhook event record
            event = WebhookEvent(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=json.dumps(payload),
                status='pending'
            )
            
            db.session.add(event)
            db.session.commit()
            
            # In a production app, this would be handled by a background worker
            # For now, we'll trigger synchronously for demo purposes
            import requests
            
            # Calculate signature if secret is provided
            signature = None
            timestamp = str(int(datetime.utcnow().timestamp()))
            
            if webhook.secret:
                payload_string = json.dumps(payload)
                signature_base = f"{timestamp}.{payload_string}"
                signature = hmac.new(
                    webhook.secret.encode(),
                    signature_base.encode(),
                    hashlib.sha256
                ).hexdigest()
            
            # Send request
            headers = {
                'Content-Type': 'application/json',
                'X-HACF-Event': event_type,
                'X-HACF-Timestamp': timestamp
            }
            
            if signature:
                headers['X-HACF-Signature'] = signature
            
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=5
            )
            
            # Update event record
            event.status = 'sent' if response.ok else 'failed'
            event.response_code = response.status_code
            event.response_body = response.text
            event.processed_at = datetime.utcnow()
            
            # Update webhook stats
            webhook.last_triggered_at = datetime.utcnow()
            if not response.ok:
                webhook.failure_count += 1
            
            db.session.commit()
        
        except Exception as e:
            logger.error(f"Error triggering webhook {webhook.id}: {str(e)}")
            
            # Update webhook failure stats
            webhook.failure_count += 1
            db.session.commit()

# Project API endpoints
@api.route('/projects', methods=['GET'])
@require_api_key
def list_projects():
    """List all projects for the current user"""
    user = g.user
    projects = Project.query.filter_by(user_id=user.id).all()
    
    result = []
    for project in projects:
        result.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "progress": project.progress(),
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "completed_at": project.completed_at.isoformat() if project.completed_at else None
        })
    
    return jsonify({"projects": result})

@api.route('/projects/<int:project_id>', methods=['GET'])
@require_api_key
def get_project(project_id):
    """Get project details"""
    user = g.user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Get project versions
    versions = ProjectVersion.query.filter_by(project_id=project.id).order_by(ProjectVersion.version_number.desc()).all()
    version_list = []
    
    for version in versions:
        version_list.append({
            "version_number": version.version_number,
            "description": version.description,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "created_by": version.created_by
        })
    
    # Determine which layers are complete
    layers_complete = {
        "layer1": project.layer1_complete,
        "layer2": project.layer2_complete,
        "layer3": project.layer3_complete,
        "layer4": project.layer4_complete,
        "layer5": project.layer5_complete
    }
    
    result = {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "task_definition": project.task_definition,
        "refined_structure": project.refined_structure,
        "development_code": project.development_code,
        "optimized_code": project.optimized_code,
        "files": project.files,
        "progress": project.progress(),
        "layers_complete": layers_complete,
        "versions": version_list,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None
    }
    
    return jsonify(result)

@api.route('/projects', methods=['POST'])
@require_api_key
def create_project():
    """Create a new project"""
    user = g.user
    data = request.json
    
    # Validate required fields
    if not data.get('title'):
        return jsonify({"error": "Project title is required"}), 400
    
    # Create project
    project = Project(
        user_id=user.id,
        title=data['title'],
        description=data.get('description', ''),
        task_definition=data.get('task_definition', '')
    )
    
    db.session.add(project)
    db.session.commit()
    
    # Trigger webhook for project creation
    trigger_webhook(user.id, 'project.created', {
        "project_id": project.id,
        "title": project.title,
        "user_id": user.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "id": project.id,
        "title": project.title,
        "message": "Project created successfully"
    }), 201

@api.route('/projects/<int:project_id>', methods=['PUT'])
@require_api_key
def update_project(project_id):
    """Update project details"""
    user = g.user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    data = request.json
    
    # Update fields
    if 'title' in data:
        project.title = data['title']
    
    if 'description' in data:
        project.description = data['description']
    
    if 'task_definition' in data:
        project.task_definition = data['task_definition']
    
    if 'refined_structure' in data:
        project.refined_structure = data['refined_structure']
    
    if 'development_code' in data:
        project.development_code = data['development_code']
    
    if 'optimized_code' in data:
        project.optimized_code = data['optimized_code']
    
    if 'files' in data:
        project.files = data['files']
    
    # Update layer completion flags
    if 'layer1_complete' in data:
        project.layer1_complete = bool(data['layer1_complete'])
    
    if 'layer2_complete' in data:
        project.layer2_complete = bool(data['layer2_complete'])
    
    if 'layer3_complete' in data:
        project.layer3_complete = bool(data['layer3_complete'])
    
    if 'layer4_complete' in data:
        project.layer4_complete = bool(data['layer4_complete'])
    
    if 'layer5_complete' in data:
        project.layer5_complete = bool(data['layer5_complete'])
    
    # Check if project is completed
    if project.layer5_complete and not project.completed_at:
        project.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    # Trigger webhook for project update
    trigger_webhook(user.id, 'project.updated', {
        "project_id": project.id,
        "title": project.title,
        "user_id": user.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "id": project.id,
        "message": "Project updated successfully"
    })

@api.route('/projects/<int:project_id>', methods=['DELETE'])
@require_api_key
def delete_project(project_id):
    """Delete a project"""
    user = g.user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    db.session.delete(project)
    db.session.commit()
    
    # Trigger webhook for project deletion
    trigger_webhook(user.id, 'project.deleted', {
        "project_id": project_id,
        "user_id": user.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "message": "Project deleted successfully"
    })

# Project Templates API
@api.route('/templates', methods=['GET'])
@require_api_key
def list_templates():
    """List all project templates for the current user"""
    user = g.user
    
    # Get user's templates and public templates
    templates = ProjectTemplate.query.filter(
        (ProjectTemplate.user_id == user.id) | 
        (ProjectTemplate.is_public == True)
    ).all()
    
    result = []
    for template in templates:
        result.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "is_public": template.is_public,
            "user_id": template.user_id,
            "is_owner": template.user_id == user.id,
            "use_count": template.use_count,
            "created_at": template.created_at.isoformat() if template.created_at else None
        })
    
    return jsonify({"templates": result})

@api.route('/templates/<int:template_id>', methods=['GET'])
@require_api_key
def get_template(template_id):
    """Get template details"""
    user = g.user
    template = ProjectTemplate.query.get(template_id)
    
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    # Check access permissions
    if not template.is_public and template.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    
    # Parse tags
    tags = []
    try:
        if template.tags:
            tags = json.loads(template.tags)
    except:
        pass
    
    result = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "configuration": template.configuration,
        "category": template.category,
        "tags": tags,
        "is_public": template.is_public,
        "user_id": template.user_id,
        "is_owner": template.user_id == user.id,
        "use_count": template.use_count,
        "rating": template.rating,
        "rating_count": template.rating_count,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }
    
    return jsonify(result)

@api.route('/templates', methods=['POST'])
@require_api_key
def create_template():
    """Create a new project template"""
    user = g.user
    data = request.json
    
    # Validate required fields
    if not data.get('name') or not data.get('configuration'):
        return jsonify({"error": "Template name and configuration are required"}), 400
    
    # Handle tags
    tags = data.get('tags', [])
    if isinstance(tags, list):
        tags_json = json.dumps(tags)
    else:
        return jsonify({"error": "Tags must be a list"}), 400
    
    # Create template
    template = ProjectTemplate(
        user_id=user.id,
        name=data['name'],
        description=data.get('description', ''),
        configuration=data['configuration'],
        category=data.get('category', 'general'),
        tags=tags_json,
        is_public=data.get('is_public', False)
    )
    
    db.session.add(template)
    db.session.commit()
    
    return jsonify({
        "id": template.id,
        "name": template.name,
        "message": "Template created successfully"
    }), 201

@api.route('/templates/<int:template_id>', methods=['PUT'])
@require_api_key
def update_template(template_id):
    """Update template details"""
    user = g.user
    template = ProjectTemplate.query.get(template_id)
    
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    # Check ownership
    if template.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        template.name = data['name']
    
    if 'description' in data:
        template.description = data['description']
    
    if 'configuration' in data:
        template.configuration = data['configuration']
    
    if 'category' in data:
        template.category = data['category']
    
    if 'is_public' in data:
        template.is_public = bool(data['is_public'])
    
    # Handle tags
    if 'tags' in data:
        tags = data['tags']
        if isinstance(tags, list):
            template.tags = json.dumps(tags)
        else:
            return jsonify({"error": "Tags must be a list"}), 400
    
    db.session.commit()
    
    return jsonify({
        "id": template.id,
        "message": "Template updated successfully"
    })

@api.route('/templates/<int:template_id>', methods=['DELETE'])
@require_api_key
def delete_template(template_id):
    """Delete a template"""
    user = g.user
    template = ProjectTemplate.query.get(template_id)
    
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    # Check ownership
    if template.user_id != user.id:
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(template)
    db.session.commit()
    
    return jsonify({
        "message": "Template deleted successfully"
    })

# Team API endpoints
@api.route('/teams', methods=['GET'])
@require_api_key
def list_teams():
    """List all teams for the current user"""
    user = g.user
    
    # Get teams where user is a member
    team_memberships = TeamMember.query.filter_by(user_id=user.id).all()
    team_ids = [tm.team_id for tm in team_memberships]
    teams = Team.query.filter(Team.id.in_(team_ids)).all()
    
    result = []
    for team in teams:
        # Get user's role in this team
        team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
        role = team_member.role if team_member else None
        
        result.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "owner_id": team.owner_id,
            "is_owner": team.owner_id == user.id,
            "role": role,
            "created_at": team.created_at.isoformat() if team.created_at else None
        })
    
    return jsonify({"teams": result})

@api.route('/teams/<int:team_id>', methods=['GET'])
@require_api_key
def get_team(team_id):
    """Get team details"""
    user = g.user
    
    # Check if user is a member of the team
    team_member = TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first()
    if not team_member:
        return jsonify({"error": "Access denied"}), 403
    
    team = Team.query.get(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Get team members
    members = TeamMember.query.filter_by(team_id=team.id).all()
    member_list = []
    
    for member in members:
        member_user = User.query.get(member.user_id)
        if member_user:
            member_list.append({
                "user_id": member.user_id,
                "username": member_user.username,
                "email": member_user.email,
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None
            })
    
    # Get team projects
    team_projects = TeamProject.query.filter_by(team_id=team.id).all()
    project_list = []
    
    for tp in team_projects:
        project = Project.query.get(tp.project_id)
        if project:
            project_list.append({
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "progress": project.progress(),
                "user_id": project.user_id,
                "created_at": project.created_at.isoformat() if project.created_at else None
            })
    
    result = {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner_id": team.owner_id,
        "avatar": team.avatar,
        "is_owner": team.owner_id == user.id,
        "role": team_member.role,
        "members": member_list,
        "projects": project_list,
        "created_at": team.created_at.isoformat() if team.created_at else None,
        "updated_at": team.updated_at.isoformat() if team.updated_at else None
    }
    
    return jsonify(result)

@api.route('/teams', methods=['POST'])
@require_api_key
def create_team():
    """Create a new team"""
    user = g.user
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({"error": "Team name is required"}), 400
    
    # Create team
    team = Team(
        name=data['name'],
        description=data.get('description', ''),
        owner_id=user.id,
        avatar=data.get('avatar')
    )
    
    db.session.add(team)
    db.session.flush()  # Get team ID without committing
    
    # Add creator as owner
    team_member = TeamMember(
        team_id=team.id,
        user_id=user.id,
        role='owner'
    )
    
    db.session.add(team_member)
    db.session.commit()
    
    return jsonify({
        "id": team.id,
        "name": team.name,
        "message": "Team created successfully"
    }), 201

@api.route('/teams/<int:team_id>', methods=['PUT'])
@require_api_key
def update_team(team_id):
    """Update team details"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check permissions (owner or admin)
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member or team_member.role not in ['owner', 'admin']:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        team.name = data['name']
    
    if 'description' in data:
        team.description = data['description']
    
    if 'avatar' in data:
        team.avatar = data['avatar']
    
    db.session.commit()
    
    return jsonify({
        "id": team.id,
        "message": "Team updated successfully"
    })

@api.route('/teams/<int:team_id>', methods=['DELETE'])
@require_api_key
def delete_team(team_id):
    """Delete a team (owner only)"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check ownership
    if team.owner_id != user.id:
        return jsonify({"error": "Only the team owner can delete the team"}), 403
    
    db.session.delete(team)
    db.session.commit()
    
    return jsonify({
        "message": "Team deleted successfully"
    })

@api.route('/teams/<int:team_id>/members', methods=['POST'])
@require_api_key
def add_team_member(team_id):
    """Add a member to the team"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check permissions (owner or admin)
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member or team_member.role not in ['owner', 'admin']:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    
    # Validate required fields
    if not data.get('user_id') and not data.get('email'):
        return jsonify({"error": "User ID or email is required"}), 400
    
    # Find user
    new_member = None
    if data.get('user_id'):
        new_member = User.query.get(data['user_id'])
    elif data.get('email'):
        new_member = User.query.filter_by(email=data['email']).first()
    
    if not new_member:
        return jsonify({"error": "User not found"}), 404
    
    # Check if user is already a member
    existing_membership = TeamMember.query.filter_by(
        team_id=team.id,
        user_id=new_member.id
    ).first()
    
    if existing_membership:
        return jsonify({"error": "User is already a member of this team"}), 400
    
    # Add member
    member = TeamMember(
        team_id=team.id,
        user_id=new_member.id,
        role=data.get('role', 'member')
    )
    
    db.session.add(member)
    db.session.commit()
    
    # Trigger webhook for member added
    trigger_webhook(user.id, 'team.member.added', {
        "team_id": team.id,
        "user_id": new_member.id,
        "added_by": user.id,
        "role": member.role,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "team_id": team.id,
        "user_id": new_member.id,
        "role": member.role,
        "message": f"Added {new_member.username} to the team"
    })

@api.route('/teams/<int:team_id>/members/<int:member_id>', methods=['PUT'])
@require_api_key
def update_team_member(team_id, member_id):
    """Update a team member's role"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check permissions (owner or admin)
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member or team_member.role not in ['owner', 'admin']:
        return jsonify({"error": "Access denied"}), 403
    
    # Find member to update
    member = TeamMember.query.filter_by(team_id=team.id, user_id=member_id).first()
    if not member:
        return jsonify({"error": "Member not found"}), 404
    
    # Owner role can only be changed by transferring ownership
    if member.role == 'owner' and user.id != team.owner_id:
        return jsonify({"error": "Only the owner can transfer ownership"}), 403
    
    data = request.json
    
    # Update role
    if 'role' in data:
        # Prevent non-owners from creating new owners
        if data['role'] == 'owner' and user.id != team.owner_id:
            return jsonify({"error": "Only the current owner can transfer ownership"}), 403
        
        old_role = member.role
        member.role = data['role']
        
        # If making someone else owner, change current owner to admin
        if data['role'] == 'owner' and member.user_id != user.id:
            # Update team owner
            team.owner_id = member.user_id
            
            # Change current owner to admin
            current_owner = TeamMember.query.filter_by(
                team_id=team.id,
                user_id=user.id
            ).first()
            
            if current_owner:
                current_owner.role = 'admin'
        
        db.session.commit()
        
        # Trigger webhook for role changed
        trigger_webhook(user.id, 'team.member.updated', {
            "team_id": team.id,
            "user_id": member.user_id,
            "updated_by": user.id,
            "old_role": old_role,
            "new_role": member.role,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "team_id": team.id,
            "user_id": member.user_id,
            "role": member.role,
            "message": "Member role updated successfully"
        })
    
    return jsonify({"error": "No changes specified"}), 400

@api.route('/teams/<int:team_id>/members/<int:member_id>', methods=['DELETE'])
@require_api_key
def remove_team_member(team_id, member_id):
    """Remove a member from the team"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check permissions (owner or admin)
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member or team_member.role not in ['owner', 'admin']:
        return jsonify({"error": "Access denied"}), 403
    
    # Find member to remove
    member = TeamMember.query.filter_by(team_id=team.id, user_id=member_id).first()
    if not member:
        return jsonify({"error": "Member not found"}), 404
    
    # Cannot remove the owner
    if member.role == 'owner':
        return jsonify({"error": "Cannot remove the team owner"}), 403
    
    # Remove member
    db.session.delete(member)
    db.session.commit()
    
    # Trigger webhook for member removed
    trigger_webhook(user.id, 'team.member.removed', {
        "team_id": team.id,
        "user_id": member_id,
        "removed_by": user.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "message": "Member removed successfully"
    })

@api.route('/teams/<int:team_id>/projects', methods=['POST'])
@require_api_key
def add_project_to_team(team_id):
    """Add a project to the team"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check if user is a member of the team
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member:
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    
    # Validate required fields
    if not data.get('project_id'):
        return jsonify({"error": "Project ID is required"}), 400
    
    project_id = data['project_id']
    
    # Verify project exists and user owns it
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    if project.user_id != user.id:
        return jsonify({"error": "You do not own this project"}), 403
    
    # Check if project is already in the team
    existing_team_project = TeamProject.query.filter_by(
        team_id=team.id,
        project_id=project_id
    ).first()
    
    if existing_team_project:
        return jsonify({"error": "Project is already part of this team"}), 400
    
    # Add project to team
    team_project = TeamProject(
        team_id=team.id,
        project_id=project_id
    )
    
    db.session.add(team_project)
    db.session.commit()
    
    return jsonify({
        "team_id": team.id,
        "project_id": project_id,
        "message": "Project added to team successfully"
    })

@api.route('/teams/<int:team_id>/projects/<int:project_id>', methods=['DELETE'])
@require_api_key
def remove_project_from_team(team_id, project_id):
    """Remove a project from the team"""
    user = g.user
    team = Team.query.get(team_id)
    
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    # Check permissions (owner, admin, or project owner)
    team_member = TeamMember.query.filter_by(team_id=team.id, user_id=user.id).first()
    if not team_member:
        return jsonify({"error": "Access denied"}), 403
    
    # Find team project
    team_project = TeamProject.query.filter_by(team_id=team.id, project_id=project_id).first()
    if not team_project:
        return jsonify({"error": "Project not found in this team"}), 404
    
    # Check permissions for removing project
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Allow if user is team owner/admin or project owner
    if team_member.role not in ['owner', 'admin'] and project.user_id != user.id:
        return jsonify({"error": "You do not have permission to remove this project"}), 403
    
    # Remove project from team
    db.session.delete(team_project)
    db.session.commit()
    
    return jsonify({
        "message": "Project removed from team successfully"
    })

# Integration-related endpoints
@api.route('/integrations', methods=['GET'])
@require_api_key
def list_integrations():
    """List all integrations for the current user"""
    user = g.user
    integrations = Integration.query.filter_by(user_id=user.id).all()
    
    result = []
    for integration in integrations:
        result.append({
            "id": integration.id,
            "provider": integration.provider,
            "name": integration.name,
            "is_active": integration.is_active,
            "created_at": integration.created_at.isoformat() if integration.created_at else None,
            "last_used_at": integration.last_used_at.isoformat() if integration.last_used_at else None
        })
    
    return jsonify({"integrations": result})

@api.route('/integrations', methods=['POST'])
@require_api_key
def create_integration():
    """Create a new integration"""
    user = g.user
    data = request.json
    
    # Validate required fields
    required_fields = ['provider', 'name', 'config']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check for duplicate
    existing = Integration.query.filter_by(
        user_id=user.id,
        provider=data['provider'],
        name=data['name']
    ).first()
    
    if existing:
        return jsonify({"error": "Integration with this provider and name already exists"}), 400
    
    # Create integration
    integration = Integration(
        user_id=user.id,
        provider=data['provider'],
        name=data['name'],
        config=json.dumps(data['config']),
        credentials=json.dumps(data.get('credentials', {})) if data.get('credentials') else None,
        is_active=data.get('is_active', True)
    )
    
    db.session.add(integration)
    db.session.commit()
    
    return jsonify({
        "id": integration.id,
        "provider": integration.provider,
        "name": integration.name,
        "message": "Integration created successfully"
    }), 201

@api.route('/integrations/<int:integration_id>', methods=['GET'])
@require_api_key
def get_integration(integration_id):
    """Get integration details"""
    user = g.user
    integration = Integration.query.filter_by(id=integration_id, user_id=user.id).first()
    
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    
    config = {}
    try:
        if integration.config:
            config = json.loads(integration.config)
    except:
        pass
    
    result = {
        "id": integration.id,
        "provider": integration.provider,
        "name": integration.name,
        "config": config,
        "is_active": integration.is_active,
        "created_at": integration.created_at.isoformat() if integration.created_at else None,
        "last_used_at": integration.last_used_at.isoformat() if integration.last_used_at else None
    }
    
    return jsonify(result)

@api.route('/integrations/<int:integration_id>', methods=['PUT'])
@require_api_key
def update_integration(integration_id):
    """Update integration details"""
    user = g.user
    integration = Integration.query.filter_by(id=integration_id, user_id=user.id).first()
    
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        integration.name = data['name']
    
    if 'config' in data:
        integration.config = json.dumps(data['config'])
    
    if 'credentials' in data:
        integration.credentials = json.dumps(data['credentials'])
    
    if 'is_active' in data:
        integration.is_active = bool(data['is_active'])
    
    db.session.commit()
    
    return jsonify({
        "id": integration.id,
        "message": "Integration updated successfully"
    })

@api.route('/integrations/<int:integration_id>', methods=['DELETE'])
@require_api_key
def delete_integration(integration_id):
    """Delete an integration"""
    user = g.user
    integration = Integration.query.filter_by(id=integration_id, user_id=user.id).first()
    
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    
    db.session.delete(integration)
    db.session.commit()
    
    return jsonify({
        "message": "Integration deleted successfully"
    })

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@api.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden"}), 403

@api.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

@api.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500