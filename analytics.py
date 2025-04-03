import json
import logging
import datetime
from collections import defaultdict

from models import Project, User, TeamMember, Conversation, Message

# Configure logging
logger = logging.getLogger(__name__)

class AnalyticsManager:
    """Manages analytics data collection and processing"""
    
    @staticmethod
    def get_project_stats():
        """Get overall project statistics"""
        from app import db
        
        # Basic project stats
        total_projects = Project.query.count()
        completed_projects = Project.query.filter_by(layer5_complete=True).count()
        active_projects = total_projects - completed_projects
        
        # Layer completion stats
        layer1_complete = Project.query.filter_by(layer1_complete=True).count()
        layer2_complete = Project.query.filter_by(layer2_complete=True).count()
        layer3_complete = Project.query.filter_by(layer3_complete=True).count()
        layer4_complete = Project.query.filter_by(layer4_complete=True).count()
        layer5_complete = completed_projects
        
        # Calculate average time per layer (placeholder for now)
        # In a real implementation, we would calculate based on timestamps
        
        # Calculate completion rate
        completion_rate = int((completed_projects / total_projects) * 100) if total_projects > 0 else 0
        
        # Get conversation metrics
        total_conversations = Conversation.query.count()
        total_messages = Message.query.count()
        
        # Assemble stats
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'completion_rate': completion_rate,
            'layer_stats': {
                'layer1': {'complete': layer1_complete, 'percent': int((layer1_complete / total_projects) * 100) if total_projects > 0 else 0},
                'layer2': {'complete': layer2_complete, 'percent': int((layer2_complete / total_projects) * 100) if total_projects > 0 else 0},
                'layer3': {'complete': layer3_complete, 'percent': int((layer3_complete / total_projects) * 100) if total_projects > 0 else 0},
                'layer4': {'complete': layer4_complete, 'percent': int((layer4_complete / total_projects) * 100) if total_projects > 0 else 0},
                'layer5': {'complete': layer5_complete, 'percent': int((layer5_complete / total_projects) * 100) if total_projects > 0 else 0},
            },
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conversation': round(total_messages / total_conversations, 1) if total_conversations > 0 else 0
        }
        
        return stats
    
    @staticmethod
    def get_project_timeline(days=30):
        """Get project creation and completion timeline"""
        from app import db
        from sqlalchemy import func
        
        # Define the date range
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get created projects by day
        created_projects = db.session.query(
            func.date(Project.created_at).label('date'), 
            func.count().label('count')
        ).filter(
            Project.created_at >= start_date,
            Project.created_at <= end_date
        ).group_by(
            func.date(Project.created_at)
        ).all()
        
        # Get completed projects by day
        completed_projects = db.session.query(
            func.date(Project.completed_at).label('date'), 
            func.count().label('count')
        ).filter(
            Project.completed_at.isnot(None),
            Project.completed_at >= start_date,
            Project.completed_at <= end_date
        ).group_by(
            func.date(Project.completed_at)
        ).all()
        
        # Convert to dictionaries
        created_dict = {str(date): count for date, count in created_projects}
        completed_dict = {str(date): count for date, count in completed_projects}
        
        # Generate a list of all dates in the range
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            date_list.append(date_str)
            current_date += datetime.timedelta(days=1)
        
        # Create the final dataset
        timeline = {
            'dates': date_list,
            'created': [created_dict.get(date, 0) for date in date_list],
            'completed': [completed_dict.get(date, 0) for date in date_list]
        }
        
        return timeline
    
    @staticmethod
    def get_user_activity(days=30):
        """Get user activity statistics"""
        from app import db
        from sqlalchemy import func
        
        # Define the date range
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get active users (users who have logged in during the period)
        active_users = User.query.filter(
            User.last_login.isnot(None),
            User.last_login >= start_date
        ).count()
        
        # Get new users (users who registered during the period)
        new_users = User.query.filter(
            User.registration_date >= start_date
        ).count()
        
        # Get total users
        total_users = User.query.count()
        
        # Get message count by day
        message_counts = db.session.query(
            func.date(Message.timestamp).label('date'), 
            func.count().label('count')
        ).filter(
            Message.timestamp >= start_date,
            Message.timestamp <= end_date
        ).group_by(
            func.date(Message.timestamp)
        ).all()
        
        # Convert to dictionary
        message_dict = {str(date): count for date, count in message_counts}
        
        # Generate a list of all dates in the range
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            date_list.append(date_str)
            current_date += datetime.timedelta(days=1)
        
        # Create the activity dataset
        activity = {
            'active_users': active_users,
            'new_users': new_users,
            'total_users': total_users,
            'retention_rate': int((active_users / total_users) * 100) if total_users > 0 else 0,
            'message_activity': {
                'dates': date_list,
                'counts': [message_dict.get(date, 0) for date in date_list]
            }
        }
        
        return activity
    
    @staticmethod
    def get_layer_performance():
        """Get performance metrics for each HACF layer"""
        from app import db
        
        # Count total projects
        total_projects = Project.query.count()
        if total_projects == 0:
            return {}
        
        # Get layer completion counts
        layer1_complete = Project.query.filter_by(layer1_complete=True).count()
        layer2_complete = Project.query.filter_by(layer2_complete=True).count()
        layer3_complete = Project.query.filter_by(layer3_complete=True).count()
        layer4_complete = Project.query.filter_by(layer4_complete=True).count()
        layer5_complete = Project.query.filter_by(layer5_complete=True).count()
        
        # Calculate success rates
        layer_stats = {
            'layer1': {
                'name': 'Task Definition & Planning',
                'success_rate': round((layer1_complete / total_projects) * 100, 1),
                'failure_rate': round(100 - ((layer1_complete / total_projects) * 100), 1),
                'avg_time': 2.5,  # Placeholder - would calculate from actual data
                'common_issues': ['Incomplete specifications', 'Ambiguous requirements', 'Conflicting goals']
            },
            'layer2': {
                'name': 'Refinement & Base Structure',
                'success_rate': round((layer2_complete / total_projects) * 100, 1) if layer1_complete > 0 else 0,
                'failure_rate': round(100 - ((layer2_complete / layer1_complete) * 100), 1) if layer1_complete > 0 else 100,
                'avg_time': 3.8,  # Placeholder
                'common_issues': ['Incompatible technologies', 'Architecture limitations', 'Resource constraints']
            },
            'layer3': {
                'name': 'Development & Execution',
                'success_rate': round((layer3_complete / layer2_complete) * 100, 1) if layer2_complete > 0 else 0,
                'failure_rate': round(100 - ((layer3_complete / layer2_complete) * 100), 1) if layer2_complete > 0 else 100,
                'avg_time': 8.5,  # Placeholder
                'common_issues': ['Integration errors', 'Missing dependencies', 'Implementation complexity']
            },
            'layer4': {
                'name': 'Debugging & Optimization',
                'success_rate': round((layer4_complete / layer3_complete) * 100, 1) if layer3_complete > 0 else 0,
                'failure_rate': round(100 - ((layer4_complete / layer3_complete) * 100), 1) if layer3_complete > 0 else 100,
                'avg_time': 5.2,  # Placeholder
                'common_issues': ['Security vulnerabilities', 'Performance bottlenecks', 'Edge case handling']
            },
            'layer5': {
                'name': 'Final Output',
                'success_rate': round((layer5_complete / layer4_complete) * 100, 1) if layer4_complete > 0 else 0,
                'failure_rate': round(100 - ((layer5_complete / layer4_complete) * 100), 1) if layer4_complete > 0 else 100,
                'avg_time': 1.3,  # Placeholder
                'common_issues': ['File formatting issues', 'Packaging errors', 'Documentation gaps']
            }
        }
        
        return layer_stats
    
    @staticmethod
    def get_technology_usage():
        """Get statistics about technology usage across projects"""
        from app import db
        
        # This would parse project metadata to determine technologies used
        # For now, we'll return placeholder data
        
        # Placeholder technologies
        technologies = {
            'languages': [
                {'name': 'Python', 'count': 35},
                {'name': 'JavaScript', 'count': 28},
                {'name': 'TypeScript', 'count': 12},
                {'name': 'Java', 'count': 8},
                {'name': 'C#', 'count': 6},
                {'name': 'PHP', 'count': 5},
                {'name': 'Ruby', 'count': 4},
                {'name': 'Go', 'count': 3}
            ],
            'frameworks': [
                {'name': 'React', 'count': 18},
                {'name': 'Flask', 'count': 15},
                {'name': 'Express', 'count': 12},
                {'name': 'Django', 'count': 10},
                {'name': 'Angular', 'count': 7},
                {'name': 'Vue.js', 'count': 6},
                {'name': 'Spring Boot', 'count': 5},
                {'name': 'ASP.NET', 'count': 4}
            ],
            'databases': [
                {'name': 'PostgreSQL', 'count': 22},
                {'name': 'MongoDB', 'count': 14},
                {'name': 'MySQL', 'count': 12},
                {'name': 'SQLite', 'count': 10},
                {'name': 'Redis', 'count': 6},
                {'name': 'Firestore', 'count': 5},
                {'name': 'DynamoDB', 'count': 3},
                {'name': 'Cassandra', 'count': 2}
            ]
        }
        
        return technologies
    
    @staticmethod
    def get_team_analytics():
        """Get analytics data for teams"""
        from app import db
        
        # Count total teams
        total_teams = TeamMember.query.distinct(TeamMember.team_id).count()
        
        # Average team size
        avg_team_size = db.session.query(
            db.func.avg(db.session.query(TeamMember).filter_by(team_id=TeamMember.team_id).count())
        ).scalar()
        
        if avg_team_size is None:
            avg_team_size = 0
        else:
            avg_team_size = round(float(avg_team_size), 1)
        
        # Get data about projects per team
        team_data = []
        
        # In a real implementation, we would query team projects here
        # For now, return placeholder data
        
        return {
            'total_teams': total_teams,
            'avg_team_size': avg_team_size,
            'team_data': [
                {'team_id': 1, 'name': 'Frontend Team', 'member_count': 5, 'project_count': 8},
                {'team_id': 2, 'name': 'Backend Team', 'member_count': 4, 'project_count': 6},
                {'team_id': 3, 'name': 'Data Science', 'member_count': 3, 'project_count': 4},
                {'team_id': 4, 'name': 'Mobile Dev', 'member_count': 2, 'project_count': 3}
            ]
        }
    
    @staticmethod
    def generate_analytics_report(user_id=None, from_date=None, to_date=None, include_teams=False):
        """Generate a comprehensive analytics report"""
        # Set default date range if not provided
        if not to_date:
            to_date = datetime.datetime.utcnow()
        
        if not from_date:
            from_date = to_date - datetime.timedelta(days=30)
        
        # Get all the analytics data
        report = {
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'date_range': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'project_stats': AnalyticsManager.get_project_stats(),
            'timeline': AnalyticsManager.get_project_timeline(days=(to_date - from_date).days),
            'user_activity': AnalyticsManager.get_user_activity(days=(to_date - from_date).days),
            'layer_performance': AnalyticsManager.get_layer_performance(),
            'technology_usage': AnalyticsManager.get_technology_usage()
        }
        
        # Include team analytics if requested
        if include_teams:
            report['team_analytics'] = AnalyticsManager.get_team_analytics()
        
        return report
    
    @staticmethod
    def export_analytics_data(format='json'):
        """Export analytics data in various formats"""
        # Generate the report
        report_data = AnalyticsManager.generate_analytics_report(include_teams=True)
        
        if format == 'json':
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            # In a real implementation, we would convert to CSV
            # For now, just return a message
            return "CSV export not yet implemented"
        
        elif format == 'pdf':
            # In a real implementation, we would generate a PDF
            # For now, just return a message
            return "PDF export not yet implemented"
        
        else:
            return f"Unsupported format: {format}"