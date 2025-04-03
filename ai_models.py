import os
import json
import logging
import secrets
from datetime import datetime

from app import db
from models import User, Project

# Configure logging
logger = logging.getLogger(__name__)

class AIModelManager:
    """Manages AI model configurations and integrations for each HACF layer"""
    
    # Default models for each HACF layer
    DEFAULT_MODELS = {
        'layer1': {  # Task Definition & Planning Layer
            'name': 'meta-llama-3.1-405B-instruct-turbo',
            'provider': 'puter.js',
            'version': '2025-03-01',
            'capabilities': ['text-generation', 'task-planning', 'requirements-analysis'],
            'max_tokens': 16000,
            'temperature': 0.7,
            'description': 'Specialized for converting user requests into structured plans'
        },
        'layer2': {  # Refinement & Base Structure Layer
            'name': 'deepseek-reasoner',
            'provider': 'puter.js',
            'version': '2025-02-15',
            'capabilities': ['code-reasoning', 'architecture-design', 'technical-planning'],
            'max_tokens': 24000,
            'temperature': 0.4,
            'description': 'Specialized for technical roadmaps and base code structure'
        },
        'layer3': {  # Development & Execution Layer
            'name': 'codestral-latest',
            'provider': 'puter.js',
            'version': '2025-03-10',
            'capabilities': ['code-generation', 'full-stack-development', 'api-design'],
            'max_tokens': 32000,
            'temperature': 0.3,
            'description': 'Specialized for generating functional code from structured inputs'
        },
        'layer4': {  # Debugging, Optimization & Security Layer
            'name': 'gpt-4o',
            'provider': 'puter.js',
            'version': '2025-01-20',
            'capabilities': ['code-debugging', 'security-analysis', 'performance-optimization'],
            'max_tokens': 24000,
            'temperature': 0.2,
            'description': 'Specialized for reviewing, debugging and optimizing code'
        },
        'layer5': {  # Final Output Layer
            'name': 'claude-3-sonnet',
            'provider': 'puter.js',
            'version': '2025-02-28',
            'capabilities': ['code-formatting', 'documentation-generation', 'user-instruction'],
            'max_tokens': 16000,
            'temperature': 0.5,
            'description': 'Specialized for formatting and preparing final output'
        }
    }
    
    # Available AI model providers
    AVAILABLE_PROVIDERS = {
        'puter.js': {
            'name': 'Puter.js Native Models',
            'description': 'Built-in AI capabilities of the Puter.js platform',
            'requires_api_key': False,
            'models': [
                'meta-llama-3.1-405B-instruct-turbo',
                'deepseek-reasoner',
                'codestral-latest',
                'gpt-4o',
                'claude-3-sonnet',
                'yi-34b',
                'mistral-large',
                'wizard-math'
            ]
        },
        'openai': {
            'name': 'OpenAI',
            'description': 'Models from OpenAI like GPT-4o and GPT-4 Turbo',
            'requires_api_key': True,
            'api_key_env': 'OPENAI_API_KEY',
            'models': [
                'gpt-4o',
                'gpt-4-turbo',
                'gpt-4-vision',
                'gpt-3.5-turbo'
            ]
        },
        'anthropic': {
            'name': 'Anthropic',
            'description': 'Claude series of models from Anthropic',
            'requires_api_key': True,
            'api_key_env': 'ANTHROPIC_API_KEY',
            'models': [
                'claude-3-opus',
                'claude-3-sonnet',
                'claude-3-haiku',
                'claude-2.1'
            ]
        },
        'perplexity': {
            'name': 'Perplexity',
            'description': 'Research-focused models with online search capabilities',
            'requires_api_key': True,
            'api_key_env': 'PERPLEXITY_API_KEY',
            'models': [
                'llama-3.1-sonar-small-128k-online',
                'llama-3.1-sonar-large-128k-online',
                'llama-3.1-sonar-huge-128k-online'
            ]
        },
        'xai': {
            'name': 'xAI',
            'description': 'Grok series of models from xAI',
            'requires_api_key': True,
            'api_key_env': 'XAI_API_KEY',
            'models': [
                'grok-2-1212',
                'grok-2-vision-1212',
                'grok-vision-beta',
                'grok-beta'
            ]
        }
    }
    
    @classmethod
    def get_model_config(cls, layer, user=None, project=None):
        """
        Get model configuration for a specific layer
        Checks user preferences and project-specific settings before falling back to defaults
        """
        # Default configuration
        config = cls.DEFAULT_MODELS.get(f'layer{layer}', {})
        
        # If project is specified, check for project-specific model configuration
        if project and hasattr(project, 'metadata'):
            try:
                metadata = json.loads(project.metadata) if project.metadata else {}
                project_models = metadata.get('models', {})
                layer_config = project_models.get(f'layer{layer}')
                
                if layer_config:
                    # Merge with defaults, allowing project settings to override
                    config.update(layer_config)
            except Exception as e:
                logger.error(f"Error parsing project model config: {str(e)}")
        
        # If user is specified, check for user preferences
        if user and hasattr(user, 'ai_model_preferences'):
            try:
                preferences = json.loads(user.ai_model_preferences) if user.ai_model_preferences else {}
                user_model = preferences.get(f'layer{layer}')
                
                if user_model:
                    # Merge with existing config, allowing user preferences to override
                    config.update(user_model)
            except Exception as e:
                logger.error(f"Error parsing user model preferences: {str(e)}")
        
        return config
    
    @classmethod
    def is_model_available(cls, model_name, provider='puter.js'):
        """Check if a specific model is available from a provider"""
        if provider not in cls.AVAILABLE_PROVIDERS:
            return False
        
        provider_info = cls.AVAILABLE_PROVIDERS[provider]
        
        # Check if model is in provider's list
        if model_name not in provider_info['models']:
            return False
        
        # If API key is required, check if it's available
        if provider_info['requires_api_key']:
            api_key_env = provider_info.get('api_key_env')
            if not api_key_env or not os.environ.get(api_key_env):
                return False
        
        return True
    
    @classmethod
    def get_available_models(cls, include_external=False):
        """Get list of available models, optionally including those from external providers"""
        available_models = {}
        
        # Always include Puter.js models
        available_models['puter.js'] = cls.AVAILABLE_PROVIDERS['puter.js']['models']
        
        # Include external providers if requested
        if include_external:
            for provider, info in cls.AVAILABLE_PROVIDERS.items():
                if provider == 'puter.js':
                    continue
                
                # Check if API key is available
                if info['requires_api_key']:
                    api_key_env = info.get('api_key_env')
                    if api_key_env and os.environ.get(api_key_env):
                        available_models[provider] = info['models']
                else:
                    available_models[provider] = info['models']
        
        return available_models
    
    @classmethod
    def get_model_capabilities(cls, model_name):
        """Get capabilities of a specific model"""
        # Search for model in all providers
        for provider, info in cls.AVAILABLE_PROVIDERS.items():
            if model_name in info['models']:
                # For now, return generic capabilities based on model name
                capabilities = []
                
                if 'gpt-4' in model_name or 'gpt-3.5' in model_name:
                    capabilities = ['text-generation', 'code-generation']
                    if 'vision' in model_name:
                        capabilities.append('image-understanding')
                
                elif 'claude' in model_name:
                    capabilities = ['text-generation', 'code-generation', 'reasoning']
                    if '3' in model_name:
                        capabilities.append('image-understanding')
                
                elif 'llama' in model_name:
                    capabilities = ['text-generation', 'code-generation']
                    if 'sonar' in model_name:
                        capabilities.append('online-search')
                
                elif 'grok' in model_name:
                    capabilities = ['text-generation', 'code-generation']
                    if 'vision' in model_name:
                        capabilities.append('image-understanding')
                
                elif 'codestral' in model_name:
                    capabilities = ['code-generation', 'code-completion', 'code-explanation']
                
                elif 'deepseek' in model_name:
                    capabilities = ['code-reasoning', 'math-problem-solving']
                
                return capabilities
        
        return []
    
    @classmethod
    def update_user_model_preferences(cls, user, layer, model_config):
        """Update a user's model preferences for a specific layer"""
        if not user:
            return False
        
        try:
            # Get current preferences
            preferences = json.loads(user.ai_model_preferences) if user.ai_model_preferences else {}
            
            # Update layer configuration
            preferences[f'layer{layer}'] = model_config
            
            # Save back to user
            user.ai_model_preferences = json.dumps(preferences)
            db.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error updating user model preferences: {str(e)}")
            return False
    
    @classmethod
    def update_project_model_config(cls, project, layer, model_config):
        """Update a project's model configuration for a specific layer"""
        if not project:
            return False
        
        try:
            # Get current metadata
            metadata = json.loads(project.metadata) if project.metadata else {}
            
            # Ensure models field exists
            if 'models' not in metadata:
                metadata['models'] = {}
            
            # Update layer configuration
            metadata['models'][f'layer{layer}'] = model_config
            
            # Save back to project
            project.metadata = json.dumps(metadata)
            db.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error updating project model config: {str(e)}")
            return False

# AI model fine-tuning manager
class AIModelFineTuningManager:
    """Manages fine-tuning of AI models for specific use cases"""
    
    # Fine-tuning status constants
    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    @classmethod
    def create_fine_tuning_job(cls, user_id, model_name, training_data, description=None):
        """
        Create a new fine-tuning job for a model
        This is a placeholder for actual implementation that would integrate with model providers
        """
        # In a real implementation, this would:
        # 1. Format and validate training data
        # 2. Submit to appropriate API (OpenAI, etc.)
        # 3. Create record in database to track progress
        
        job_id = f"ft-{secrets.token_hex(8)}"
        
        return {
            'job_id': job_id,
            'user_id': user_id,
            'model_name': model_name,
            'base_model': model_name.split(':')[0] if ':' in model_name else model_name,
            'status': cls.STATUS_QUEUED,
            'created_at': datetime.utcnow().isoformat(),
            'description': description,
            'message': 'Fine-tuning job created and queued'
        }
    
    @classmethod
    def get_fine_tuning_job_status(cls, job_id):
        """
        Check status of a fine-tuning job
        This is a placeholder for actual implementation
        """
        # In a real implementation, this would query the database or API
        return {
            'job_id': job_id,
            'status': cls.STATUS_PROCESSING,
            'progress': 42,  # Percentage
            'message': 'Fine-tuning in progress',
            'estimated_completion': '2 hours'
        }
    
    @classmethod
    def list_fine_tuned_models(cls, user_id):
        """
        List all fine-tuned models for a user
        This is a placeholder for actual implementation
        """
        # In a real implementation, this would query the database
        return [
            {
                'id': 'ft-model-1',
                'name': 'custom-code-assistant',
                'base_model': 'codestral-latest',
                'created_at': '2025-03-15T14:30:00Z',
                'status': 'active'
            }
        ]