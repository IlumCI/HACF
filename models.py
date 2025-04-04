from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from typing import Dict, List, Any, Optional

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    conversations = db.relationship('Conversation', backref='user', lazy=True, foreign_keys='Conversation.user_id')
    projects = db.relationship('Project', backref='user', lazy=True, foreign_keys='Project.user_id')
    
    # Role-based access control field - add this column to the database
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'manager'
    
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
    
    # HACF layers output - 12 layer framework
    layer0_output = db.Column(db.Text)  # Layer 0: Requirement Validation
    layer1_output = db.Column(db.Text)  # Layer 1: Task Definition
    layer2_output = db.Column(db.Text)  # Layer 2: Analysis & Research
    layer3_output = db.Column(db.Text)  # Layer 3: Refinement
    layer4_output = db.Column(db.Text)  # Layer 4: Prototyping
    layer5_output = db.Column(db.Text)  # Layer 5: Development
    layer6_output = db.Column(db.Text)  # Layer 6: Testing & QA
    layer7_output = db.Column(db.Text)  # Layer 7: Optimization
    layer8_output = db.Column(db.Text)  # Layer 8: Deployment Preparation
    layer9_output = db.Column(db.Text)  # Layer 9: Final Output
    layer10_output = db.Column(db.Text)  # Layer 10: Monitoring & Feedback
    layer11_output = db.Column(db.Text)  # Layer 11: Evolution & Maintenance
    
    # Legacy fields for backward compatibility
    task_definition = db.Column(db.Text)  # Legacy: Layer 1
    refined_structure = db.Column(db.Text)  # Legacy: Layer 2
    development_code = db.Column(db.Text)  # Legacy: Layer 3
    optimized_code = db.Column(db.Text)  # Legacy: Layer 4
    files = db.Column(db.Text)  # Legacy: JSON string of files generated - Layer 5
    
    # Layered process flags - 12 layer framework
    layer0_complete = db.Column(db.Boolean, default=False)
    layer1_complete = db.Column(db.Boolean, default=False)
    layer2_complete = db.Column(db.Boolean, default=False)
    layer3_complete = db.Column(db.Boolean, default=False)
    layer4_complete = db.Column(db.Boolean, default=False)
    layer5_complete = db.Column(db.Boolean, default=False)
    layer6_complete = db.Column(db.Boolean, default=False)
    layer7_complete = db.Column(db.Boolean, default=False)
    layer8_complete = db.Column(db.Boolean, default=False)
    layer9_complete = db.Column(db.Boolean, default=False)
    layer10_complete = db.Column(db.Boolean, default=False)
    layer11_complete = db.Column(db.Boolean, default=False)
    
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
            self.layer0_complete,
            self.layer1_complete,
            self.layer2_complete,
            self.layer3_complete,
            self.layer4_complete,
            self.layer5_complete,
            self.layer6_complete,
            self.layer7_complete,
            self.layer8_complete,
            self.layer9_complete,
            self.layer10_complete,
            self.layer11_complete
        ])
        return (completed_layers / 12) * 100
        
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


# Advanced HACF Framework Models

class HACFSession(db.Model):
    """
    Tracks an active HACF processing session with enhanced framework features
    """
    id = db.Column(db.String(36), primary_key=True)  # UUID
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Current state
    current_layer = db.Column(db.Integer, default=0)  # Current HACF layer being processed (0-11)
    status = db.Column(db.String(20), default='active')  # active, paused, completed, failed
    
    # Adaptive sequencing
    layer_sequence = db.Column(db.Text, nullable=True)  # JSON array of ordered layer numbers
    sequence_rationale = db.Column(db.Text, nullable=True)  # Explanation for sequence decision
    
    # Domain specialization
    domain = db.Column(db.String(50), nullable=True)  # Domain specialization applied (healthcare, finance, etc.)
    industry = db.Column(db.String(50), nullable=True)  # Industry specialization
    complexity_assessment = db.Column(db.Text, nullable=True)  # JSON complexity assessment
    
    # Timestamps for layer completion - 12 layer framework
    layer0_started_at = db.Column(db.DateTime, nullable=True)
    layer0_completed_at = db.Column(db.DateTime, nullable=True)
    layer1_started_at = db.Column(db.DateTime, nullable=True)
    layer1_completed_at = db.Column(db.DateTime, nullable=True)
    layer2_started_at = db.Column(db.DateTime, nullable=True)
    layer2_completed_at = db.Column(db.DateTime, nullable=True)
    layer3_started_at = db.Column(db.DateTime, nullable=True)
    layer3_completed_at = db.Column(db.DateTime, nullable=True)
    layer4_started_at = db.Column(db.DateTime, nullable=True)
    layer4_completed_at = db.Column(db.DateTime, nullable=True)
    layer5_started_at = db.Column(db.DateTime, nullable=True)
    layer5_completed_at = db.Column(db.DateTime, nullable=True)
    layer6_started_at = db.Column(db.DateTime, nullable=True)
    layer6_completed_at = db.Column(db.DateTime, nullable=True)
    layer7_started_at = db.Column(db.DateTime, nullable=True)
    layer7_completed_at = db.Column(db.DateTime, nullable=True)
    layer8_started_at = db.Column(db.DateTime, nullable=True)
    layer8_completed_at = db.Column(db.DateTime, nullable=True)
    layer9_started_at = db.Column(db.DateTime, nullable=True)
    layer9_completed_at = db.Column(db.DateTime, nullable=True)
    layer10_started_at = db.Column(db.DateTime, nullable=True)
    layer10_completed_at = db.Column(db.DateTime, nullable=True)
    layer11_started_at = db.Column(db.DateTime, nullable=True)
    layer11_completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    checkpoints = db.relationship('HACFCheckpoint', backref='session', lazy=True)
    memories = db.relationship('HACFMemory', backref='session', lazy=True)
    evaluations = db.relationship('HACFEvaluation', backref='session', lazy=True)
    
    def __repr__(self):
        return f'<HACFSession {self.id}>'
    
    @property
    def layer_sequence_list(self) -> List[int]:
        """Get the layer sequence as a Python list"""
        if not self.layer_sequence:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Default sequence - 12 layer framework
        try:
            return json.loads(self.layer_sequence)
        except:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    
    @property
    def next_layer(self) -> Optional[int]:
        """Get the next layer in the sequence"""
        sequence = self.layer_sequence_list
        if self.current_layer in sequence:
            idx = sequence.index(self.current_layer)
            if idx < len(sequence) - 1:
                return sequence[idx + 1]
        return None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate session progress percentage"""
        sequence = self.layer_sequence_list
        if not sequence:
            return 0.0
            
        # Count completed layers in the sequence
        completed_count = 0
        for layer in sequence:
            completed_at_attr = f'layer{layer}_completed_at'
            if hasattr(self, completed_at_attr) and getattr(self, completed_at_attr) is not None:
                completed_count += 1
                
        return (completed_count / len(sequence)) * 100


class HACFMemory(db.Model):
    """
    Represents a memory entry in the cross-layer memory system
    """
    id = db.Column(db.String(36), primary_key=True)  # UUID
    session_id = db.Column(db.String(36), db.ForeignKey('hacf_session.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Memory content
    source_layer = db.Column(db.Integer, nullable=False)  # Which layer created this memory
    memory_type = db.Column(db.String(30), nullable=False)  # decision, constraint, insight, error, etc.
    priority = db.Column(db.String(20), nullable=False)  # critical, high, medium, low
    content = db.Column(db.Text, nullable=False)  # The actual memory content
    memory_metadata = db.Column(db.Text, nullable=True)  # JSON metadata
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<HACFMemory {self.id}>'
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as a Python dictionary"""
        if not self.memory_metadata:
            return {}
        try:
            return json.loads(self.memory_metadata)
        except:
            return {}


class HACFCheckpoint(db.Model):
    """
    Represents a human-AI collaboration checkpoint during processing
    """
    id = db.Column(db.String(36), primary_key=True)  # UUID
    session_id = db.Column(db.String(36), db.ForeignKey('hacf_session.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Checkpoint information
    layer = db.Column(db.Integer, nullable=False)  # Layer to which this checkpoint applies
    checkpoint_type = db.Column(db.String(30), nullable=False)  # review, guidance, correction, etc.
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.String(20), nullable=False)  # before, during, after
    required_skills = db.Column(db.Text, nullable=True)  # JSON array of required skills
    is_optional = db.Column(db.Boolean, default=True)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, completed, skipped
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Feedback
    feedback = db.Column(db.Text, nullable=True)  # JSON feedback data
    feedback_processed = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<HACFCheckpoint {self.id}>'
    
    @property
    def required_skills_list(self) -> List[str]:
        """Get required skills as a Python list"""
        if not self.required_skills:
            return []
        try:
            return json.loads(self.required_skills)
        except:
            return []
    
    @property
    def feedback_dict(self) -> Dict[str, Any]:
        """Get feedback as a Python dictionary"""
        if not self.feedback:
            return {}
        try:
            return json.loads(self.feedback)
        except:
            return {}


class HACFEvaluation(db.Model):
    """
    Stores evaluation results for HACF layer outputs using proprietary metrics
    """
    id = db.Column(db.String(36), primary_key=True)  # UUID
    session_id = db.Column(db.String(36), db.ForeignKey('hacf_session.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Evaluation target
    layer = db.Column(db.Integer, nullable=False)  # Layer being evaluated
    output_id = db.Column(db.String(36), nullable=True)  # ID of output being evaluated (if applicable)
    
    # Overall scores
    overall_score = db.Column(db.Float, nullable=False)  # Overall evaluation score (0.0-1.0)
    dimension_scores = db.Column(db.Text, nullable=False)  # JSON of dimension scores
    metric_scores = db.Column(db.Text, nullable=False)  # JSON of individual metric scores
    
    # Analysis
    recommendations = db.Column(db.Text, nullable=True)  # JSON array of recommendations
    strengths = db.Column(db.Text, nullable=True)  # JSON array of identified strengths
    weaknesses = db.Column(db.Text, nullable=True)  # JSON array of identified weaknesses
    
    # Domain-specific evaluation
    domain = db.Column(db.String(50), nullable=True)  # Domain for specialized evaluation
    domain_specific_scores = db.Column(db.Text, nullable=True)  # JSON of domain-specific metrics
    
    def __repr__(self):
        return f'<HACFEvaluation {self.id}>'
    
    @property
    def dimension_scores_dict(self) -> Dict[str, float]:
        """Get dimension scores as a Python dictionary"""
        if not self.dimension_scores:
            return {}
        try:
            return json.loads(self.dimension_scores)
        except:
            return {}
    
    @property
    def recommendations_list(self) -> List[str]:
        """Get recommendations as a Python list"""
        if not self.recommendations:
            return []
        try:
            return json.loads(self.recommendations)
        except:
            return []
