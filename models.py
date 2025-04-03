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
    
    # Role-based access control fields
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'manager'
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
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
