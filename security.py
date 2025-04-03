import os
import re
import time
import json
import logging
import hashlib
import secrets
import datetime
import ipaddress
from typing import List, Dict, Any, Optional, Tuple

from flask import request, abort, current_app, g, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_login import current_user

from app import db
from models import User

# Configure logging
logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security features and enhancements"""
    
    # Authentication constants
    TOKEN_EXPIRY = 3600  # 1 hour
    FAILED_LOGIN_LIMIT = 5
    FAILED_LOGIN_WINDOW = 900  # 15 minutes
    PASSWORD_RESET_EXPIRY = 86400  # 24 hours
    
    # CSRF tokens
    _csrf_tokens = {}
    _csrf_token_expiry = {}
    
    # Rate limiting
    _request_counts = {}
    _ip_blocklist = set()
    
    # Failed login attempts
    _failed_logins = {}
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage"""
        return generate_password_hash(password)
    
    @staticmethod
    def check_password(hashed_password: str, password: str) -> bool:
        """Check if a password matches its hash"""
        return check_password_hash(hashed_password, password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """Validate password meets strength requirements"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Check for complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain at least one uppercase letter, one lowercase letter, and one digit"
        
        if not has_special:
            return False, "Password must contain at least one special character"
        
        # Check for common passwords (simplified - would use a proper list in production)
        common_passwords = ['password', 'password123', '12345678', 'qwerty123']
        if password.lower() in common_passwords:
            return False, "Password is too common"
        
        return True, "Password meets strength requirements"
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_csrf_token(session_id: str) -> str:
        """Generate a CSRF token for a session"""
        token = secrets.token_urlsafe(32)
        
        SecurityManager._csrf_tokens[session_id] = token
        SecurityManager._csrf_token_expiry[session_id] = time.time() + 3600  # 1 hour
        
        return token
    
    @staticmethod
    def verify_csrf_token(session_id: str, token: str) -> bool:
        """Verify a CSRF token is valid for a session"""
        if session_id not in SecurityManager._csrf_tokens:
            return False
        
        if session_id in SecurityManager._csrf_token_expiry and SecurityManager._csrf_token_expiry[session_id] < time.time():
            # Token expired, remove it
            del SecurityManager._csrf_tokens[session_id]
            del SecurityManager._csrf_token_expiry[session_id]
            return False
        
        return SecurityManager._csrf_tokens[session_id] == token
    
    @staticmethod
    def validate_input(input_data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate input data against a set of rules
        
        Example rules:
        {
            'username': {
                'required': True,
                'type': 'string',
                'min_length': 3,
                'max_length': 30,
                'pattern': r'^[a-zA-Z0-9_]+$'
            },
            'email': {
                'required': True,
                'type': 'email'
            }
        }
        """
        errors = {}
        
        for field, rule in rules.items():
            # Check if field is required but missing
            if rule.get('required', False) and (field not in input_data or input_data[field] is None):
                errors[field] = f"{field} is required"
                continue
            
            # Skip validation if field is not present
            if field not in input_data or input_data[field] is None:
                continue
            
            value = input_data[field]
            
            # Type validation
            field_type = rule.get('type', 'string')
            if field_type == 'string':
                if not isinstance(value, str):
                    errors[field] = f"{field} must be a string"
                    continue
                
                # String length validation
                min_length = rule.get('min_length')
                if min_length is not None and len(value) < min_length:
                    errors[field] = f"{field} must be at least {min_length} characters"
                    continue
                
                max_length = rule.get('max_length')
                if max_length is not None and len(value) > max_length:
                    errors[field] = f"{field} must be at most {max_length} characters"
                    continue
                
                # Pattern validation
                pattern = rule.get('pattern')
                if pattern and not re.match(pattern, value):
                    errors[field] = f"{field} has an invalid format"
                    continue
            
            elif field_type == 'email':
                if not isinstance(value, str):
                    errors[field] = f"{field} must be a string"
                    continue
                
                # Basic email validation - production would use proper regex or libraries
                if '@' not in value or '.' not in value:
                    errors[field] = f"{field} must be a valid email address"
                    continue
            
            elif field_type == 'number':
                if not isinstance(value, (int, float)):
                    errors[field] = f"{field} must be a number"
                    continue
                
                # Number range validation
                min_value = rule.get('min_value')
                if min_value is not None and value < min_value:
                    errors[field] = f"{field} must be at least {min_value}"
                    continue
                
                max_value = rule.get('max_value')
                if max_value is not None and value > max_value:
                    errors[field] = f"{field} must be at most {max_value}"
                    continue
            
            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors[field] = f"{field} must be a boolean"
                    continue
            
            elif field_type == 'date':
                if not isinstance(value, str):
                    errors[field] = f"{field} must be a string"
                    continue
                
                # Date validation - would use proper validation in production
                try:
                    datetime.datetime.fromisoformat(value)
                except ValueError:
                    errors[field] = f"{field} must be a valid date in ISO format"
                    continue
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_html(html: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks
        In a production system, this would use a library like bleach
        """
        # Very basic implementation - would use a proper library in production
        # Replace script tags
        html = html.replace('<script', '&lt;script')
        html = html.replace('</script>', '&lt;/script&gt;')
        
        # Replace on* event handlers
        import re
        html = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
        
        return html
    
    @staticmethod
    def sanitize_input(data: Dict[str, Any], sanitize_fields: List[str]) -> Dict[str, Any]:
        """Sanitize specific fields in input data"""
        sanitized = data.copy()
        
        for field in sanitize_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = SecurityManager.sanitize_html(sanitized[field])
        
        return sanitized
    
    @staticmethod
    def rate_limit(ip_address: str, limit: int = 60, window: int = 60) -> bool:
        """
        Rate limit requests by IP address
        Returns True if rate limit is not exceeded, False otherwise
        """
        now = time.time()
        key = f"{ip_address}:{int(now / window)}"
        
        # Check if IP is blocklisted
        if ip_address in SecurityManager._ip_blocklist:
            return False
        
        # Update request count
        if key in SecurityManager._request_counts:
            SecurityManager._request_counts[key] += 1
        else:
            SecurityManager._request_counts[key] = 1
        
        # Check if limit is exceeded
        if SecurityManager._request_counts[key] > limit:
            # Add to blocklist for temporary period if rate limit far exceeded
            if SecurityManager._request_counts[key] > limit * 2:
                SecurityManager._ip_blocklist.add(ip_address)
                
                # Schedule removal from blocklist after 1 hour
                def remove_from_blocklist():
                    time.sleep(3600)
                    if ip_address in SecurityManager._ip_blocklist:
                        SecurityManager._ip_blocklist.remove(ip_address)
                
                import threading
                thread = threading.Thread(target=remove_from_blocklist)
                thread.daemon = True
                thread.start()
            
            return False
        
        return True
    
    @staticmethod
    def record_failed_login(username: str, ip_address: str) -> bool:
        """
        Record a failed login attempt
        Returns True if account should be temporarily locked
        """
        now = time.time()
        key = f"{username}:{ip_address}"
        
        # Initialize or update failed login count
        if key in SecurityManager._failed_logins:
            # Check if window has expired
            if now - SecurityManager._failed_logins[key]['first_attempt'] > SecurityManager.FAILED_LOGIN_WINDOW:
                # Reset if window expired
                SecurityManager._failed_logins[key] = {
                    'count': 1,
                    'first_attempt': now,
                    'last_attempt': now
                }
            else:
                # Increment count
                SecurityManager._failed_logins[key]['count'] += 1
                SecurityManager._failed_logins[key]['last_attempt'] = now
        else:
            # First failed attempt
            SecurityManager._failed_logins[key] = {
                'count': 1,
                'first_attempt': now,
                'last_attempt': now
            }
        
        # Check if limit exceeded
        return SecurityManager._failed_logins[key]['count'] >= SecurityManager.FAILED_LOGIN_LIMIT
    
    @staticmethod
    def is_account_locked(username: str, ip_address: str) -> bool:
        """Check if an account is temporarily locked due to failed login attempts"""
        now = time.time()
        key = f"{username}:{ip_address}"
        
        if key not in SecurityManager._failed_logins:
            return False
        
        login_info = SecurityManager._failed_logins[key]
        
        # Check if window has expired
        if now - login_info['first_attempt'] > SecurityManager.FAILED_LOGIN_WINDOW:
            # Window expired, remove record
            del SecurityManager._failed_logins[key]
            return False
        
        # Check if limit exceeded
        return login_info['count'] >= SecurityManager.FAILED_LOGIN_LIMIT
    
    @staticmethod
    def reset_failed_logins(username: str, ip_address: str) -> None:
        """Reset failed login attempts after successful login"""
        key = f"{username}:{ip_address}"
        
        if key in SecurityManager._failed_logins:
            del SecurityManager._failed_logins[key]
    
    @staticmethod
    def check_ip_risk(ip_address: str) -> Dict[str, Any]:
        """Check if an IP address is potentially risky"""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Check if private address
            if ip.is_private:
                return {'risk': 'low', 'reason': 'Private IP address'}
            
            # Check if loopback
            if ip.is_loopback:
                return {'risk': 'low', 'reason': 'Loopback address'}
            
            # Check for known VPN/Proxy exit points
            # In a real system, this would check against a database of known exits
            
            # Placeholder for demonstration
            return {'risk': 'unknown', 'reason': 'No risk factors identified'}
            
        except ValueError:
            return {'risk': 'high', 'reason': 'Invalid IP address format'}

# Decorators for endpoint security

def csrf_protected(f):
    """Decorator to require CSRF token verification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only check POST/PUT/DELETE requests
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.form.get('csrf_token')
            if not token or not SecurityManager.verify_csrf_token(session.get('id'), token):
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

def rate_limited(limit=60, window=60):
    """Decorator to apply rate limiting to an endpoint"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            if not SecurityManager.rate_limit(ip, limit, window):
                abort(429)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to restrict access to admin users"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission):
    """Decorator to require a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            
            # Check if user has permission
            user_permissions = current_user.get_permissions()
            if permission not in user_permissions:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Flask request handlers

def before_request_security():
    """Security checks to run before each request"""
    # Rate limiting
    ip = request.remote_addr
    if not SecurityManager.rate_limit(ip):
        abort(429)
    
    # Add CSRF token to template context
    if 'id' in session:
        g.csrf_token = SecurityManager.generate_csrf_token(session['id'])
    
    # Security headers will be set in after_request

def after_request_security(response):
    """Add security headers to responses"""
    # Content Security Policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'"
    
    # Prevent browsers from performing MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Enforce HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Clickjacking protection
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

def init_security(app):
    """Initialize security features for a Flask application"""
    # Register before/after request handlers
    app.before_request(before_request_security)
    app.after_request(after_request_security)
    
    # Set Flask app security settings
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=12)
    
    # Default to requiring HTTPS in production
    if not app.debug and not app.testing:
        from flask_talisman import Talisman
        Talisman(app, content_security_policy={
            'default-src': ['\'self\''],
            'script-src': ['\'self\''],
            'style-src': ['\'self\'', 'https://cdn.replit.com'],
            'img-src': ['\'self\'', 'data:'],
            'font-src': ['\'self\'', 'https://cdn.replit.com']
        })
    
    # Set up cleanup tasks for security
    @app.before_first_request
    def setup_security_cleanup():
        def cleanup_job():
            while True:
                # Clean up expired CSRF tokens
                now = time.time()
                expired_tokens = [
                    session_id for session_id, expiry in SecurityManager._csrf_token_expiry.items()
                    if expiry < now
                ]
                
                for session_id in expired_tokens:
                    if session_id in SecurityManager._csrf_tokens:
                        del SecurityManager._csrf_tokens[session_id]
                    if session_id in SecurityManager._csrf_token_expiry:
                        del SecurityManager._csrf_token_expiry[session_id]
                
                # Clean up old request counts for rate limiting
                keys_to_remove = []
                for key in SecurityManager._request_counts.keys():
                    # Extract timestamp from key
                    try:
                        ip, timestamp = key.split(':')
                        if int(timestamp) < int(now / 60) - 10:  # Keep for 10 minutes
                            keys_to_remove.append(key)
                    except:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del SecurityManager._request_counts[key]
                
                # Wait before next cleanup
                time.sleep(300)  # Run every 5 minutes
        
        # Start cleanup thread
        import threading
        cleanup_thread = threading.Thread(target=cleanup_job)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    logger.info("Security features initialized")