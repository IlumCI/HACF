import json
import logging
import datetime
import hashlib
from typing import List, Dict, Any, Optional

from flask import current_app
from flask_login import current_user

from app import db
from models import User, Project, Team, TeamMember, ProjectComment, ProjectVersion

# Configure logging
logger = logging.getLogger(__name__)

class CollaborationManager:
    """Manages real-time collaboration features and project sharing"""
    
    @staticmethod
    def get_user_teams(user_id: int) -> List[Dict[str, Any]]:
        """Get all teams for a user with role information"""
        # Query team memberships for the user
        team_memberships = TeamMember.query.filter_by(user_id=user_id).all()
        
        result = []
        for membership in team_memberships:
            team = Team.query.get(membership.team_id)
            if team:
                result.append({
                    'team_id': team.id,
                    'name': team.name,
                    'description': team.description,
                    'avatar': team.avatar,
                    'role': membership.role,
                    'is_owner': team.owner_id == user_id,
                    'member_count': TeamMember.query.filter_by(team_id=team.id).count(),
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None
                })
        
        return result
    
    @staticmethod
    def get_team_members(team_id: int) -> List[Dict[str, Any]]:
        """Get all members of a team with their information"""
        # Verify team exists
        team = Team.query.get(team_id)
        if not team:
            return []
        
        # Query team memberships
        memberships = TeamMember.query.filter_by(team_id=team_id).all()
        
        result = []
        for membership in memberships:
            user = User.query.get(membership.user_id)
            if user:
                result.append({
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': membership.role,
                    'profile_picture': user.profile_picture,
                    'is_owner': team.owner_id == user.id,
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None
                })
        
        return result
    
    @staticmethod
    def get_team_projects(team_id: int) -> List[Dict[str, Any]]:
        """Get all projects shared with a team"""
        from models import TeamProject
        
        # Verify team exists
        team = Team.query.get(team_id)
        if not team:
            return []
        
        # Query team projects
        team_projects = TeamProject.query.filter_by(team_id=team_id).all()
        
        result = []
        for tp in team_projects:
            project = Project.query.get(tp.project_id)
            if project:
                # Get owner info
                owner = User.query.get(project.user_id)
                owner_name = owner.username if owner else "Unknown"
                
                result.append({
                    'project_id': project.id,
                    'title': project.title,
                    'description': project.description,
                    'owner_id': project.user_id,
                    'owner_name': owner_name,
                    'progress': project.progress(),
                    'created_at': project.created_at.isoformat() if project.created_at else None,
                    'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                    'layer1_complete': project.layer1_complete,
                    'layer2_complete': project.layer2_complete,
                    'layer3_complete': project.layer3_complete,
                    'layer4_complete': project.layer4_complete,
                    'layer5_complete': project.layer5_complete
                })
        
        return result
    
    @staticmethod
    def check_team_access(user_id: int, team_id: int, required_role: Optional[str] = None) -> bool:
        """Check if a user has access to a team, optionally with a specific role"""
        # Query team membership
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        
        if not membership:
            return False
        
        # Check role if required
        if required_role:
            # For 'admin' access, both 'admin' and 'owner' roles are sufficient
            if required_role == 'admin':
                return membership.role in ['admin', 'owner']
            # For other roles, exact match is required
            return membership.role == required_role
        
        return True
    
    @staticmethod
    def share_project_with_team(project_id: int, team_id: int, user_id: int) -> Dict[str, Any]:
        """Share a project with a team"""
        from models import TeamProject
        
        # Verify project exists and user has access
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Check if user owns the project or is an admin
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        if project.user_id != user_id and user.role != 'admin':
            return {"success": False, "error": "You don't have permission to share this project"}
        
        # Verify team exists and user is a member
        team = Team.query.get(team_id)
        if not team:
            return {"success": False, "error": "Team not found"}
        
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        if not membership:
            return {"success": False, "error": "You are not a member of this team"}
        
        # Check if project is already shared with the team
        existing = TeamProject.query.filter_by(team_id=team_id, project_id=project_id).first()
        if existing:
            return {"success": False, "error": "Project is already shared with this team"}
        
        # Share project with team
        team_project = TeamProject(team_id=team_id, project_id=project_id)
        
        try:
            db.session.add(team_project)
            db.session.commit()
            return {"success": True, "message": "Project shared successfully"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sharing project: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def unshare_project_from_team(project_id: int, team_id: int, user_id: int) -> Dict[str, Any]:
        """Remove a project from a team"""
        from models import TeamProject
        
        # Find team project
        team_project = TeamProject.query.filter_by(team_id=team_id, project_id=project_id).first()
        if not team_project:
            return {"success": False, "error": "Project is not shared with this team"}
        
        # Verify user has permission (project owner, team owner/admin)
        project = Project.query.get(project_id)
        team = Team.query.get(team_id)
        
        if not project or not team:
            return {"success": False, "error": "Project or team not found"}
        
        # Check if user is project owner
        is_project_owner = project.user_id == user_id
        
        # Check if user is team owner/admin
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        is_team_admin = membership and membership.role in ['owner', 'admin']
        
        # Check if user is global admin
        user = User.query.get(user_id)
        is_global_admin = user and user.role == 'admin'
        
        if not (is_project_owner or is_team_admin or is_global_admin):
            return {"success": False, "error": "You don't have permission to unshare this project"}
        
        # Remove project from team
        try:
            db.session.delete(team_project)
            db.session.commit()
            return {"success": True, "message": "Project removed from team successfully"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error unsharing project: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def add_project_comment(project_id: int, user_id: int, content: str, 
                          file_path: Optional[str] = None, 
                          line_number: Optional[int] = None,
                          parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Add a comment to a project"""
        # Verify project exists
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Check if user has access to the project
        if not CollaborationManager.can_access_project(user_id, project_id):
            return {"success": False, "error": "You don't have access to this project"}
        
        # Check parent comment if specified
        if parent_id:
            parent = ProjectComment.query.get(parent_id)
            if not parent or parent.project_id != project_id:
                return {"success": False, "error": "Invalid parent comment"}
        
        # Create comment
        comment = ProjectComment(
            project_id=project_id,
            user_id=user_id,
            content=content,
            file_path=file_path,
            line_number=line_number,
            parent_id=parent_id
        )
        
        try:
            db.session.add(comment)
            db.session.commit()
            
            return {
                "success": True,
                "comment_id": comment.id,
                "message": "Comment added successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding comment: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def get_project_comments(project_id: int, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all comments for a project, optionally filtered by file"""
        # Query comments
        query = ProjectComment.query.filter_by(project_id=project_id)
        
        # Filter by file if specified
        if file_path:
            query = query.filter_by(file_path=file_path)
        
        comments = query.order_by(ProjectComment.created_at).all()
        
        # Format comments
        result = []
        comment_map = {}
        
        for comment in comments:
            user = User.query.get(comment.user_id)
            username = user.username if user else "Unknown User"
            
            formatted = {
                'id': comment.id,
                'content': comment.content,
                'user_id': comment.user_id,
                'username': username,
                'file_path': comment.file_path,
                'line_number': comment.line_number,
                'created_at': comment.created_at.isoformat() if comment.created_at else None,
                'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
                'parent_id': comment.parent_id,
                'replies': []
            }
            
            comment_map[comment.id] = formatted
            
            # Add to result if it's a top-level comment
            if not comment.parent_id:
                result.append(formatted)
            # Otherwise add to parent's replies
            elif comment.parent_id in comment_map:
                comment_map[comment.parent_id]['replies'].append(formatted)
        
        return result
    
    @staticmethod
    def can_access_project(user_id: int, project_id: int) -> bool:
        """Check if a user has access to a project"""
        # Verify project exists
        project = Project.query.get(project_id)
        if not project:
            return False
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return False
        
        # User is project owner
        if project.user_id == user_id:
            return True
        
        # User is global admin
        if user.role == 'admin':
            return True
        
        # Check if project is shared with any team the user is a member of
        from models import TeamProject
        
        # Get user's teams
        user_teams = TeamMember.query.filter_by(user_id=user_id).all()
        user_team_ids = [tm.team_id for tm in user_teams]
        
        # Check if project is in any of these teams
        team_project = TeamProject.query.filter(
            TeamProject.project_id == project_id,
            TeamProject.team_id.in_(user_team_ids)
        ).first()
        
        return team_project is not None
    
    @staticmethod
    def create_project_version(project_id: int, user_id: int, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new version snapshot of a project"""
        # Verify project exists
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user exists and has access
        if not CollaborationManager.can_access_project(user_id, project_id):
            return {"success": False, "error": "You don't have access to this project"}
        
        # Get next version number
        latest_version = ProjectVersion.query.filter_by(project_id=project_id)\
            .order_by(ProjectVersion.version_number.desc()).first()
        
        next_version = 1
        if latest_version:
            next_version = latest_version.version_number + 1
        
        # Create snapshot of project
        snapshot = {
            'title': project.title,
            'description': project.description,
            'task_definition': project.task_definition,
            'refined_structure': project.refined_structure,
            'development_code': project.development_code,
            'optimized_code': project.optimized_code,
            'files': project.files,
            'layer1_complete': project.layer1_complete,
            'layer2_complete': project.layer2_complete,
            'layer3_complete': project.layer3_complete,
            'layer4_complete': project.layer4_complete,
            'layer5_complete': project.layer5_complete,
            'version_created_at': datetime.datetime.utcnow().isoformat(),
            'version_created_by': user_id
        }
        
        # Create version
        version = ProjectVersion(
            project_id=project_id,
            version_number=next_version,
            description=description,
            snapshot=json.dumps(snapshot),
            created_by=user_id
        )
        
        try:
            db.session.add(version)
            db.session.commit()
            
            return {
                "success": True,
                "version_id": version.id,
                "version_number": version.version_number,
                "message": "Project version created successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating project version: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def get_project_versions(project_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a project"""
        # Query versions
        versions = ProjectVersion.query.filter_by(project_id=project_id)\
            .order_by(ProjectVersion.version_number.desc()).all()
        
        result = []
        for version in versions:
            user = User.query.get(version.created_by)
            username = user.username if user else "Unknown User"
            
            result.append({
                'id': version.id,
                'version_number': version.version_number,
                'description': version.description,
                'created_by': version.created_by,
                'created_by_username': username,
                'created_at': version.created_at.isoformat() if version.created_at else None
            })
        
        return result
    
    @staticmethod
    def restore_project_version(project_id: int, version_id: int, user_id: int) -> Dict[str, Any]:
        """Restore a project to a previous version"""
        # Verify project exists
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user has permission to modify project
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        if project.user_id != user_id and user.role != 'admin':
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Find the version
        version = ProjectVersion.query.get(version_id)
        if not version or version.project_id != project_id:
            return {"success": False, "error": "Version not found"}
        
        try:
            # Create snapshot of current state before restoring
            CollaborationManager.create_project_version(
                project_id, 
                user_id, 
                f"Automatic snapshot before restoring to version {version.version_number}"
            )
            
            # Restore from snapshot
            snapshot = json.loads(version.snapshot)
            
            project.title = snapshot.get('title', project.title)
            project.description = snapshot.get('description', project.description)
            project.task_definition = snapshot.get('task_definition', project.task_definition)
            project.refined_structure = snapshot.get('refined_structure', project.refined_structure)
            project.development_code = snapshot.get('development_code', project.development_code)
            project.optimized_code = snapshot.get('optimized_code', project.optimized_code)
            project.files = snapshot.get('files', project.files)
            project.layer1_complete = snapshot.get('layer1_complete', project.layer1_complete)
            project.layer2_complete = snapshot.get('layer2_complete', project.layer2_complete)
            project.layer3_complete = snapshot.get('layer3_complete', project.layer3_complete)
            project.layer4_complete = snapshot.get('layer4_complete', project.layer4_complete)
            project.layer5_complete = snapshot.get('layer5_complete', project.layer5_complete)
            
            db.session.commit()
            
            return {
                "success": True,
                "message": f"Project restored to version {version.version_number} successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error restoring project version: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}

class RealtimeCollaboration:
    """
    Manages real-time collaboration functionality
    This is a placeholder for WebSocket-based collaboration that would be implemented
    with a library like Socket.IO in a production environment
    """
    
    @staticmethod
    def get_active_users(project_id: int) -> List[Dict[str, Any]]:
        """Get users currently viewing/editing a project"""
        # In a real implementation, this would check a real-time data store
        return []
    
    @staticmethod
    def notify_project_update(project_id: int, user_id: int, update_type: str, data: Dict[str, Any]) -> bool:
        """
        Notify other users about a project update
        This is a placeholder for real-time notifications
        """
        # In a real implementation, this would broadcast to connected clients
        logger.info(f"Notification: Project {project_id} updated by user {user_id}: {update_type}")
        return True