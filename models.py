from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    conversations = db.relationship('Conversation', backref='user', lazy=True)
    projects = db.relationship('Project', backref='user', lazy=True)
    templates = db.relationship('ProjectTemplate', backref='user', lazy=True)
    
    # User profile fields
    profile_picture = db.Column(db.String(255), nullable=True)  # URL to profile image
    bio = db.Column(db.Text, nullable=True)  # User biography/description
    company = db.Column(db.String(100), nullable=True)  # User's company or organization
    job_title = db.Column(db.String(100), nullable=True)  # User's job title
    website = db.Column(db.String(255), nullable=True)  # User's personal website
    location = db.Column(db.String(100), nullable=True)  # User's location
    
    # Preferences
    preferred_technologies = db.Column(db.Text, nullable=True)  # JSON string of preferred technologies
    theme_preference = db.Column(db.String(20), default='dark')  # 'light', 'dark', 'system'
    email_notifications = db.Column(db.Boolean, default=True)  # Whether to send email notifications
    
    # API integration
    api_key = db.Column(db.String(64), nullable=True, unique=True)  # Personal API key
    api_quota = db.Column(db.Integer, default=100)  # API usage quota
    api_usage_count = db.Column(db.Integer, default=0)  # Current API usage
    
    # Role-based access control fields
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'manager'
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True if from user, False if from AI
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # HACF specific fields
    hacf_layer = db.Column(db.String(50), nullable=True)  # Which HACF layer processed this message
    hacf_layer_number = db.Column(db.Integer, nullable=True)  # Numerical identifier for the layer (1-5)
    layer_metadata = db.Column(db.Text, nullable=True)  # Additional metadata from layer processing
    
    def __repr__(self):
        return f'<Message {self.id}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # HACF layers output
    task_definition = db.Column(db.Text)  # Layer 1: Task Definition & Planning
    refined_structure = db.Column(db.Text)  # Layer 2: Refinement & Base Structure
    development_code = db.Column(db.Text)  # Layer 3: Development & Execution
    optimized_code = db.Column(db.Text)  # Layer 4: Debugging, Optimization & Security
    files = db.Column(db.Text)  # JSON string of files generated - Layer 5: Final Output
    
    # Layered process flags
    layer1_complete = db.Column(db.Boolean, default=False)
    layer2_complete = db.Column(db.Boolean, default=False)
    layer3_complete = db.Column(db.Boolean, default=False)
    layer4_complete = db.Column(db.Boolean, default=False)
    layer5_complete = db.Column(db.Boolean, default=False)
    
    # Date tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Project {self.title}>'
    
    @property
    def progress(self):
        """Calculate project completion percentage based on completed layers"""
        completed_layers = sum([
            self.layer1_complete,
            self.layer2_complete,
            self.layer3_complete,
            self.layer4_complete,
            self.layer5_complete
        ])
        return (completed_layers / 5) * 100
        
# Project Template model for saving and reusing project configurations
class ProjectTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    configuration = db.Column(db.Text, nullable=False)  # JSON string of project configuration
    is_public = db.Column(db.Boolean, default=False)  # Whether template is shared publicly
    category = db.Column(db.String(50), default='general')  # Category for templates (web, mobile, etc.)
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    
    # Usage metrics
    use_count = db.Column(db.Integer, default=0)  # Number of times template has been used
    rating = db.Column(db.Float, default=0.0)  # Average user rating
    rating_count = db.Column(db.Integer, default=0)  # Number of ratings received
    
    # Date tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProjectTemplate {self.name}>'
        
# Team and Collaboration Models
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    avatar = db.Column(db.String(255), nullable=True)  # URL to team avatar
    
    # Team members through TeamMember relationship
    members = db.relationship('TeamMember', backref='team', lazy=True, cascade='all, delete-orphan')
    
    # Team projects through TeamProject relationship
    projects = db.relationship('TeamProject', backref='team', lazy=True, cascade='all, delete-orphan')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Team {self.name}>'

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'owner', 'admin', 'member', 'viewer'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # To ensure a user can be a member of a team only once
    __table_args__ = (db.UniqueConstraint('team_id', 'user_id', name='_team_user_uc'),)
    
    def __repr__(self):
        return f'<TeamMember {self.user_id} in Team {self.team_id}>'

class TeamProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # Ensure a project can be associated with a team only once
    __table_args__ = (db.UniqueConstraint('team_id', 'project_id', name='_team_project_uc'),)
    
    def __repr__(self):
        return f'<TeamProject {self.project_id} in Team {self.team_id}>'

# Model for project comments and feedback
class ProjectComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)  # Path to specific file if comment is file-specific
    line_number = db.Column(db.Integer, nullable=True)  # Line number if comment is on specific code line
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # For threaded comments
    parent_id = db.Column(db.Integer, db.ForeignKey('project_comment.id'), nullable=True)
    replies = db.relationship('ProjectComment', backref=db.backref('parent', remote_side=[id]))
    
    def __repr__(self):
        return f'<ProjectComment {self.id} for Project {self.project_id}>'

# Model for project versions/history
class ProjectVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    snapshot = db.Column(db.Text, nullable=False)  # JSON snapshot of project state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Ensure a project can only have one of each version number
    __table_args__ = (db.UniqueConstraint('project_id', 'version_number', name='_project_version_uc'),)
    
    def __repr__(self):
        return f'<ProjectVersion {self.version_number} for Project {self.project_id}>'

# API Integration Models
class ApiClient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    client_id = db.Column(db.String(64), nullable=False, unique=True)
    client_secret = db.Column(db.String(128), nullable=False)
    redirect_uris = db.Column(db.Text, nullable=True)  # JSON array of URIs
    allowed_scopes = db.Column(db.Text, nullable=False)  # JSON array of allowed scopes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # For OAuth integration
    authorization_code = db.Column(db.String(100), nullable=True)
    code_expires_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<ApiClient {self.name}>'

class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    api_client_id = db.Column(db.Integer, db.ForeignKey('api_client.id'), nullable=True)
    access_token = db.Column(db.String(128), nullable=False, unique=True)
    refresh_token = db.Column(db.String(128), nullable=True, unique=True)
    token_type = db.Column(db.String(20), default='Bearer')
    scopes = db.Column(db.Text, nullable=True)  # JSON array of scopes
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_revoked = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ApiToken {self.id}>'
    
    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(255), nullable=False)
    secret = db.Column(db.String(64), nullable=True)  # For signature verification
    events = db.Column(db.Text, nullable=False)  # JSON array of event types
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    failure_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Webhook {self.name}>'

class WebhookEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey('webhook.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.Text, nullable=False)  # JSON payload
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    response_code = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<WebhookEvent {self.event_type} for Webhook {self.webhook_id}>'

class Integration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # github, gitlab, jenkins, etc.
    name = db.Column(db.String(100), nullable=False)
    config = db.Column(db.Text, nullable=False)  # JSON configuration
    credentials = db.Column(db.Text, nullable=True)  # Encrypted credentials
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'provider', 'name', name='_user_provider_name_uc'),)
    
    def __repr__(self):
        return f'<Integration {self.provider}/{self.name}>'
