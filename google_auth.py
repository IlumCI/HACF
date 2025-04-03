import json
import os
import logging

import requests
from flask import Blueprint, redirect, request, url_for, flash, session
from flask_login import login_required, login_user, logout_user, current_user
from oauthlib.oauth2 import WebApplicationClient

from models import User
from app import db

# Configure logging
logger = logging.getLogger(__name__)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get the current Replit domain for the redirect URL
REPLIT_DOMAIN = os.environ.get("REPLIT_DOMAIN", os.environ.get("REPLIT_DEV_DOMAIN"))
REDIRECT_URL = f"https://{REPLIT_DOMAIN}/google_login/callback" if REPLIT_DOMAIN else None

# Display setup instructions in logs
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    logger.info("Google OAuth credentials found.")
    if REDIRECT_URL:
        logger.info(f"Redirect URL: {REDIRECT_URL}")
        logger.info("Ensure this URL is added to your Google OAuth app's redirect URIs")
else:
    logger.warning("""
To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add appropriate redirect URIs to Authorized redirect URIs
4. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables
""")

# Only create client if credentials are available
client = WebApplicationClient(GOOGLE_CLIENT_ID) if GOOGLE_CLIENT_ID else None

# Create blueprint
google_auth = Blueprint("google_auth", __name__)

@google_auth.route("/google_login")
def login():
    """Initiate Google OAuth flow"""
    # Check if OAuth is configured
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google authentication is not configured.", "danger")
        return redirect(url_for("login"))
    
    # Get Google's provider configuration
    try:
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        # Generate request URI
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            # Ensure we use HTTPS for the external URL
            redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    except Exception as e:
        logger.error(f"Error initiating Google login: {str(e)}")
        flash("An error occurred while connecting to Google. Please try again.", "danger")
        return redirect(url_for("login"))

@google_auth.route("/google_login/callback")
def callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google authentication is not configured.", "danger")
        return redirect(url_for("login"))
    
    # Get authorization code from request
    code = request.args.get("code")
    if not code:
        flash("Authentication failed. Please try again.", "danger")
        return redirect(url_for("login"))
    
    try:
        # Get Google provider configuration
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        
        # Prepare and send token request
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=request.base_url.replace("http://", "https://"),
            code=code,
        )
        
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )
        
        # Parse the token response
        client.parse_request_body_response(json.dumps(token_response.json()))
        
        # Get user info from Google
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)
        userinfo = userinfo_response.json()
        
        # Verify email
        if not userinfo.get("email_verified"):
            flash("User email not verified by Google.", "danger")
            return redirect(url_for("login"))
        
        # Get user details
        user_email = userinfo["email"]
        user_name = userinfo.get("given_name", userinfo.get("name", "User"))
        
        # Find or create user
        user = User.query.filter_by(email=user_email).first()
        if not user:
            # Create new user
            user = User(
                username=user_name,
                email=user_email
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new user via Google login: {user_email}")
        
        # Log in the user
        login_user(user)
        flash(f"Welcome, {user.username}! You've successfully logged in with Google.", "success")
        
        # Redirect to originally requested page if it exists
        next_page = session.pop('next', None)
        if next_page:
            return redirect(next_page)
        return redirect(url_for("profile"))
    
    except Exception as e:
        logger.error(f"Error in Google login callback: {str(e)}")
        flash("An error occurred during Google authentication. Please try again.", "danger")
        return redirect(url_for("login"))

@google_auth.route("/logout")
@login_required
def logout():
    """Log out the user"""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))