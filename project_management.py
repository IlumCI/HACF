import json
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple

from app import db
from models import Project, User

# Configure logging
logger = logging.getLogger(__name__)

class ProjectManager:
    """Manages enhanced project management features"""
    
    # Task status constants
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_REVIEW = 'review'
    STATUS_DONE = 'done'
    STATUS_BLOCKED = 'blocked'
    
    # Priority constants
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'
    
    @staticmethod
    def get_project_tasks(project_id: int) -> List[Dict[str, Any]]:
        """Get all tasks for a project"""
        project = Project.query.get(project_id)
        if not project:
            return []
        
        # Check if project has tasks stored in metadata
        tasks = []
        try:
            if project.metadata:
                metadata = json.loads(project.metadata)
                tasks = metadata.get('tasks', [])
        except Exception as e:
            logger.error(f"Error parsing project tasks: {str(e)}")
        
        return tasks
    
    @staticmethod
    def add_project_task(project_id: int, user_id: int, 
                       title: str, description: Optional[str] = None,
                       priority: str = 'medium', status: str = 'todo',
                       due_date: Optional[str] = None) -> Dict[str, Any]:
        """Add a new task to a project"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing tasks
        tasks = ProjectManager.get_project_tasks(project_id)
        
        # Generate task ID
        task_id = f"task-{len(tasks) + 1}-{datetime.datetime.utcnow().timestamp():.0f}"
        
        # Create new task
        new_task = {
            'id': task_id,
            'title': title,
            'description': description,
            'status': status,
            'priority': priority,
            'created_by': user_id,
            'assigned_to': None,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'updated_at': datetime.datetime.utcnow().isoformat(),
            'due_date': due_date,
            'comments': []
        }
        
        # Add to tasks list
        tasks.append(new_task)
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['tasks'] = tasks
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "Task added successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding project task: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def update_project_task(project_id: int, user_id: int, task_id: str, 
                         updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing task"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing tasks
        tasks = ProjectManager.get_project_tasks(project_id)
        
        # Find the task
        task_index = None
        for i, task in enumerate(tasks):
            if task.get('id') == task_id:
                task_index = i
                break
        
        if task_index is None:
            return {"success": False, "error": "Task not found"}
        
        # Update the task
        for key, value in updates.items():
            # Don't allow updating id, created_by, created_at
            if key not in ['id', 'created_by', 'created_at']:
                tasks[task_index][key] = value
        
        # Update timestamp
        tasks[task_index]['updated_at'] = datetime.datetime.utcnow().isoformat()
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['tasks'] = tasks
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Task updated successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating project task: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def delete_project_task(project_id: int, user_id: int, task_id: str) -> Dict[str, Any]:
        """Delete a task from a project"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing tasks
        tasks = ProjectManager.get_project_tasks(project_id)
        
        # Find and remove the task
        new_tasks = [task for task in tasks if task.get('id') != task_id]
        
        if len(new_tasks) == len(tasks):
            return {"success": False, "error": "Task not found"}
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['tasks'] = new_tasks
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Task deleted successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting project task: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def add_task_comment(project_id: int, user_id: int, task_id: str, content: str) -> Dict[str, Any]:
        """Add a comment to a task"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user has access to project
        if not ProjectManager._can_access_project(user_id, project_id):
            return {"success": False, "error": "You don't have access to this project"}
        
        # Get existing tasks
        tasks = ProjectManager.get_project_tasks(project_id)
        
        # Find the task
        task_index = None
        for i, task in enumerate(tasks):
            if task.get('id') == task_id:
                task_index = i
                break
        
        if task_index is None:
            return {"success": False, "error": "Task not found"}
        
        # Make sure task has comments array
        if 'comments' not in tasks[task_index]:
            tasks[task_index]['comments'] = []
        
        # Get user info
        user = User.query.get(user_id)
        username = user.username if user else "Unknown"
        
        # Add comment
        comment = {
            'id': f"comment-{len(tasks[task_index]['comments']) + 1}-{datetime.datetime.utcnow().timestamp():.0f}",
            'content': content,
            'user_id': user_id,
            'username': username,
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        tasks[task_index]['comments'].append(comment)
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['tasks'] = tasks
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "comment_id": comment['id'],
                "message": "Comment added successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding task comment: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def get_project_milestones(project_id: int) -> List[Dict[str, Any]]:
        """Get all milestones for a project"""
        project = Project.query.get(project_id)
        if not project:
            return []
        
        # Check if project has milestones stored in metadata
        milestones = []
        try:
            if project.metadata:
                metadata = json.loads(project.metadata)
                milestones = metadata.get('milestones', [])
        except Exception as e:
            logger.error(f"Error parsing project milestones: {str(e)}")
        
        return milestones
    
    @staticmethod
    def add_project_milestone(project_id: int, user_id: int, 
                            title: str, description: Optional[str] = None,
                            due_date: Optional[str] = None) -> Dict[str, Any]:
        """Add a new milestone to a project"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing milestones
        milestones = ProjectManager.get_project_milestones(project_id)
        
        # Generate milestone ID
        milestone_id = f"milestone-{len(milestones) + 1}-{datetime.datetime.utcnow().timestamp():.0f}"
        
        # Create new milestone
        new_milestone = {
            'id': milestone_id,
            'title': title,
            'description': description,
            'status': 'pending',  # pending, completed
            'created_by': user_id,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'updated_at': datetime.datetime.utcnow().isoformat(),
            'due_date': due_date,
            'completed_at': None,
            'tasks': []  # Task IDs associated with this milestone
        }
        
        # Add to milestones list
        milestones.append(new_milestone)
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['milestones'] = milestones
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "milestone_id": milestone_id,
                "message": "Milestone added successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding project milestone: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def update_project_milestone(project_id: int, user_id: int, milestone_id: str, 
                              updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing milestone"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing milestones
        milestones = ProjectManager.get_project_milestones(project_id)
        
        # Find the milestone
        milestone_index = None
        for i, milestone in enumerate(milestones):
            if milestone.get('id') == milestone_id:
                milestone_index = i
                break
        
        if milestone_index is None:
            return {"success": False, "error": "Milestone not found"}
        
        # Check if marking as completed
        if updates.get('status') == 'completed' and milestones[milestone_index].get('status') != 'completed':
            updates['completed_at'] = datetime.datetime.utcnow().isoformat()
        
        # Update the milestone
        for key, value in updates.items():
            # Don't allow updating id, created_by, created_at
            if key not in ['id', 'created_by', 'created_at']:
                milestones[milestone_index][key] = value
        
        # Update timestamp
        milestones[milestone_index]['updated_at'] = datetime.datetime.utcnow().isoformat()
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['milestones'] = milestones
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Milestone updated successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating project milestone: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def get_project_timeline(project_id: int) -> Dict[str, Any]:
        """Get project timeline with milestones, tasks, and dependencies"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Get milestones and tasks
        milestones = ProjectManager.get_project_milestones(project_id)
        tasks = ProjectManager.get_project_tasks(project_id)
        
        # Get dependencies
        dependencies = []
        try:
            if project.metadata:
                metadata = json.loads(project.metadata)
                dependencies = metadata.get('dependencies', [])
        except Exception as e:
            logger.error(f"Error parsing project dependencies: {str(e)}")
        
        # Calculate start and end dates
        start_date = project.created_at.isoformat() if project.created_at else None
        
        end_date = None
        if project.completed_at:
            end_date = project.completed_at.isoformat()
        else:
            # Find the latest due date among milestones and tasks
            dates = []
            
            for milestone in milestones:
                if milestone.get('due_date'):
                    dates.append(milestone.get('due_date'))
            
            for task in tasks:
                if task.get('due_date'):
                    dates.append(task.get('due_date'))
            
            if dates:
                end_date = max(dates)
        
        return {
            "success": True,
            "timeline": {
                "project_id": project_id,
                "title": project.title,
                "start_date": start_date,
                "end_date": end_date,
                "milestones": milestones,
                "tasks": tasks,
                "dependencies": dependencies
            }
        }
    
    @staticmethod
    def add_task_dependency(project_id: int, user_id: int, 
                          source_task_id: str, target_task_id: str,
                          dependency_type: str = 'finish_to_start') -> Dict[str, Any]:
        """Add a dependency between two tasks"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing tasks to verify they exist
        tasks = ProjectManager.get_project_tasks(project_id)
        
        source_task = None
        target_task = None
        
        for task in tasks:
            if task.get('id') == source_task_id:
                source_task = task
            if task.get('id') == target_task_id:
                target_task = task
        
        if not source_task:
            return {"success": False, "error": "Source task not found"}
        
        if not target_task:
            return {"success": False, "error": "Target task not found"}
        
        # Get existing dependencies
        dependencies = []
        try:
            if project.metadata:
                metadata = json.loads(project.metadata)
                dependencies = metadata.get('dependencies', [])
        except Exception as e:
            logger.error(f"Error parsing project dependencies: {str(e)}")
        
        # Check if dependency already exists
        for dep in dependencies:
            if dep.get('source') == source_task_id and dep.get('target') == target_task_id:
                return {"success": False, "error": "Dependency already exists"}
        
        # Add dependency
        dependency_id = f"dep-{len(dependencies) + 1}-{datetime.datetime.utcnow().timestamp():.0f}"
        
        dependency = {
            'id': dependency_id,
            'source': source_task_id,
            'target': target_task_id,
            'type': dependency_type,
            'created_by': user_id,
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        dependencies.append(dependency)
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['dependencies'] = dependencies
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "dependency_id": dependency_id,
                "message": "Dependency added successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding task dependency: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def remove_task_dependency(project_id: int, user_id: int, dependency_id: str) -> Dict[str, Any]:
        """Remove a dependency between tasks"""
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}
        
        # Verify user can modify project
        if not ProjectManager._can_modify_project(user_id, project_id):
            return {"success": False, "error": "You don't have permission to modify this project"}
        
        # Get existing dependencies
        dependencies = []
        try:
            if project.metadata:
                metadata = json.loads(project.metadata)
                dependencies = metadata.get('dependencies', [])
        except Exception as e:
            logger.error(f"Error parsing project dependencies: {str(e)}")
        
        # Find and remove the dependency
        new_dependencies = [dep for dep in dependencies if dep.get('id') != dependency_id]
        
        if len(new_dependencies) == len(dependencies):
            return {"success": False, "error": "Dependency not found"}
        
        try:
            # Update project metadata
            metadata = {}
            if project.metadata:
                try:
                    metadata = json.loads(project.metadata)
                except:
                    metadata = {}
            
            metadata['dependencies'] = new_dependencies
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Dependency removed successfully"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing task dependency: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    @staticmethod
    def generate_gantt_chart_data(project_id: int) -> Dict[str, Any]:
        """Generate data format suitable for Gantt chart visualization"""
        # Get project timeline
        timeline_result = ProjectManager.get_project_timeline(project_id)
        
        if not timeline_result.get('success', False):
            return timeline_result
        
        timeline = timeline_result.get('timeline', {})
        
        # Format tasks for Gantt chart
        tasks = []
        links = []
        
        # Add milestones as summary tasks
        for i, milestone in enumerate(timeline.get('milestones', [])):
            milestone_start = milestone.get('due_date')
            if not milestone_start:
                # Use project start date if milestone has no due date
                milestone_start = timeline.get('start_date')
            
            tasks.append({
                'id': milestone.get('id'),
                'text': milestone.get('title'),
                'start_date': milestone_start,
                'duration': 1,  # Milestones are usually shown as zero-duration
                'progress': 1.0 if milestone.get('status') == 'completed' else 0.0,
                'type': 'milestone'
            })
        
        # Add regular tasks
        for i, task in enumerate(timeline.get('tasks', [])):
            # Parse due date or use current date plus some days
            task_due_date = task.get('due_date')
            if not task_due_date:
                # Use a placeholder date for visualization
                task_due_date = datetime.datetime.utcnow() + datetime.timedelta(days=i + 1)
                task_due_date = task_due_date.isoformat()
            
            # Calculate progress based on status
            progress = 0.0
            if task.get('status') == 'done':
                progress = 1.0
            elif task.get('status') == 'in_progress':
                progress = 0.5
            elif task.get('status') == 'review':
                progress = 0.75
            
            tasks.append({
                'id': task.get('id'),
                'text': task.get('title'),
                'start_date': timeline.get('start_date'),
                'duration': 3,  # Placeholder
                'progress': progress,
                'type': 'task',
                'priority': task.get('priority', 'medium')
            })
        
        # Add dependencies as links
        for dependency in timeline.get('dependencies', []):
            links.append({
                'id': dependency.get('id'),
                'source': dependency.get('source'),
                'target': dependency.get('target'),
                'type': dependency.get('type', 'finish_to_start')
            })
        
        return {
            "success": True,
            "gantt_data": {
                "tasks": tasks,
                "links": links
            }
        }
    
    # Helper methods
    
    @staticmethod
    def _can_modify_project(user_id: int, project_id: int) -> bool:
        """Check if a user can modify a project"""
        project = Project.query.get(project_id)
        if not project:
            return False
        
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Project owner can modify
        if project.user_id == user_id:
            return True
        
        # Admin can modify
        if user.role == 'admin':
            return True
        
        # Team access is handled differently - would be implemented in a real application
        return False
    
    @staticmethod
    def _can_access_project(user_id: int, project_id: int) -> bool:
        """Check if a user can access a project"""
        # In a real app, this would check team memberships
        # For now, we'll just check if they can modify
        return ProjectManager._can_modify_project(user_id, project_id)