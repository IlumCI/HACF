import os
import json
import logging
import hashlib
import secrets
import datetime
import ipaddress
from functools import wraps

from flask import request, redirect, url_for, flash, abort, session, g, current_app
from flask_login import current_user

from models import User
from app import db

# Configure logging
logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security features like 2FA, rate limiting, and audit logging"""
    
    # Rate limiting settings
    RATE_LIMITS = {
        'login': {'count': 5, 'period': 300},  # 5 attempts per 5 minutes
        'register': {'count': 3, 'period': 3600},  # 3 attempts per hour
        'api': {'count': 100, 'period': 3600},  # 100 requests per hour
        'password_reset': {'count': 3, 'period': 86400}  # 3 attempts per day
    }
    
    # IP access control
    IP_WHITELIST = []
    IP_BLACKLIST = []
    
    @classmethod
    def setup(cls):
        """Initialize security settings from environment or config"""
        # Load IP whitelists/blacklists from environment
        whitelist = os.environ.get('IP_WHITELIST', '')
        blacklist = os.environ.get('IP_BLACKLIST', '')
        
        if whitelist:
            cls.IP_WHITELIST = [ip.strip() for ip in whitelist.split(',')]
        
        if blacklist:
            cls.IP_BLACKLIST = [ip.strip() for ip in blacklist.split(',')]
    
    @classmethod
    def check_ip_access(cls, ip_address):
        """Check if an IP address is allowed to access the application"""
        # If whitelist is defined, only allow IPs on the whitelist
        if cls.IP_WHITELIST:
            return cls._ip_in_list(ip_address, cls.IP_WHITELIST)
        
        # If no whitelist but blacklist exists, block IPs on the blacklist
        if cls.IP_BLACKLIST:
            return not cls._ip_in_list(ip_address, cls.IP_BLACKLIST)
        
        # If no lists defined, allow all
        return True
    
    @classmethod
    def _ip_in_list(cls, ip_address, ip_list):
        """Check if an IP address is in a list of IPs or CIDR ranges"""
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            
            for ip_entry in ip_list:
                # Check if entry is a CIDR range
                if '/' in ip_entry:
                    network = ipaddress.ip_network(ip_entry, strict=False)
                    if ip_obj in network:
                        return True
                # Check for exact match
                elif ip_address == ip_entry:
                    return True
            
            return False
        except ValueError:
            logger.error(f"Invalid IP address format: {ip_address}")
            return False
    
    @classmethod
    def rate_limit_check(cls, key, identifier):
        """
        Check if a rate limit has been exceeded
        key: The type of rate limit (login, register, etc.)
        identifier: Unique identifier (IP, user_id, etc.)
        
        Returns: (allowed, remaining, reset_time)
        """
        if key not in cls.RATE_LIMITS:
            return True, None, None
        
        limit = cls.RATE_LIMITS[key]
        rate_limit_key = f"rate_limit:{key}:{identifier}"
        
        # Get current tracking data from session or initialize
        now = datetime.datetime.utcnow()
        rate_data = session.get(rate_limit_key, {
            'count': 0,
            'reset_time': (now + datetime.timedelta(seconds=limit['period'])).timestamp()
        })
        
        # Check if we need to reset the counter
        if now.timestamp() > rate_data['reset_time']:
            rate_data = {
                'count': 0,
                'reset_time': (now + datetime.timedelta(seconds=limit['period'])).timestamp()
            }
        
        # Check if limit exceeded
        allowed = rate_data['count'] < limit['count']
        remaining = limit['count'] - rate_data['count']
        reset_time = datetime.datetime.fromtimestamp(rate_data['reset_time'])
        
        # Increment counter if not in testing mode
        if allowed and not current_app.testing:
            rate_data['count'] += 1
            session[rate_limit_key] = rate_data
        
        return allowed, remaining, reset_time
    
    @classmethod
    def check_rate_limit(cls, key):
        """Decorator for rate-limited routes"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                identifier = request.remote_addr
                allowed, remaining, reset_time = cls.rate_limit_check(key, identifier)
                
                if not allowed:
                    logger.warning(f"Rate limit exceeded for {key} by {identifier}")
                    flash(f"Too many attempts. Please try again after {reset_time.strftime('%H:%M:%S')}.", "danger")
                    return redirect(url_for('home'))
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @classmethod
    def create_audit_log(cls, user_id, action, resource_type=None, resource_id=None, details=None, status='success'):
        """
        Create an audit log entry
        In a real implementation, this would save to a database table
        """
        log_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string if hasattr(request, 'user_agent') else None,
            'details': details,
            'status': status
        }
        
        logger.info(f"AUDIT: {json.dumps(log_entry)}")
        return log_entry
    
    @classmethod
    def require_2fa(cls, f):
        """Decorator to require 2FA for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            # Check if user has 2FA enabled and verified for this session
            if current_user.has_2fa and not session.get('2fa_verified'):
                # Store the original URL for redirection after 2FA
                session['next'] = request.url
                return redirect(url_for('verify_2fa'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    @classmethod
    def generate_totp_secret(cls):
        """Generate a new TOTP secret for 2FA"""
        return secrets.token_hex(20)
    
    @classmethod
    def validate_totp(cls, secret, token):
        """
        Validate a TOTP token
        This is a placeholder that would use a library like pyotp in a real implementation
        """
        # In a real implementation:
        # import pyotp
        # totp = pyotp.TOTP(secret)
        # return totp.verify(token)
        
        # For demo purposes, just check if token is '123456'
        return token == '123456'

# Middleware function to apply security checks
def security_middleware():
    """Apply security checks and headers to all requests"""
    # Skip checks for static files
    if request.path.startswith('/static/'):
        return
    
    # Check IP access
    if not SecurityManager.check_ip_access(request.remote_addr):
        abort(403, description="Your IP address is not allowed to access this application.")
    
    # Set security headers
    response = current_app.make_default_response()
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdn.replit.com; img-src 'self' data: https:; font-src 'self' data: https:;"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

# Password complexity checker
def check_password_strength(password):
    """Check if a password meets complexity requirements"""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    
    # Check for character types
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    if not (has_lower and has_upper and has_digit and has_special):
        return False, "Password must include uppercase, lowercase, numbers, and special characters."
    
    return True, "Password meets complexity requirements."

# Initialize security settings
SecurityManager.setup()