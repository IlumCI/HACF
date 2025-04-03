import os
import json
import logging
import hashlib
import datetime
from typing import List, Dict, Any, Optional

from app import db
from models import User, Project

# Configure logging
logger = logging.getLogger(__name__)

class KnowledgeBase:
    """Manages the knowledge base system for code patterns and solutions"""
    
    @staticmethod
    def extract_snippets_from_project(project: Project) -> List[Dict[str, Any]]:
        """
        Extract reusable code snippets from a project
        This would be integrated with AI analysis in a production system
        """
        snippets = []
        
        try:
            # If project has files, analyze them for reusable patterns
            if project.files:
                files = json.loads(project.files)
                
                for file in files:
                    # Extract filename and extension
                    filename = file.get('name', '')
                    if not filename:
                        continue
                    
                    extension = os.path.splitext(filename)[1].lower()
                    content = file.get('content', '')
                    
                    # Basic snippet extraction (would be AI-powered in production)
                    if extension in ['.py', '.js', '.ts', '.java', '.cs', '.php', '.rb', '.go']:
                        # For demo purposes, just extract functions/methods
                        # In a real system, this would use language-specific parsing
                        chunks = _split_code_content(content, extension)
                        
                        for i, chunk in enumerate(chunks):
                            if len(chunk.strip()) < 50 or len(chunk.strip()) > 1000:
                                continue
                            
                            # Hash the content for deduplication
                            content_hash = hashlib.sha256(chunk.encode()).hexdigest()
                            
                            snippets.append({
                                'project_id': project.id,
                                'filename': filename,
                                'extension': extension,
                                'content': chunk,
                                'content_hash': content_hash,
                                'extracted_at': datetime.datetime.utcnow().isoformat(),
                                'tags': _generate_tags(chunk, extension),
                                'title': _generate_title(chunk, extension)
                            })
        
        except Exception as e:
            logger.error(f"Error extracting snippets from project {project.id}: {str(e)}")
        
        return snippets
    
    @staticmethod
    def search_knowledge_base(query: str, language: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant snippets
        This would use vector search or similar in a production system
        """
        # This is a placeholder for a real search implementation
        # In production, this would use a search engine or vector database
        
        # For demo purposes, return some placeholder results
        results = [
            {
                'id': 'snippet-1',
                'title': 'User Authentication Helper',
                'content': '# Authentication helper functions\n\ndef validate_token(token):\n    """Validate JWT token"""\n    try:\n        # Token validation logic\n        return True\n    except Exception:\n        return False',
                'language': 'python',
                'tags': ['auth', 'security', 'jwt'],
                'similarity': 0.92,
                'project_id': 1,
                'created_at': '2025-03-15T14:30:00Z'
            },
            {
                'id': 'snippet-2',
                'title': 'Frontend Form Validation',
                'content': 'function validateForm(formData) {\n  // Check required fields\n  for (const field of requiredFields) {\n    if (!formData[field]) {\n      return { valid: false, error: `${field} is required` };\n    }\n  }\n  return { valid: true };\n}',
                'language': 'javascript',
                'tags': ['frontend', 'validation', 'forms'],
                'similarity': 0.85,
                'project_id': 2,
                'created_at': '2025-03-12T09:45:00Z'
            }
        ]
        
        # Filter by language if specified
        if language:
            results = [r for r in results if r.get('language') == language]
        
        # Filter by tags if specified
        if tags:
            results = [r for r in results if any(tag in r.get('tags', []) for tag in tags)]
        
        return results
    
    @staticmethod
    def add_snippet_to_knowledge_base(snippet: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Add a new snippet to the knowledge base
        """
        # Validate snippet
        required_fields = ['title', 'content', 'language']
        for field in required_fields:
            if field not in snippet:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate hash for deduplication
        content_hash = hashlib.sha256(snippet['content'].encode()).hexdigest()
        
        # Add metadata
        snippet['added_by'] = user_id
        snippet['added_at'] = datetime.datetime.utcnow().isoformat()
        snippet['content_hash'] = content_hash
        snippet['id'] = f"snippet-{content_hash[:8]}"
        
        # In a real implementation, we would store in a database
        # For now, just return the snippet with added metadata
        
        return snippet
    
    @staticmethod
    def get_related_snippets(snippet_id: str) -> List[Dict[str, Any]]:
        """
        Get snippets related to a specific snippet
        This would use similarity search in a production system
        """
        # This is a placeholder for a real implementation
        return []
    
    @staticmethod
    def get_popular_snippets(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most popular/used snippets
        """
        # This is a placeholder for a real implementation
        return []
    
    @staticmethod
    def get_user_snippets(user_id: int) -> List[Dict[str, Any]]:
        """
        Get snippets added by a specific user
        """
        # This is a placeholder for a real implementation
        return []

class DocumentationGenerator:
    """Generates documentation from code and project structures"""
    
    @staticmethod
    def generate_project_documentation(project: Project) -> Dict[str, Any]:
        """
        Generate comprehensive documentation for a project
        """
        try:
            documentation = {
                'project_id': project.id,
                'title': project.title,
                'description': project.description,
                'generated_at': datetime.datetime.utcnow().isoformat(),
                'sections': []
            }
            
            # Overview section
            documentation['sections'].append({
                'title': 'Overview',
                'content': project.description or 'No description provided.',
                'order': 1
            })
            
            # Architecture section (from refined_structure)
            if project.refined_structure:
                documentation['sections'].append({
                    'title': 'Architecture',
                    'content': project.refined_structure,
                    'order': 2
                })
            
            # Files section
            if project.files:
                try:
                    files = json.loads(project.files)
                    file_list = [file.get('name') for file in files if file.get('name')]
                    
                    documentation['sections'].append({
                        'title': 'Files',
                        'content': '* ' + '\n* '.join(file_list),
                        'order': 3
                    })
                    
                    # Generate documentation for each file
                    file_docs = []
                    for file in files:
                        filename = file.get('name')
                        content = file.get('content')
                        
                        if filename and content:
                            file_docs.append({
                                'filename': filename,
                                'documentation': _generate_file_documentation(filename, content)
                            })
                    
                    if file_docs:
                        documentation['file_documentation'] = file_docs
                
                except json.JSONDecodeError:
                    logger.error(f"Error parsing files JSON for project {project.id}")
            
            # Usage section
            documentation['sections'].append({
                'title': 'Usage',
                'content': 'This section describes how to use the project.',
                'order': 4
            })
            
            # API section (if applicable)
            # This would be generated from code analysis in a real implementation
            
            return documentation
            
        except Exception as e:
            logger.error(f"Error generating documentation for project {project.id}: {str(e)}")
            return {
                'project_id': project.id,
                'error': str(e)
            }
    
    @staticmethod
    def export_documentation(project_id: int, format: str = 'markdown') -> str:
        """
        Export project documentation in various formats
        """
        # Placeholder implementation
        if format == 'markdown':
            return "# Project Documentation\n\n## Overview\n\nThis is a placeholder for generated documentation."
        elif format == 'html':
            return "<h1>Project Documentation</h1><h2>Overview</h2><p>This is a placeholder for generated documentation.</p>"
        elif format == 'pdf':
            return "PDF generation not implemented"
        else:
            return f"Unsupported format: {format}"

class BestPracticesManager:
    """Manages best practices and coding standards"""
    
    @staticmethod
    def get_best_practices(category: str = None, language: str = None) -> List[Dict[str, Any]]:
        """
        Get best practices for a specific category and/or language
        """
        # Placeholder implementation with some common best practices
        practices = [
            {
                'id': 'bp-1',
                'title': 'Use meaningful variable names',
                'description': 'Variables should have descriptive names that indicate their purpose. Avoid single-letter variables except for simple loop counters.',
                'category': 'code_quality',
                'languages': ['any'],
                'example': '# Good\nuser_count = get_total_users()\n\n# Bad\nn = get_total_users()'
            },
            {
                'id': 'bp-2',
                'title': 'Handle exceptions properly',
                'description': 'Always catch specific exceptions rather than using a broad catch-all. Log exception details for debugging.',
                'category': 'error_handling',
                'languages': ['python', 'java', 'javascript'],
                'example': '# Good\ntry:\n    data = process_file(filename)\nexcept FileNotFoundError as e:\n    logger.error(f"File not found: {filename}")\nexcept PermissionError as e:\n    logger.error(f"Permission denied: {filename}")\n\n# Bad\ntry:\n    data = process_file(filename)\nexcept Exception as e:\n    print("Error")'
            },
            {
                'id': 'bp-3',
                'title': 'Use HTTPS for all communications',
                'description': 'Always use HTTPS instead of HTTP for all API calls and external communications to ensure data security.',
                'category': 'security',
                'languages': ['any'],
                'example': '# Good\nresponse = requests.get("https://api.example.com/data")\n\n# Bad\nresponse = requests.get("http://api.example.com/data")'
            },
            {
                'id': 'bp-4',
                'title': 'Validate user input',
                'description': 'Always validate and sanitize user input to prevent injection attacks and unexpected behavior.',
                'category': 'security',
                'languages': ['any'],
                'example': '# Good\nif not is_valid_username(username):\n    return "Invalid username"\n\n# Bad\nquery = f"SELECT * FROM users WHERE username = \'{username}\'"\n'
            }
        ]
        
        # Filter by category
        if category:
            practices = [p for p in practices if p.get('category') == category]
        
        # Filter by language
        if language:
            practices = [p for p in practices if language in p.get('languages', []) or 'any' in p.get('languages', [])]
        
        return practices
    
    @staticmethod
    def check_code_against_best_practices(code: str, language: str) -> List[Dict[str, Any]]:
        """
        Analyze code against best practices and return suggestions
        This would use AI analysis in a production system
        """
        # Placeholder implementation
        # In a real system, this would perform actual code analysis
        
        return [
            {
                'line': 12,
                'practice_id': 'bp-2',
                'message': 'Consider catching specific exceptions instead of Exception',
                'severity': 'warning'
            },
            {
                'line': 24,
                'practice_id': 'bp-4',
                'message': 'Potential SQL injection vulnerability. Use parameterized queries instead.',
                'severity': 'critical'
            }
        ]

# Helper functions

def _split_code_content(content: str, extension: str) -> List[str]:
    """Split code content into logical chunks (functions, classes, etc.)"""
    # Very basic implementation - in production this would use language-specific parsers
    if extension in ['.py']:
        # Simple Python function/class detection
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            if line.startswith('def ') or line.startswith('class '):
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    elif extension in ['.js', '.ts']:
        # Simple JavaScript/TypeScript function detection
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            if 'function ' in line or '=>' in line or 'class ' in line:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    # For other languages, just return the whole content as one chunk
    return [content]

def _generate_tags(content: str, extension: str) -> List[str]:
    """Generate tags for a code snippet based on content"""
    # Very basic implementation - in production this would use AI analysis
    tags = []
    
    # Add language tag based on extension
    if extension == '.py':
        tags.append('python')
    elif extension == '.js':
        tags.append('javascript')
    elif extension == '.ts':
        tags.append('typescript')
    elif extension == '.java':
        tags.append('java')
    elif extension == '.cs':
        tags.append('csharp')
    elif extension == '.php':
        tags.append('php')
    elif extension == '.rb':
        tags.append('ruby')
    elif extension == '.go':
        tags.append('go')
    
    # Check for common keywords
    if 'function' in content or 'def ' in content:
        tags.append('function')
    
    if 'class' in content:
        tags.append('class')
    
    if 'import' in content or 'require' in content:
        tags.append('module')
    
    if 'database' in content.lower() or 'sql' in content.lower():
        tags.append('database')
    
    if 'authentication' in content.lower() or 'auth' in content.lower():
        tags.append('authentication')
    
    if 'api' in content.lower() or 'rest' in content.lower():
        tags.append('api')
    
    return tags

def _generate_title(content: str, extension: str) -> str:
    """Generate a title for a code snippet based on content"""
    # Very basic implementation - in production this would use AI analysis
    lines = content.split('\n')
    
    # Try to find function or class definition
    for line in lines:
        if 'def ' in line:
            # Extract function name for Python
            parts = line.split('def ')[1].split('(')[0].strip()
            return f"Function: {parts}"
        elif 'function ' in line:
            # Extract function name for JavaScript
            parts = line.split('function ')[1].split('(')[0].strip()
            return f"Function: {parts}"
        elif 'class ' in line:
            # Extract class name
            parts = line.split('class ')[1].split('(')[0].split('{')[0].strip()
            return f"Class: {parts}"
    
    # Fallback - use first 30 chars
    first_line = lines[0].strip()
    if len(first_line) > 30:
        return first_line[:27] + '...'
    return first_line

def _generate_file_documentation(filename: str, content: str) -> Dict[str, Any]:
    """Generate documentation for a specific file"""
    return {
        'overview': f"Documentation for {filename}",
        'content_type': _determine_content_type(filename),
        'lines_of_code': len(content.split('\n')),
        'sections': []
    }

def _determine_content_type(filename: str) -> str:
    """Determine the type of a file based on filename"""
    extension = os.path.splitext(filename)[1].lower()
    
    if extension in ['.py']:
        return 'Python'
    elif extension in ['.js']:
        return 'JavaScript'
    elif extension in ['.ts']:
        return 'TypeScript'
    elif extension in ['.html']:
        return 'HTML'
    elif extension in ['.css']:
        return 'CSS'
    elif extension in ['.sql']:
        return 'SQL'
    elif extension in ['.md']:
        return 'Markdown'
    elif extension in ['.json']:
        return 'JSON'
    elif extension in ['.yaml', '.yml']:
        return 'YAML'
    elif extension in ['.java']:
        return 'Java'
    elif extension in ['.cs']:
        return 'C#'
    elif extension in ['.php']:
        return 'PHP'
    elif extension in ['.rb']:
        return 'Ruby'
    elif extension in ['.go']:
        return 'Go'
    else:
        return 'Unknown'