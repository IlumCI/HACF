import json
import logging
import random
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

from app import db
from models import User, Project

# Configure logging
logger = logging.getLogger(__name__)

class AdaptiveLayerSequencer:
    """
    Implements adaptive sequencing of HACF layers based on project complexity,
    domain context, and feedback loops.
    
    This moves beyond the traditional linear flow to create a dynamic,
    project-specific approach to HACF layer execution.
    """
    
    # Layer complexity factors
    COMPLEXITY_FACTORS = {
        'code_size': {
            'threshold_low': 1000,   # characters
            'threshold_medium': 5000,
            'threshold_high': 20000
        },
        'domain_complexity': {
            'low': ['landing_page', 'portfolio', 'simple_blog'],
            'medium': ['e_commerce', 'content_management', 'data_visualization'],
            'high': ['financial_system', 'healthcare_app', 'ai_system', 'security_critical']
        },
        'feature_count': {
            'threshold_low': 3,
            'threshold_medium': 8,
            'threshold_high': 15
        },
        'integration_count': {
            'threshold_low': 1,
            'threshold_medium': 3,
            'threshold_high': 6
        }
    }
    
    # Layer transition networks - defines how layers can connect in non-linear ways
    # Enhanced layer definitions (12 total layers)
    # Layer 0: Requirement Validation (validation, stakeholder feedback, early constraints)
    # Layer 1: Task Definition (goals, requirements, constraints)
    # Layer 2: Analysis & Research (market research, competitor analysis, technology assessment)
    # Layer 3: Refinement (architecture, technology selection, planning)
    # Layer 4: Prototyping (rapid prototyping, concept validation, visual representation)
    # Layer 5: Development (coding, implementation)
    # Layer 6: Testing & Quality Assurance (unit testing, integration testing, QA)
    # Layer 7: Optimization (debugging, performance, security)
    # Layer 8: Deployment Preparation (infrastructure setup, CI/CD, environment provisioning)
    # Layer 9: Final Output (documentation, packaging, delivery)
    # Layer 10: Monitoring & Feedback (monitoring setup, feedback collection, analytics)
    # Layer 11: Evolution & Maintenance (maintenance planning, roadmap, technical debt management)
    
    # Layer names, descriptions, and associated AI models
    HACF_LAYERS = {
        0: {
            'name': 'Requirement Validation',
            'description': 'Validates project requirements, gathers stakeholder feedback, and identifies early constraints',
            'model': 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',
            'responsibilities': [
                'Validate user requirements for clarity and completeness',
                'Gather and incorporate stakeholder feedback',
                'Identify early project constraints and limitations',
                'Perform initial feasibility assessment',
                'Establish acceptance criteria'
            ]
        },
        1: {
            'name': 'Task Definition',
            'description': 'Defines project goals, detailed requirements, and constraints',
            'model': 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',
            'responsibilities': [
                'Convert user requirements into structured project plans',
                'Define clear project goals and objectives',
                'Outline constraints and limitations',
                'Create initial project scope definition',
                'Structure requirements into actionable tasks'
            ]
        },
        2: {
            'name': 'Analysis & Research',
            'description': 'Conducts market research, competitor analysis, and technology assessment',
            'model': 'deepseek-reasoner',
            'responsibilities': [
                'Perform market and competitor analysis',
                'Evaluate available technologies and tools',
                'Research similar solutions and best practices',
                'Analyze technical feasibility of requirements',
                'Identify potential challenges and risks'
            ]
        },
        3: {
            'name': 'Refinement',
            'description': 'Creates system architecture, selects appropriate technologies, and develops a detailed plan',
            'model': 'deepseek-reasoner',
            'responsibilities': [
                'Define system architecture and components',
                'Select optimal technologies and frameworks',
                'Create detailed implementation plan',
                'Design data models and relationships',
                'Ensure technical consistency across components'
            ]
        },
        4: {
            'name': 'Prototyping',
            'description': 'Builds rapid prototypes, validates concepts, and creates visual representations',
            'model': 'codestral-latest',
            'responsibilities': [
                'Develop proof-of-concept implementations',
                'Create UI/UX mockups and wireframes',
                'Build functional prototypes for validation',
                'Test critical functionality assumptions',
                'Gather early feedback on design concepts'
            ]
        },
        5: {
            'name': 'Development',
            'description': 'Implements full code solutions based on approved designs and prototypes',
            'model': 'codestral-latest',
            'responsibilities': [
                'Write production-ready code',
                'Implement frontend and backend components',
                'Develop database schema and interactions',
                'Create APIs and service integrations',
                'Follow coding standards and best practices'
            ]
        },
        6: {
            'name': 'Testing & Quality Assurance',
            'description': 'Performs comprehensive testing including unit, integration, and quality assessment',
            'model': 'claude-3-7-sonnet',
            'responsibilities': [
                'Develop and execute unit tests',
                'Perform integration and system testing',
                'Conduct user acceptance testing',
                'Ensure code quality and standards compliance',
                'Validate functionality against requirements'
            ]
        },
        7: {
            'name': 'Optimization',
            'description': 'Debugs code, improves performance, and enhances security measures',
            'model': 'gpt-4o',
            'responsibilities': [
                'Identify and fix bugs and issues',
                'Optimize performance and resource usage',
                'Implement security enhancements',
                'Refactor code for readability and maintainability',
                'Conduct code reviews and address feedback'
            ]
        },
        8: {
            'name': 'Deployment Preparation',
            'description': 'Sets up infrastructure, configures CI/CD pipelines, and provisions environments',
            'model': 'gpt-4o',
            'responsibilities': [
                'Configure deployment environments',
                'Set up continuous integration/deployment pipelines',
                'Prepare infrastructure for production',
                'Configure monitoring and logging solutions',
                'Create deployment and rollback procedures'
            ]
        },
        9: {
            'name': 'Final Output',
            'description': 'Creates comprehensive documentation, packages deliverables, and finalizes delivery',
            'model': 'claude-3-7-sonnet',
            'responsibilities': [
                'Generate comprehensive documentation',
                'Package code and assets for delivery',
                'Create user guides and instructions',
                'Prepare project handover materials',
                'Ensure all deliverables meet quality standards'
            ]
        },
        10: {
            'name': 'Monitoring & Feedback',
            'description': 'Establishes monitoring systems, collects user feedback, and implements analytics',
            'model': 'gpt-4o',
            'responsibilities': [
                'Set up application and performance monitoring',
                'Implement feedback collection mechanisms',
                'Configure analytics and reporting',
                'Create dashboards and visualization tools',
                'Establish alerting and notification systems'
            ]
        },
        11: {
            'name': 'Evolution & Maintenance',
            'description': 'Plans ongoing maintenance, creates future roadmaps, and manages technical debt',
            'model': 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',
            'responsibilities': [
                'Develop maintenance and support plans',
                'Create feature roadmap for future development',
                'Manage and prioritize technical debt',
                'Plan for scalability and future enhancements',
                'Document long-term sustainability strategies'
            ]
        }
    }
    
    LAYER_TRANSITION_NETWORKS = {
        'standard': {
            0: [1],           # From layer 0, can only go to layer 1
            1: [2],           # From layer 1, can only go to layer 2
            2: [3],           # From layer 2, can only go to layer 3
            3: [4],           # From layer 3, can only go to layer 4
            4: [5],           # From layer 4, can only go to layer 5
            5: [6],           # From layer 5, can only go to layer 6
            6: [7],           # From layer 6, can only go to layer 7
            7: [8],           # From layer 7, can only go to layer 8
            8: [9],           # From layer 8, can only go to layer 9
            9: [10],          # From layer 9, can only go to layer 10
            10: [11],         # From layer 10, can only go to layer 11
            11: []            # Terminal layer
        },
        'agile': {
            0: [1],           # Always start with requirement validation
            1: [2, 3],        # Can skip analysis & go straight to refinement
            2: [3, 4],        # Can go to refinement or skip to prototyping
            3: [4, 5],        # Can go to prototyping or skip to development
            4: [3, 5, 6],     # Can loop back to refinement or move forward
            5: [4, 6, 7],     # Can loop back to prototype or move forward
            6: [5, 7, 8],     # Can loop back to development or move forward
            7: [5, 6, 8, 9],  # Can loop back or skip forward
            8: [7, 9, 10],    # Can loop back or move forward
            9: [10, 7, 8],    # Can loop back to optimize/deploy or move forward
            10: [11, 7, 8, 9], # Can loop back for improvements
            11: [7, 10]       # Can loop back for optimizations or monitoring
        },
        'research': {
            0: [1, 2],        # Can skip task definition for research projects
            1: [0, 2, 3, 4],  # More flexible transitions 
            2: [1, 3, 4, 5],  # Can move in multiple directions
            3: [1, 2, 4, 5, 6],
            4: [2, 3, 5, 6, 7],
            5: [3, 4, 6, 7, 8],
            6: [4, 5, 7, 8, 9],
            7: [5, 6, 8, 9, 10],
            8: [6, 7, 9, 10, 11],
            9: [7, 8, 10, 11],
            10: [7, 8, 9, 11],
            11: [7, 8, 9, 10]  # Can restart from multiple points
        },
        'security_focused': {
            0: [1],
            1: [2],
            2: [3],
            3: [4],
            4: [5, 6],        # Can skip development for security assessment
            5: [6, 3, 4],     # Loop between development and prototyping
            6: [7, 5, 4],     # Security concerns can send back to earlier layers
            7: [8, 6, 5],     # Security optimization can require dev changes
            8: [9, 7, 6],     # Deployment prep may need security fixes
            9: [10, 7, 8],    # Documentation may need security updates
            10: [11, 7],      # Monitoring setup may reveal security issues
            11: [7, 10]       # Maintenance may require security updates
        },
        'iterative_development': {
            0: [1],
            1: [2],
            2: [3],
            3: [4],
            4: [5],
            5: [5, 6],        # Can repeat development layer
            6: [5, 7],        # Can return to development based on testing
            7: [5, 6, 8],     # Can return to development or testing from optimization
            8: [7, 9],        # Can return to optimization from deployment prep
            9: [5, 7, 8, 10], # Can loop back for improvements
            10: [7, 11],      # Can return to optimization based on monitoring
            11: [5, 7, 10]    # Can iterate on maintenance
        }
    }
    
    # Special adjustment factors for industry-specific workflows
    INDUSTRY_ADJUSTMENTS = {
        'healthcare': {
            'layer_weights': {
                1: 1.2,  # More emphasis on clear task definition for regulatory compliance
                2: 1.5,  # More architecture planning for HIPAA compliance
                3: 1.0,
                4: 1.8,  # Heavy emphasis on security/optimization for PHI
                5: 1.3   # More detailed documentation requirements
            },
            'preferred_network': 'security_focused'
        },
        'finance': {
            'layer_weights': {
                1: 1.1,
                2: 1.2,
                3: 1.0,
                4: 2.0,  # Extremely high focus on security and validation
                5: 1.5   # Detailed audit trail and documentation
            },
            'preferred_network': 'security_focused'
        },
        'education': {
            'layer_weights': {
                1: 1.5,  # Higher emphasis on clear requirements for educational outcomes
                2: 1.0,
                3: 1.0,
                4: 0.8,  # Less emphasis on optimization (more on usability)
                5: 1.7   # Very high focus on final documentation and instructions
            },
            'preferred_network': 'agile'
        },
        'startup': {
            'layer_weights': {
                1: 0.9,  # Move faster, define less upfront
                2: 0.8,
                3: 1.2,  # Emphasis on development speed
                4: 0.7,  # Less initial optimization
                5: 0.7   # Less documentation
            },
            'preferred_network': 'iterative_development'
        },
        'government': {
            'layer_weights': {
                1: 1.8,  # Extensive requirements gathering
                2: 1.5,  # Detailed planning
                3: 1.0,
                4: 1.3,  # Security focus
                5: 1.9   # Comprehensive documentation
            },
            'preferred_network': 'standard'
        },
        'research': {
            'layer_weights': {
                1: 1.3,  # Careful problem definition
                2: 1.1,
                3: 1.0,
                4: 1.0,
                5: 1.5   # Detailed findings and documentation
            },
            'preferred_network': 'research'
        }
    }
    
    @classmethod
    def calculate_project_complexity(cls, project: Project) -> Dict[str, Any]:
        """Calculate the complexity profile of a project"""
        if not project:
            return {'overall': 'medium', 'factors': {}}
            
        try:
            # This would be calculated from actual project data in production
            # Here we're creating a demonstration version
            
            metadata = json.loads(project.metadata) if project.metadata else {}
            domain = metadata.get('domain', 'general')
            industry = metadata.get('industry', 'technology')
            
            # Estimated code size (would be calculated from actual files)
            code_size = metadata.get('estimated_code_size', 4500)
            
            # Feature count from project requirements
            feature_list = metadata.get('features', [])
            feature_count = len(feature_list)
            
            # Integration count
            integrations = metadata.get('integrations', [])
            integration_count = len(integrations)
            
            # Calculate complexity for each factor
            factors = {}
            
            # Code size complexity
            if code_size < cls.COMPLEXITY_FACTORS['code_size']['threshold_low']:
                factors['code_size'] = 'low'
            elif code_size < cls.COMPLEXITY_FACTORS['code_size']['threshold_medium']:
                factors['code_size'] = 'medium'
            else:
                factors['code_size'] = 'high'
                
            # Domain complexity
            domain_complexity = 'medium'  # Default
            for level, domains in cls.COMPLEXITY_FACTORS['domain_complexity'].items():
                if domain in domains:
                    domain_complexity = level
                    break
            factors['domain_complexity'] = domain_complexity
            
            # Feature count complexity
            if feature_count < cls.COMPLEXITY_FACTORS['feature_count']['threshold_low']:
                factors['feature_count'] = 'low'
            elif feature_count < cls.COMPLEXITY_FACTORS['feature_count']['threshold_medium']:
                factors['feature_count'] = 'medium'
            else:
                factors['feature_count'] = 'high'
                
            # Integration complexity
            if integration_count < cls.COMPLEXITY_FACTORS['integration_count']['threshold_low']:
                factors['integration_count'] = 'low'
            elif integration_count < cls.COMPLEXITY_FACTORS['integration_count']['threshold_medium']:
                factors['integration_count'] = 'medium'
            else:
                factors['integration_count'] = 'high'
                
            # Calculate overall complexity
            complexity_scores = {
                'low': 1,
                'medium': 2,
                'high': 3
            }
            
            # Weight the factors (could be adjusted based on industry)
            weights = {
                'code_size': 0.25,
                'domain_complexity': 0.35,
                'feature_count': 0.2,
                'integration_count': 0.2
            }
            
            weighted_score = 0
            for factor, level in factors.items():
                weighted_score += complexity_scores[level] * weights[factor]
                
            # Determine overall complexity
            overall = 'medium'  # Default
            if weighted_score < 1.67:
                overall = 'low'
            elif weighted_score > 2.33:
                overall = 'high'
                
            return {
                'overall': overall,
                'factors': factors,
                'score': weighted_score,
                'industry': industry
            }
            
        except Exception as e:
            logger.error(f"Error calculating project complexity: {str(e)}")
            return {'overall': 'medium', 'factors': {}}
    
    @classmethod
    def determine_layer_sequence(cls, project: Project, session_id: str = None, 
                                feedback: Optional[Dict[str, Any]] = None) -> List[int]:
        """
        Determine the optimal sequence of HACF layers for a project
        
        This creates a custom execution path through the HACF framework
        based on project characteristics and previous outputs
        """
        try:
            # Calculate project complexity
            complexity = cls.calculate_project_complexity(project)
            overall_complexity = complexity['overall']
            industry = complexity.get('industry', 'technology')
            
            # Get metadata
            metadata = json.loads(project.metadata) if project.metadata else {}
            project_type = metadata.get('project_type', 'web_application')
            
            # Select appropriate transition network
            network_type = 'standard'  # Default
            
            # Check for industry-specific network
            if industry in cls.INDUSTRY_ADJUSTMENTS:
                network_type = cls.INDUSTRY_ADJUSTMENTS[industry].get('preferred_network', 'standard')
                
            # Override based on project type
            if project_type == 'research_poc':
                network_type = 'research'
            elif project_type == 'security_critical':
                network_type = 'security_focused'
            elif project_type == 'mvp' or project_type == 'prototype':
                network_type = 'iterative_development'
            elif project_type == 'agile_project':
                network_type = 'agile'
                
            # Get the selected transition network
            transition_network = cls.LAYER_TRANSITION_NETWORKS.get(network_type, 
                                                               cls.LAYER_TRANSITION_NETWORKS['standard'])
            
            # If we have feedback from a previous HACF session
            if feedback and session_id:
                # Use feedback to influence next layer selection
                # Higher satisfaction means more likely to follow standard path
                # Lower satisfaction means more likely to take alternative paths
                satisfaction = feedback.get('satisfaction', 0.7)  # Default moderate satisfaction
                
                # Get current layer from session
                # For now, we'll just use a default value 
                # In a real implementation, we would query the database
                current_layer = 1
                
                # Get possible next layers
                possible_next_layers = transition_network.get(current_layer, [])
                
                if not possible_next_layers:
                    return [5]  # Default to final layer if no transitions defined
                
                # Default path is first in list (usually the standard next layer)
                standard_next_layer = possible_next_layers[0] if possible_next_layers else current_layer + 1
                
                # If high satisfaction (> 0.8), follow standard path
                if satisfaction > 0.8:
                    return [standard_next_layer]
                
                # If low satisfaction (< 0.4), consider alternative paths more strongly
                if satisfaction < 0.4:
                    # More likely to select an alternative path or even reprocess the current layer
                    if len(possible_next_layers) > 1:
                        # Exclude the standard path from alternatives
                        alternatives = [layer for layer in possible_next_layers if layer != standard_next_layer]
                        if alternatives:
                            # With low satisfaction, 70% chance of taking alternative path
                            if random.random() < 0.7:
                                return [random.choice(alternatives)]
                    
                    # 30% chance of reprocessing current layer with adjustments
                    if random.random() < 0.3:
                        return [current_layer]
                
                # Moderate satisfaction - standard path with some chance of alternatives
                if len(possible_next_layers) > 1:
                    alternatives = [layer for layer in possible_next_layers if layer != standard_next_layer]
                    if alternatives and random.random() < 0.3:  # 30% chance of alternative path
                        return [random.choice(alternatives)]
                
                return [standard_next_layer]
            
            # For new sessions, create a full path plan
            current_layer = 1
            path = [current_layer]
            
            # Generate a projected path through the network
            # This is just a plan - actual execution may deviate based on feedback
            while current_layer != 5 and len(path) < 10:  # Limit to 10 steps to prevent infinite loops
                possible_next_layers = transition_network.get(current_layer, [])
                
                if not possible_next_layers:
                    if current_layer < 5:
                        current_layer += 1  # Default progression if not specified
                    else:
                        break  # End if we're already at or past layer 5
                else:
                    # For initial planning, choose the most probable path
                    # This is usually the first option in the network definition
                    current_layer = possible_next_layers[0]
                    
                path.append(current_layer)
                
                # For complex projects in agile or iterative networks, 
                # add some repetition of development/optimization layers
                if (overall_complexity == 'high' and 
                    network_type in ['agile', 'iterative_development'] and
                    current_layer in [3, 4] and
                    random.random() < 0.4):  # 40% chance of repeating these layers
                    path.append(current_layer)  # Repeat the layer
            
            return path
            
        except Exception as e:
            logger.error(f"Error determining layer sequence: {str(e)}")
            return [1, 2, 3, 4, 5]  # Default to standard sequence
    
    @classmethod
    def get_layer_execution_parameters(cls, project: Project, layer: int) -> Dict[str, Any]:
        """
        Get execution parameters for a specific layer based on project characteristics
        """
        try:
            complexity = cls.calculate_project_complexity(project)
            industry = complexity.get('industry', 'technology')
            overall_complexity = complexity['overall']
            
            # Base parameters
            parameters = {
                'max_tokens': 4000,
                'temperature': 0.7,
                'depth': 'standard',
                'focus_areas': []
            }
            
            # Adjust based on layer
            if layer == 1:  # Task Definition
                parameters['max_tokens'] = 3000
                parameters['temperature'] = 0.8  # More creative in requirements gathering
                parameters['focus_areas'] = ['requirements', 'constraints', 'user_stories']
                
            elif layer == 2:  # Refinement
                parameters['max_tokens'] = 4000
                parameters['temperature'] = 0.6  # More precise in architecture
                parameters['focus_areas'] = ['architecture', 'technical_planning', 'data_model']
                
            elif layer == 3:  # Development
                parameters['max_tokens'] = 6000
                parameters['temperature'] = 0.4  # More precise in code generation
                parameters['focus_areas'] = ['code_generation', 'implementation', 'apis']
                
            elif layer == 4:  # Optimization
                parameters['max_tokens'] = 5000
                parameters['temperature'] = 0.3  # Very precise in optimization
                parameters['focus_areas'] = ['performance', 'security', 'debugging']
                
            elif layer == 5:  # Final Output
                parameters['max_tokens'] = 4000
                parameters['temperature'] = 0.5  # Balanced for documentation
                parameters['focus_areas'] = ['documentation', 'user_guide', 'deployment']
            
            # Adjust parameters based on complexity
            complexity_adjustments = {
                'low': {
                    'max_tokens_factor': 0.8,
                    'temperature_adjustment': 0.1,  # Increase temperature (more creative)
                    'depth': 'basic'
                },
                'medium': {
                    'max_tokens_factor': 1.0,
                    'temperature_adjustment': 0.0,  # No change
                    'depth': 'standard'
                },
                'high': {
                    'max_tokens_factor': 1.5,  # Use more tokens for complex projects
                    'temperature_adjustment': -0.1,  # Decrease temperature (more precise)
                    'depth': 'comprehensive'
                }
            }
            
            adj = complexity_adjustments[overall_complexity]
            parameters['max_tokens'] = int(parameters['max_tokens'] * adj['max_tokens_factor'])
            parameters['temperature'] = max(0.1, min(1.0, parameters['temperature'] + adj['temperature_adjustment']))
            parameters['depth'] = adj['depth']
            
            # Apply industry-specific adjustments
            if industry in cls.INDUSTRY_ADJUSTMENTS:
                industry_adj = cls.INDUSTRY_ADJUSTMENTS[industry]
                layer_weight = industry_adj['layer_weights'].get(layer, 1.0)
                
                # Apply weight to max_tokens
                parameters['max_tokens'] = int(parameters['max_tokens'] * layer_weight)
                
                # Add industry-specific focus areas
                if industry == 'healthcare' and layer == 4:
                    parameters['focus_areas'].extend(['hipaa_compliance', 'phi_security'])
                elif industry == 'finance' and layer == 4:
                    parameters['focus_areas'].extend(['financial_regulations', 'transaction_security'])
                elif industry == 'education' and layer == 5:
                    parameters['focus_areas'].extend(['accessibility', 'learning_outcomes'])
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error getting layer execution parameters: {str(e)}")
            return {
                'max_tokens': 4000,
                'temperature': 0.7,
                'depth': 'standard',
                'focus_areas': []
            }


class CrossLayerMemory:
    """
    Implements a sophisticated cross-layer memory system that maintains context
    and insights across different HACF layers.
    
    This creates a shared understanding that evolves throughout the project lifecycle,
    allowing decisions in one layer to influence operations in other layers.
    """
    
    # Memory types
    MEMORY_TYPES = {
        'decision': {
            'description': 'Key decisions made during the process',
            'priority': 'high'
        },
        'constraint': {
            'description': 'Limitations or requirements that must be honored',
            'priority': 'critical'
        },
        'insight': {
            'description': 'Important observations about the project or code',
            'priority': 'medium'
        },
        'error': {
            'description': 'Problems encountered that should be avoided',
            'priority': 'high'
        },
        'preference': {
            'description': 'User or system preferences that guide development',
            'priority': 'medium'
        },
        'context': {
            'description': 'Background information that aids understanding',
            'priority': 'low'
        },
        'artifact': {
            'description': 'Created code, documentation, or other outputs',
            'priority': 'medium'
        }
    }
    
    # Memory priority weights (for retrieval)
    PRIORITY_WEIGHTS = {
        'critical': 1.0,
        'high': 0.8,
        'medium': 0.5,
        'low': 0.3
    }
    
    # Layer relevance matrix - how relevant memories from one layer are to other layers
    # Values range from 0.0 (not relevant) to 1.0 (highly relevant)
    LAYER_RELEVANCE = {
        1: {  # Relevance of Layer 1 memories to each layer
            1: 1.0,  # To itself
            2: 0.9,  # Layer 1 memories are highly relevant to Layer 2
            3: 0.7,  # Layer 1 memories are moderately relevant to Layer 3
            4: 0.5,  # Layer 1 memories are somewhat relevant to Layer 4
            5: 0.8   # Layer 1 memories are highly relevant to Layer 5 (for documentation)
        },
        2: {  # Relevance of Layer 2 memories to each layer
            1: 0.4,  # Layer 2 memories have limited relevance to Layer 1
            2: 1.0,  # To itself
            3: 0.9,  # Layer 2 memories are highly relevant to Layer 3
            4: 0.7,  # Layer 2 memories are moderately relevant to Layer 4
            5: 0.7   # Layer 2 memories are moderately relevant to Layer 5
        },
        3: {  # Relevance of Layer 3 memories to each layer
            1: 0.2,  # Layer 3 memories have minimal relevance to Layer 1
            2: 0.5,  # Layer 3 memories have some relevance to Layer 2
            3: 1.0,  # To itself
            4: 0.9,  # Layer 3 memories are highly relevant to Layer 4
            5: 0.8   # Layer 3 memories are highly relevant to Layer 5
        },
        4: {  # Relevance of Layer 4 memories to each layer
            1: 0.3,  # Layer 4 memories have some relevance to Layer 1
            2: 0.6,  # Layer 4 memories have moderate relevance to Layer 2
            3: 0.8,  # Layer 4 memories are highly relevant to Layer 3
            4: 1.0,  # To itself
            5: 0.9   # Layer 4 memories are highly relevant to Layer 5
        },
        5: {  # Relevance of Layer 5 memories to each layer
            1: 0.2,  # Layer 5 memories have minimal relevance to Layer 1
            2: 0.3,  # Layer 5 memories have limited relevance to Layer 2
            3: 0.4,  # Layer 5 memories have some relevance to Layer 3
            4: 0.5,  # Layer 5 memories have moderate relevance to Layer 4
            5: 1.0   # To itself
        }
    }
    
    @classmethod
    def create_memory(cls, session_id: str, layer: int, memory_type: str, 
                     content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new memory entry for the cross-layer memory system
        """
        if memory_type not in cls.MEMORY_TYPES:
            memory_type = 'context'  # Default to context if type not recognized
            
        priority = cls.MEMORY_TYPES[memory_type]['priority']
        
        # Generate a unique memory ID
        memory_id = f"mem-{session_id}-{layer}-{random.randint(1000, 9999)}"
        
        # Create the memory object
        memory = {
            'id': memory_id,
            'session_id': session_id,
            'created_at': datetime.utcnow().isoformat(),
            'source_layer': layer,
            'type': memory_type,
            'priority': priority,
            'content': content,
            'metadata': metadata or {},
            'usage_count': 0,
            'last_accessed': None
        }
        
        # In a production system, this would be stored in the database
        # For this implementation, we're returning the memory object directly
        # In a real implementation, this would store to a database table
        
        return memory
    
    @classmethod
    def get_relevant_memories(cls, session_id: str, current_layer: int, 
                             keywords: Optional[List[str]] = None,
                             memory_types: Optional[List[str]] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve memories relevant to the current layer, filtered by keywords and types
        
        This uses a sophisticated scoring algorithm to determine which memories
        are most relevant to the current context
        """
        # In a production system, this would query from a database
        # For this implementation, we're returning sample data
        
        # Simulated memories
        memories = [
            {
                'id': f"mem-{session_id}-1-1001",
                'session_id': session_id,
                'created_at': '2025-04-01T10:00:00Z',
                'source_layer': 1,
                'type': 'constraint',
                'priority': 'critical',
                'content': 'User requires a responsive design that works on mobile devices',
                'metadata': {'category': 'ui_requirement'},
                'usage_count': 2,
                'last_accessed': '2025-04-01T11:30:00Z'
            },
            {
                'id': f"mem-{session_id}-1-1002",
                'session_id': session_id,
                'created_at': '2025-04-01T10:05:00Z',
                'source_layer': 1,
                'type': 'decision',
                'priority': 'high',
                'content': 'Will use Flask for backend, Bootstrap for frontend',
                'metadata': {'category': 'architecture'},
                'usage_count': 3,
                'last_accessed': '2025-04-01T14:20:00Z'
            },
            {
                'id': f"mem-{session_id}-2-2001",
                'session_id': session_id,
                'created_at': '2025-04-01T11:15:00Z',
                'source_layer': 2,
                'type': 'artifact',
                'priority': 'medium',
                'content': 'Database schema defines Users, Projects, and Comments tables',
                'metadata': {'category': 'database', 'artifact_type': 'schema'},
                'usage_count': 1,
                'last_accessed': '2025-04-01T12:45:00Z'
            },
            {
                'id': f"mem-{session_id}-3-3001",
                'session_id': session_id,
                'created_at': '2025-04-01T13:30:00Z',
                'source_layer': 3,
                'type': 'error',
                'priority': 'high',
                'content': 'Initial implementation had SQL injection vulnerability in search function',
                'metadata': {'category': 'security', 'fixed': True},
                'usage_count': 2,
                'last_accessed': '2025-04-01T15:10:00Z'
            },
            {
                'id': f"mem-{session_id}-4-4001",
                'session_id': session_id,
                'created_at': '2025-04-01T16:20:00Z',
                'source_layer': 4,
                'type': 'insight',
                'priority': 'medium',
                'content': 'Adding database index on project name improved search performance by 40%',
                'metadata': {'category': 'performance', 'improvement': 'database'},
                'usage_count': 1,
                'last_accessed': '2025-04-01T17:00:00Z'
            }
        ]
        
        # Filter by memory type if specified
        if memory_types:
            memories = [m for m in memories if m['type'] in memory_types]
            
        # Calculate relevance score for each memory
        scored_memories = []
        for memory in memories:
            score = cls._calculate_memory_relevance(memory, current_layer, keywords)
            if score > 0:
                scored_memories.append((memory, score))
                
        # Sort by relevance score and take top 'limit' results
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        relevant_memories = [memory for memory, score in scored_memories[:limit]]
        
        # Update usage statistics (in a real implementation, this would update the database)
        for memory in relevant_memories:
            memory['usage_count'] += 1
            memory['last_accessed'] = datetime.utcnow().isoformat()
            
        return relevant_memories
    
    @classmethod
    def _calculate_memory_relevance(cls, memory: Dict[str, Any], current_layer: int, 
                                  keywords: Optional[List[str]] = None) -> float:
        """
        Calculate a relevance score for a memory to the current context
        
        This uses a combination of:
        1. Layer relevance matrix values
        2. Priority weighting
        3. Keyword matching
        4. Recency and usage factors
        """
        # Base score from layer relevance matrix
        source_layer = memory['source_layer']
        base_score = cls.LAYER_RELEVANCE.get(source_layer, {}).get(current_layer, 0.0)
        
        # Priority weight
        priority = memory['priority']
        priority_weight = cls.PRIORITY_WEIGHTS.get(priority, 0.5)
        
        # Keyword matching
        keyword_score = 0.0
        if keywords:
            content = memory['content'].lower()
            metadata = memory['metadata']
            # Count matching keywords in content
            content_matches = sum(1 for kw in keywords if kw.lower() in content)
            # Count matching keywords in metadata values
            metadata_matches = sum(1 for kw in keywords for val in metadata.values() 
                               if isinstance(val, str) and kw.lower() in val.lower())
            
            # Calculate keyword score (0.0 to 1.0)
            max_possible_matches = len(keywords) * 2  # Can match in both content and metadata
            if max_possible_matches > 0:
                keyword_score = min(1.0, (content_matches + metadata_matches) / max_possible_matches)
        else:
            # If no keywords specified, use a neutral value
            keyword_score = 0.5
            
        # Usage and recency factors
        usage_factor = min(1.0, memory['usage_count'] / 5.0)  # Caps at 5 uses
        
        # Calculate overall score
        score = base_score * 0.4 + priority_weight * 0.3 + keyword_score * 0.2 + usage_factor * 0.1
        
        return score
    
    @classmethod
    def get_memory_summary(cls, session_id: str, layer: int) -> Dict[str, Any]:
        """
        Generate a summary of critical memories for a layer
        """
        # Get memories, prioritizing critical and high priority items
        memories = cls.get_relevant_memories(
            session_id=session_id,
            current_layer=layer,
            memory_types=['constraint', 'decision', 'error'],
            limit=15
        )
        
        # Organize by type
        organized = defaultdict(list)
        for memory in memories:
            organized[memory['type']].append(memory)
            
        # Create summary text
        summary = {
            'constraints': "\n".join([f"• {m['content']}" for m in organized['constraint']]),
            'decisions': "\n".join([f"• {m['content']}" for m in organized['decision']]),
            'errors': "\n".join([f"• {m['content']}" for m in organized['error']]),
            'count': len(memories)
        }
        
        return summary


class ProprietaryEvaluation:
    """
    Implements a unique, proprietary evaluation system for HACF layer outputs.
    
    This provides quantitative and qualitative assessment of each layer's
    performance, guiding the overall process and adaptation.
    """
    
    # Core evaluation dimensions
    EVALUATION_DIMENSIONS = {
        'completeness': {
            'description': 'Measures how fully the output addresses all requirements',
            'weight': 0.25
        },
        'correctness': {
            'description': 'Measures the technical accuracy and compliance with standards',
            'weight': 0.25
        },
        'efficiency': {
            'description': 'Measures resource usage, performance, and optimization',
            'weight': 0.15
        },
        'innovation': {
            'description': 'Measures uniqueness and creative problem-solving',
            'weight': 0.10
        },
        'maintainability': {
            'description': 'Measures code organization, documentation, and future adaptability',
            'weight': 0.15
        },
        'usability': {
            'description': 'Measures end-user experience and interface quality',
            'weight': 0.10
        }
    }
    
    # Layer-specific evaluation criteria
    LAYER_CRITERIA = {
        0: {  # Requirement Validation
            'criteria': [
                'stakeholder_validation',
                'requirement_completeness',
                'feasibility_assessment',
                'acceptance_criteria_clarity',
                'constraint_identification'
            ],
            'dimension_weights': {
                'quality': 0.35,
                'completeness': 0.30,
                'clarity': 0.25,
                'efficiency': 0.10
            }
        },
        1: {  # Task Definition
            'criteria': [
                'requirement_clarity',
                'scope_definition',
                'constraint_identification',
                'user_story_completeness',
                'feasibility_assessment'
            ],
            'dimension_weights': {
                'completeness': 0.35,  # More important for this layer
                'correctness': 0.20,
                'efficiency': 0.05,
                'innovation': 0.20,
                'maintainability': 0.05,
                'usability': 0.15
            }
        },
        2: {  # Analysis & Research
            'criteria': [
                'market_analysis_depth',
                'competitor_evaluation',
                'technology_assessment',
                'feasibility_validation',
                'risk_identification'
            ],
            'dimension_weights': {
                'completeness': 0.25,
                'correctness': 0.30,
                'efficiency': 0.10,
                'innovation': 0.20,  # Higher importance for research
                'maintainability': 0.05,
                'usability': 0.10
            }
        },
        3: {  # Refinement
            'criteria': [
                'architecture_soundness',
                'technical_feasibility',
                'scalability_consideration',
                'dependency_management',
                'interface_definition'
            ],
            'dimension_weights': {
                'completeness': 0.20,
                'correctness': 0.35,
                'efficiency': 0.15,
                'innovation': 0.15,
                'maintainability': 0.10,
                'usability': 0.05
            }
        },
        4: {  # Prototyping
            'criteria': [
                'concept_validation',
                'visual_representation',
                'implementation_fidelity',
                'user_feedback_collection',
                'rapid_iteration'
            ],
            'dimension_weights': {
                'completeness': 0.15,
                'correctness': 0.20,
                'efficiency': 0.10,
                'innovation': 0.30,
                'maintainability': 0.05,
                'usability': 0.20
            }
        },
        5: {  # Development
            'criteria': [
                'code_functionality',
                'api_implementation',
                'error_handling',
                'coding_standards',
                'test_coverage'
            ],
            'dimension_weights': {
                'completeness': 0.25,
                'correctness': 0.30,
                'efficiency': 0.15,
                'innovation': 0.05,
                'maintainability': 0.20,
                'usability': 0.05
            }
        },
        6: {  # Testing & Quality Assurance
            'criteria': [
                'test_coverage',
                'edge_case_handling',
                'integration_validation',
                'security_testing',
                'performance_testing'
            ],
            'dimension_weights': {
                'completeness': 0.25,
                'correctness': 0.40,
                'efficiency': 0.15,
                'innovation': 0.05,
                'maintainability': 0.10,
                'usability': 0.05
            }
        },
        7: {  # Optimization
            'criteria': [
                'performance_improvement',
                'security_hardening',
                'resource_usage',
                'error_reduction',
                'edge_case_handling'
            ],
            'dimension_weights': {
                'completeness': 0.15,
                'correctness': 0.25,
                'efficiency': 0.30,
                'innovation': 0.10,
                'maintainability': 0.15,
                'usability': 0.05
            }
        },
        8: {  # Deployment Preparation
            'criteria': [
                'infrastructure_configuration',
                'ci_cd_pipeline_setup',
                'environment_provisioning',
                'deployment_automation',
                'rollback_procedures'
            ],
            'dimension_weights': {
                'completeness': 0.20,
                'correctness': 0.30,
                'efficiency': 0.25,
                'innovation': 0.05,
                'maintainability': 0.15,
                'usability': 0.05
            }
        },
        9: {  # Final Output
            'criteria': [
                'documentation_quality',
                'code_organization',
                'deployment_readiness',
                'user_guide_clarity',
                'overall_cohesion'
            ],
            'dimension_weights': {
                'completeness': 0.25,
                'correctness': 0.15,
                'efficiency': 0.10,
                'innovation': 0.05,
                'maintainability': 0.25,
                'usability': 0.20
            }
        },
        10: {  # Monitoring & Feedback
            'criteria': [
                'monitoring_coverage',
                'analytics_implementation',
                'feedback_collection_mechanisms',
                'alerting_system_setup',
                'dashboard_usability'
            ],
            'dimension_weights': {
                'completeness': 0.20,
                'correctness': 0.20,
                'efficiency': 0.15,
                'innovation': 0.10,
                'maintainability': 0.15,
                'usability': 0.20
            }
        },
        11: {  # Evolution & Maintenance
            'criteria': [
                'maintenance_planning',
                'roadmap_development',
                'technical_debt_management',
                'scalability_assessment',
                'long_term_sustainability'
            ],
            'dimension_weights': {
                'completeness': 0.15,
                'correctness': 0.15,
                'efficiency': 0.10,
                'innovation': 0.15,
                'maintainability': 0.35,
                'usability': 0.10
            }
        }
    }
    
    # Industry-specific evaluation adjustments
    INDUSTRY_ADJUSTMENTS = {
        'healthcare': {
            'additional_criteria': [
                'hipaa_compliance',
                'patient_data_security',
                'clinical_workflow_integration'
            ],
            'dimension_weights': {
                'correctness': 1.3,  # 30% more important
                'efficiency': 0.9,
                'usability': 1.2
            }
        },
        'finance': {
            'additional_criteria': [
                'transaction_security',
                'audit_trail_completeness',
                'regulatory_compliance'
            ],
            'dimension_weights': {
                'correctness': 1.4,  # 40% more important
                'efficiency': 1.1,
                'innovation': 0.8
            }
        },
        'education': {
            'additional_criteria': [
                'accessibility_compliance',
                'learning_outcome_alignment',
                'student_engagement'
            ],
            'dimension_weights': {
                'usability': 1.4,  # 40% more important
                'completeness': 1.1,
                'efficiency': 0.9
            }
        }
    }
    
    @classmethod
    def evaluate_layer_output(cls, project: Project, layer: int, output: Dict[str, Any],
                             metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Evaluate the output of a specific HACF layer
        
        This uses the proprietary evaluation framework to assess quality and
        guide improvements for future layers
        """
        # Determine industry for potential adjustments
        industry = None
        try:
            if project and project.metadata:
                metadata = json.loads(project.metadata)
                industry = metadata.get('industry')
        except:
            pass
            
        # Get layer-specific criteria
        layer_config = cls.LAYER_CRITERIA.get(layer, cls.LAYER_CRITERIA[1])
        criteria = layer_config['criteria']
        dimension_weights = layer_config['dimension_weights']
        
        # Apply industry adjustments if applicable
        if industry and industry in cls.INDUSTRY_ADJUSTMENTS:
            industry_adj = cls.INDUSTRY_ADJUSTMENTS[industry]
            
            # Add industry-specific criteria
            criteria.extend(industry_adj.get('additional_criteria', []))
            
            # Adjust dimension weights
            adjusted_weights = {}
            for dimension, weight in dimension_weights.items():
                adjustment = industry_adj.get('dimension_weights', {}).get(dimension, 1.0)
                adjusted_weights[dimension] = weight * adjustment
                
            # Normalize weights to sum to 1.0
            weight_sum = sum(adjusted_weights.values())
            dimension_weights = {d: w/weight_sum for d, w in adjusted_weights.items()}
        
        # If metrics are provided, use them
        # Otherwise, generate simulated metrics (in a real system, this would use actual analysis)
        if not metrics:
            metrics = cls._generate_simulated_metrics(criteria)
            
        # Calculate dimension scores
        dimension_scores = cls._calculate_dimension_scores(metrics, criteria)
        
        # Calculate weighted overall score
        overall_score = 0.0
        for dimension, score in dimension_scores.items():
            weight = dimension_weights.get(dimension, cls.EVALUATION_DIMENSIONS[dimension]['weight'])
            overall_score += score * weight
            
        # Generate recommendations
        recommendations = cls._generate_recommendations(metrics, criteria, dimension_scores)
        
        # Create evaluation result
        result = {
            'overall_score': overall_score,
            'dimension_scores': dimension_scores,
            'metric_scores': metrics,
            'recommendations': recommendations,
            'evaluation_timestamp': datetime.utcnow().isoformat()
        }
        
        return result
    
    @classmethod
    def _generate_simulated_metrics(cls, criteria: List[str]) -> Dict[str, float]:
        """Generate simulated metrics for demonstration purposes"""
        metrics = {}
        for criterion in criteria:
            # Generate a random score between 0.6 and 0.95
            # This would be replaced with actual analysis in a production system
            metrics[criterion] = 0.6 + (random.random() * 0.35)
        return metrics
    
    @classmethod
    def _calculate_dimension_scores(cls, metrics: Dict[str, float], 
                                  criteria: List[str]) -> Dict[str, float]:
        """Calculate scores for each evaluation dimension based on metrics"""
        # This is a simplified mapping of criteria to dimensions
        # In a production system, this would be more sophisticated
        dimension_criteria_map = {
            'completeness': [c for c in criteria if any(x in c for x in 
                                                   ['completeness', 'coverage', 'scope', 'requirement'])],
            'correctness': [c for c in criteria if any(x in c for x in 
                                                    ['correctness', 'accuracy', 'compliance', 'soundness'])],
            'efficiency': [c for c in criteria if any(x in c for x in 
                                                   ['efficiency', 'performance', 'resource', 'optimization'])],
            'innovation': [c for c in criteria if any(x in c for x in 
                                                   ['innovation', 'creative', 'unique'])],
            'maintainability': [c for c in criteria if any(x in c for x in 
                                                        ['maintainability', 'documentation', 'organization'])],
            'usability': [c for c in criteria if any(x in c for x in 
                                                  ['usability', 'user', 'interface', 'experience'])]
        }
        
        # For criteria that don't match the simple mapping, assign to dimensions
        for criterion in criteria:
            assigned = False
            for dimension in dimension_criteria_map:
                if criterion in dimension_criteria_map[dimension]:
                    assigned = True
                    break
                    
            if not assigned:
                # Assign based on criterion name
                if 'security' in criterion or 'error' in criterion:
                    dimension_criteria_map['correctness'].append(criterion)
                elif 'test' in criterion:
                    dimension_criteria_map['maintainability'].append(criterion)
                else:
                    # Default to completeness
                    dimension_criteria_map['completeness'].append(criterion)
        
        # Calculate average score for each dimension
        dimension_scores = {}
        for dimension, dim_criteria in dimension_criteria_map.items():
            if dim_criteria:
                dimension_scores[dimension] = sum(metrics.get(c, 0.0) for c in dim_criteria) / len(dim_criteria)
            else:
                # If no criteria mapped to this dimension, use a default value
                dimension_scores[dimension] = 0.75
                
        return dimension_scores
    
    @classmethod
    def _generate_recommendations(cls, metrics: Dict[str, float], criteria: List[str],
                               dimension_scores: Dict[str, float]) -> List[str]:
        """Generate improvement recommendations based on evaluation"""
        recommendations = []
        
        # Find lowest scoring metrics
        sorted_metrics = sorted(metrics.items(), key=lambda x: x[1])
        lowest_metrics = sorted_metrics[:3]  # Top 3 lowest scores
        
        for criterion, score in lowest_metrics:
            if score < 0.7:
                # Generate recommendation based on criterion
                if 'requirement' in criterion or 'scope' in criterion:
                    recommendations.append(f"Improve clarity and completeness of requirements definition")
                elif 'architecture' in criterion:
                    recommendations.append(f"Refine system architecture to ensure technical feasibility and scalability")
                elif 'code' in criterion or 'implementation' in criterion:
                    recommendations.append(f"Enhance code quality and implementation completeness")
                elif 'performance' in criterion or 'efficiency' in criterion:
                    recommendations.append(f"Optimize for better performance and resource efficiency")
                elif 'security' in criterion:
                    recommendations.append(f"Strengthen security measures and vulnerability protections")
                elif 'documentation' in criterion:
                    recommendations.append(f"Improve documentation quality and completeness")
                elif 'test' in criterion:
                    recommendations.append(f"Expand test coverage and test case variety")
                else:
                    recommendations.append(f"Improve {criterion.replace('_', ' ')} in next iteration")
        
        # Add dimension-based recommendations
        lowest_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1])[:2]
        for dimension, score in lowest_dimensions:
            if score < 0.75:
                if dimension == 'completeness':
                    recommendations.append("Work on more comprehensive coverage of all requirements")
                elif dimension == 'correctness':
                    recommendations.append("Focus on technical accuracy and standards compliance")
                elif dimension == 'efficiency':
                    recommendations.append("Improve resource usage and performance optimization")
                elif dimension == 'innovation':
                    recommendations.append("Consider more creative or unique approaches")
                elif dimension == 'maintainability':
                    recommendations.append("Enhance code organization and documentation")
                elif dimension == 'usability':
                    recommendations.append("Improve user experience and interface design")
        
        # Ensure no duplicate recommendations
        recommendations = list(set(recommendations))
        
        return recommendations


class DomainSpecializationEngine:
    """
    Provides domain-specific layer customizations for different industries.
    
    This allows the HACF framework to adapt its behavior, evaluations,
    and outputs based on specialized knowledge of different vertical markets.
    """
    
    # Domain specializations available
    DOMAIN_SPECIALIZATIONS = {
        'healthcare': {
            'name': 'Healthcare & Life Sciences',
            'description': 'Specialized behaviors for healthcare applications, including HIPAA compliance, clinical workflows, and patient data management',
            'key_concerns': [
                'Protected Health Information (PHI) security',
                'HIPAA and regulatory compliance',
                'Clinical workflow integration',
                'Patient experience optimization',
                'Medical terminology accuracy'
            ],
            'prompt_modifiers': {
                1: "Ensure all requirements consider HIPAA compliance and patient data security. Define clear boundaries for PHI handling.",
                2: "Architecture must incorporate secure PHI storage and transmission. Consider audit logging requirements for all data access.",
                3: "Implement all code with strict input validation and output sanitization. Include comprehensive PHI access controls.",
                4: "Thoroughly audit for security vulnerabilities. Ensure all PHI is encrypted at rest and in transit.",
                5: "Document all security measures and compliance features. Include security best practices for operators."
            }
        },
        'finance': {
            'name': 'Financial Services',
            'description': 'Specialized behaviors for financial applications, focusing on security, regulatory compliance, and transaction integrity',
            'key_concerns': [
                'Transaction security and integrity',
                'Financial regulatory compliance (SOX, PCI-DSS, etc.)',
                'Audit trail and transaction logging',
                'Fraud detection and prevention',
                'Financial calculation accuracy'
            ],
            'prompt_modifiers': {
                1: "Requirements must include comprehensive audit logging and financial regulatory compliance. Define clear transaction boundaries.",
                2: "Design architecture with transaction integrity as a core principle. Include reconciliation and verification mechanisms.",
                3: "Implement with strict transaction atomicity. Include comprehensive input validation for all financial data.",
                4: "Audit for security vulnerabilities with focus on financial fraud vectors. Implement advanced error handling for all calculations.",
                5: "Document all compliance measures and financial security features. Include disaster recovery procedures."
            }
        },
        'education': {
            'name': 'Education Technology',
            'description': 'Specialized behaviors for educational applications, with focus on accessibility, learning outcomes, and student engagement',
            'key_concerns': [
                'Accessibility compliance (WCAG, Section 508)',
                'Learning outcome measurement',
                'Student privacy (FERPA compliance)',
                'Engagement optimization',
                'Multi-platform support for diverse learning environments'
            ],
            'prompt_modifiers': {
                1: "Requirements must consider accessibility standards and student privacy regulations. Define clear learning objectives.",
                2: "Architecture should support diverse learning modalities and content types. Consider both synchronous and asynchronous education models.",
                3: "Implement with strong accessibility support. Include comprehensive student data privacy protections.",
                4: "Optimize for engagement and usability across different skill levels. Ensure all content is accessible.",
                5: "Document all accessibility features and learning outcome measurements. Include teacher/administrator instructions."
            }
        },
        'government': {
            'name': 'Government & Public Sector',
            'description': 'Specialized behaviors for government applications, with focus on compliance, accessibility, and public service delivery',
            'key_concerns': [
                'Regulatory compliance and policy adherence',
                'Accessibility requirements (ADA, Section 508)',
                'Transparent audit trails',
                'Public record management',
                'Cross-department data exchange'
            ],
            'prompt_modifiers': {
                1: "Requirements must address all applicable governmental regulations and policies. Define clear boundaries for public data access.",
                2: "Architecture should incorporate high-availability and disaster recovery. Consider long-term data retention requirements.",
                3: "Implement with comprehensive access controls and audit logging. Support diverse public service workflows.",
                4: "Ensure full accessibility compliance. Implement comprehensive error handling for public-facing interfaces.",
                5: "Document all compliance measures and provide detailed operational procedures. Include public data handling guidelines."
            }
        },
        'retail': {
            'name': 'Retail & E-commerce',
            'description': 'Specialized behaviors for retail applications, focusing on customer experience, inventory management, and sales optimization',
            'key_concerns': [
                'Customer journey optimization',
                'Payment processing security',
                'Inventory management',
                'Promotional campaign support',
                'Multi-channel commerce integration'
            ],
            'prompt_modifiers': {
                1: "Requirements should focus on customer experience and conversion optimization. Define clear inventory and order management processes.",
                2: "Architecture should support high-volume transaction processing and seasonal scaling. Consider integrations with payment processors.",
                3: "Implement with focus on shopping cart functionality and checkout optimization. Include comprehensive inventory controls.",
                4: "Optimize for performance under high load. Ensure robust payment processing error handling.",
                5: "Document customer journey touchpoints and provide operational procedures for order management."
            }
        },
        'manufacturing': {
            'name': 'Manufacturing & Supply Chain',
            'description': 'Specialized behaviors for manufacturing applications, with focus on process optimization, quality control, and supply chain management',
            'key_concerns': [
                'Production process integration',
                'Quality control and compliance',
                'Supply chain visibility',
                'Equipment maintenance scheduling',
                'Regulatory compliance for manufacturing'
            ],
            'prompt_modifiers': {
                1: "Requirements should address production workflow integration and material tracking. Define clear quality control checkpoints.",
                2: "Architecture should support real-time data collection from production equipment. Consider integration with ERP systems.",
                3: "Implement robust error handling for production-critical functions. Include comprehensive logging of all production steps.",
                4: "Optimize for reliability in manufacturing environments. Ensure data integrity for quality control measurements.",
                5: "Document all production-related features and provide detailed integration instructions for manufacturing systems."
            }
        }
    }
    
    # Specialized evaluation criteria by domain
    DOMAIN_EVALUATION_CRITERIA = {
        'healthcare': [
            'phi_security',
            'hipaa_compliance',
            'clinical_workflow_compatibility',
            'medical_terminology_accuracy',
            'patient_experience_quality'
        ],
        'finance': [
            'transaction_integrity',
            'financial_compliance',
            'audit_trail_completeness',
            'fraud_prevention_measures',
            'calculation_accuracy'
        ],
        'education': [
            'accessibility_compliance',
            'learning_outcome_measurement',
            'student_engagement',
            'ferpa_compliance',
            'multi_platform_support'
        ],
        'government': [
            'regulatory_adherence',
            'public_accessibility',
            'audit_transparency',
            'records_management',
            'inter_department_compatibility'
        ],
        'retail': [
            'customer_journey_optimization',
            'payment_processing_security',
            'inventory_management',
            'promotional_flexibility',
            'multi_channel_integration'
        ],
        'manufacturing': [
            'production_process_integration',
            'quality_control_support',
            'supply_chain_visibility',
            'equipment_integration',
            'manufacturing_compliance'
        ]
    }
    
    @classmethod
    def get_domain_specialization(cls, domain: str) -> Dict[str, Any]:
        """Get the domain specialization for a specific industry vertical"""
        return cls.DOMAIN_SPECIALIZATIONS.get(domain, {})
    
    @classmethod
    def get_available_domains(cls) -> List[Dict[str, Any]]:
        """Get a list of all available domain specializations"""
        domains = []
        for domain_id, domain_data in cls.DOMAIN_SPECIALIZATIONS.items():
            domains.append({
                'id': domain_id,
                'name': domain_data['name'],
                'description': domain_data['description']
            })
        return domains
    
    @classmethod
    def get_layer_prompt_modifier(cls, domain: str, layer: int) -> str:
        """Get the prompt modifier for a specific domain and layer"""
        domain_data = cls.DOMAIN_SPECIALIZATIONS.get(domain, {})
        modifiers = domain_data.get('prompt_modifiers', {})
        return modifiers.get(layer, "")
    
    @classmethod
    def get_domain_evaluation_criteria(cls, domain: str) -> List[str]:
        """Get specialized evaluation criteria for a domain"""
        return cls.DOMAIN_EVALUATION_CRITERIA.get(domain, [])
        
    @classmethod
    def get_available_domains(cls) -> List[Dict[str, Any]]:
        """Get a list of all available domain specializations"""
        domains = []
        for domain_id, domain_data in cls.DOMAIN_SPECIALIZATIONS.items():
            domains.append({
                'id': domain_id,
                'name': domain_data['name'],
                'description': domain_data['description']
            })
        return domains
    
    @classmethod
    def apply_domain_specialization(cls, prompt: str, domain: str, layer: int) -> str:
        """Apply domain-specific modifications to a prompt"""
        modifier = cls.get_layer_prompt_modifier(domain, layer)
        
        if not modifier:
            return prompt
            
        # Add the modifier to the prompt
        specialized_prompt = f"{prompt}\n\n[DOMAIN SPECIALIZATION: {modifier}]"
        
        return specialized_prompt
    
    @classmethod
    def get_domain_specific_templates(cls, domain: str) -> Dict[str, Any]:
        """Get domain-specific templates and artifacts"""
        # This would return code snippets, document templates, etc.
        # specific to a domain
        
        # Sample templates
        templates = {
            'healthcare': {
                'code_snippets': [
                    {
                        'name': 'PHI Data Validation',
                        'language': 'python',
                        'code': '# PHI Data Validation Function\ndef validate_phi_data(phi_data):\n    """Validate Protected Health Information\"\"\"\n    # Validation logic here\n    return validated_data'
                    },
                    {
                        'name': 'HIPAA Audit Log',
                        'language': 'python',
                        'code': '# HIPAA Compliant Audit Logging\ndef log_phi_access(user_id, record_id, action):\n    """Log PHI access in HIPAA-compliant format\"\"\"\n    # Logging logic here\n    return log_entry'
                    }
                ],
                'document_templates': [
                    {
                        'name': 'HIPAA Compliance Checklist',
                        'format': 'markdown',
                        'content': '# HIPAA Compliance Checklist\n\n## Technical Safeguards\n- [ ] Access Controls\n- [ ] Audit Controls\n- [ ] Integrity Controls\n- [ ] Transmission Security\n\n## Administrative Safeguards\n- [ ] Security Management Process\n- [ ] Assigned Security Responsibility\n- [ ] Workforce Training\n- [ ] Evaluation\n\n## Physical Safeguards\n- [ ] Facility Access Controls\n- [ ] Workstation Security\n- [ ] Device and Media Controls'
                    }
                ]
            },
            'finance': {
                'code_snippets': [
                    {
                        'name': 'Transaction Integrity Check',
                        'language': 'python',
                        'code': '# Financial Transaction Integrity Verification\ndef verify_transaction_integrity(transaction_data):\n    """Verify the integrity of a financial transaction\"\"\"\n    # Verification logic here\n    return verification_result'
                    }
                ],
                'document_templates': [
                    {
                        'name': 'Financial Compliance Report',
                        'format': 'markdown',
                        'content': '# Financial Compliance Report\n\n## Regulatory Compliance\n- [ ] SOX Section 404 Controls\n- [ ] PCI-DSS Requirements\n- [ ] AML Procedures\n\n## Transaction Security\n- [ ] Encryption Standards\n- [ ] Fraud Detection\n- [ ] Audit Logging\n\n## Data Retention\n- [ ] Record Keeping Policies\n- [ ] Data Purging Procedures\n- [ ] Backup Verification'
                    }
                ]
            }
        }
        
        return templates.get(domain, {})


class HumanAICollaborationManager:
    """
    Manages the integration of human expertise at strategic checkpoints in the HACF process.
    
    This creates intentional intervention points where human knowledge
    enhances the AI system, making the framework more resistant to simple replication.
    """
    
    # Collaboration checkpoint types
    CHECKPOINT_TYPES = {
        'review': {
            'description': 'Human reviews AI output and provides feedback',
            'required_skills': [],
            'average_time': 15  # minutes
        },
        'guidance': {
            'description': 'Human provides specific direction before AI processing',
            'required_skills': [],
            'average_time': 10  # minutes
        },
        'correction': {
            'description': 'Human corrects specific aspects of AI output',
            'required_skills': [],
            'average_time': 20  # minutes
        },
        'extension': {
            'description': 'Human extends AI output with additional insights',
            'required_skills': [],
            'average_time': 25  # minutes
        },
        'decision': {
            'description': 'Human makes a key decision among AI-generated alternatives',
            'required_skills': [],
            'average_time': 15  # minutes
        }
    }
    
    # Layer-specific checkpoint configurations
    LAYER_CHECKPOINTS = {
        0: {  # Requirement Validation
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Stakeholder Requirement Guidance',
                    'description': 'Human stakeholders provide initial guidance on requirements and constraints',
                    'required_skills': ['domain_knowledge', 'stakeholder_management'],
                    'position': 'before',  # Execute before layer processing
                    'optional': False  # Required checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Initial Validation Review',
                    'description': 'Human reviews AI-validated requirements for completeness and accuracy',
                    'required_skills': ['business_analysis', 'requirements_engineering'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        1: {  # Task Definition
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Initial Project Scope Guidance',
                    'description': 'Human provides initial guidance on project scope and key requirements',
                    'required_skills': ['business_analysis', 'requirements_gathering'],
                    'position': 'before',  # Execute before layer processing
                    'optional': False  # Required checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Requirements Review',
                    'description': 'Human reviews AI-generated requirements and provides feedback',
                    'required_skills': ['business_analysis', 'domain_knowledge'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        2: {  # Analysis & Research
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Research Focus Guidance',
                    'description': 'Human provides guidance on research focus areas and priorities',
                    'required_skills': ['market_research', 'competitive_analysis'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Research Findings Review',
                    'description': 'Human reviews research findings and provides additional context',
                    'required_skills': ['domain_expertise', 'technology_assessment'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        3: {  # Refinement
            'default_checkpoints': [
                {
                    'type': 'decision',
                    'name': 'Architecture Approach Selection',
                    'description': 'Human selects preferred architecture approach from AI-generated alternatives',
                    'required_skills': ['system_architecture', 'technical_planning'],
                    'position': 'during',  # Execute during layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'correction',
                    'name': 'Technical Feasibility Assessment',
                    'description': 'Human reviews and corrects technical approach for feasibility',
                    'required_skills': ['system_architecture', 'development_experience'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        4: {  # Prototyping
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Prototype Focus Guidance',
                    'description': 'Human provides guidance on prototype focus areas and key features',
                    'required_skills': ['product_design', 'user_experience'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Prototype Evaluation',
                    'description': 'Human evaluates prototype functionality and provides feedback',
                    'required_skills': ['usability_testing', 'product_design'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        5: {  # Development
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Development Approach Guidance',
                    'description': 'Human provides guidance on development approach and key implementation details',
                    'required_skills': ['software_development', 'coding_standards'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'correction',
                    'name': 'Code Review',
                    'description': 'Human reviews AI-generated code and provides corrections',
                    'required_skills': ['software_development', 'code_review'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        6: {  # Testing & Quality Assurance
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Test Strategy Guidance',
                    'description': 'Human provides guidance on testing strategy and focus areas',
                    'required_skills': ['quality_assurance', 'test_planning'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Test Results Review',
                    'description': 'Human reviews test results and identifies gaps in coverage',
                    'required_skills': ['quality_assurance', 'test_analysis'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        7: {  # Optimization
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Optimization Priority Guidance',
                    'description': 'Human sets priorities for optimization efforts',
                    'required_skills': ['performance_optimization', 'security_expertise'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Security Review',
                    'description': 'Human reviews security measures and provides feedback',
                    'required_skills': ['security_expertise', 'risk_assessment'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        8: {  # Deployment Preparation
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Infrastructure Strategy',
                    'description': 'Human provides guidance on infrastructure and deployment approach',
                    'required_skills': ['devops', 'cloud_architecture'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Deployment Readiness Review',
                    'description': 'Human reviews deployment configuration and provides feedback',
                    'required_skills': ['devops', 'infrastructure_management'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        9: {  # Final Output
            'default_checkpoints': [
                {
                    'type': 'extension',
                    'name': 'Documentation Enhancement',
                    'description': 'Human extends AI-generated documentation with additional insights',
                    'required_skills': ['technical_writing', 'user_experience'],
                    'position': 'during',  # Execute during layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Final Deliverable Review',
                    'description': 'Human conducts final review of complete project deliverables',
                    'required_skills': ['project_management', 'quality_assurance'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        10: {  # Monitoring & Feedback
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Monitoring Requirements',
                    'description': 'Human provides guidance on monitoring requirements and metrics',
                    'required_skills': ['system_monitoring', 'analytics'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Monitoring Setup Review',
                    'description': 'Human reviews monitoring configuration and provides feedback',
                    'required_skills': ['devops', 'system_monitoring'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        },
        11: {  # Evolution & Maintenance
            'default_checkpoints': [
                {
                    'type': 'guidance',
                    'name': 'Maintenance Strategy',
                    'description': 'Human provides guidance on maintenance approach and roadmap',
                    'required_skills': ['product_management', 'technical_planning'],
                    'position': 'before',  # Execute before layer processing
                    'optional': True  # Optional checkpoint
                },
                {
                    'type': 'review',
                    'name': 'Maintenance Plan Review',
                    'description': 'Human reviews maintenance plan and provides feedback',
                    'required_skills': ['support_management', 'technical_debt_management'],
                    'position': 'after',  # Execute after layer processing
                    'optional': False  # Required checkpoint
                }
            ]
        }
    }
    
    # Domain-specific checkpoint adjustments
    DOMAIN_CHECKPOINT_ADJUSTMENTS = {
        'healthcare': {
            'additional_checkpoints': [
                {
                    'layer': 2,
                    'type': 'review',
                    'name': 'HIPAA Compliance Review',
                    'description': 'Healthcare compliance expert reviews architecture for HIPAA compliance',
                    'required_skills': ['hipaa_expertise', 'healthcare_compliance'],
                    'position': 'after',
                    'optional': False
                },
                {
                    'layer': 4,
                    'type': 'review',
                    'name': 'PHI Security Audit',
                    'description': 'Security expert audits PHI protection measures',
                    'required_skills': ['healthcare_security', 'data_protection'],
                    'position': 'after',
                    'optional': False
                }
            ]
        },
        'finance': {
            'additional_checkpoints': [
                {
                    'layer': 2,
                    'type': 'review',
                    'name': 'Financial Compliance Review',
                    'description': 'Financial compliance expert reviews architecture',
                    'required_skills': ['financial_regulations', 'compliance_expertise'],
                    'position': 'after',
                    'optional': False
                },
                {
                    'layer': 3,
                    'type': 'correction',
                    'name': 'Financial Calculation Verification',
                    'description': 'Financial expert verifies calculation implementation',
                    'required_skills': ['financial_analysis', 'accounting_principles'],
                    'position': 'after',
                    'optional': False
                }
            ]
        }
    }
    
    @classmethod
    def get_layer_checkpoints(cls, layer: int, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get checkpoints for a specific layer, optionally with domain-specific additions"""
        # Get default checkpoints for the layer
        checkpoints = cls.LAYER_CHECKPOINTS.get(layer, {}).get('default_checkpoints', [])
        
        # Add domain-specific checkpoints if applicable
        if domain and domain in cls.DOMAIN_CHECKPOINT_ADJUSTMENTS:
            domain_adj = cls.DOMAIN_CHECKPOINT_ADJUSTMENTS[domain]
            additional_checkpoints = [cp for cp in domain_adj.get('additional_checkpoints', []) 
                                    if cp['layer'] == layer]
            
            # Combine with default checkpoints
            checkpoints = checkpoints + additional_checkpoints
            
        return checkpoints
    
    @classmethod
    def create_checkpoint(cls, session_id: str, layer: int, checkpoint_type: str,
                        name: str, description: str, position: str = 'after',
                        required_skills: Optional[List[str]] = None,
                        optional: bool = True) -> Dict[str, Any]:
        """Create a custom checkpoint for a HACF session"""
        if checkpoint_type not in cls.CHECKPOINT_TYPES:
            checkpoint_type = 'review'  # Default to review
            
        checkpoint_id = f"cp-{session_id}-{layer}-{checkpoint_type}-{random.randint(1000, 9999)}"
        
        checkpoint = {
            'id': checkpoint_id,
            'session_id': session_id,
            'layer': layer,
            'type': checkpoint_type,
            'name': name,
            'description': description,
            'position': position,
            'required_skills': required_skills or [],
            'optional': optional,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'feedback': None
        }
        
        # In a production system, this would be stored in the database
        return checkpoint
    
    @classmethod
    def update_checkpoint_status(cls, checkpoint_id: str, status: str, 
                               feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update the status of a checkpoint (e.g., completed, skipped)
        Returns the updated checkpoint
        """
        # In a production system, this would update the database record
        # Here we're returning a simulated response
        
        checkpoint = {
            'id': checkpoint_id,
            'status': status,
            'completed_at': datetime.utcnow().isoformat() if status == 'completed' else None,
            'feedback': feedback
        }
        
        return checkpoint
    
    @classmethod
    def get_checkpoint_status(cls, checkpoint_id: str) -> Dict[str, Any]:
        """Get the current status of a checkpoint"""
        # In a production system, this would query the database
        # Here we're returning a simulated response
        
        return {
            'id': checkpoint_id,
            'status': 'pending',
            'created_at': '2025-04-01T10:00:00Z',
            'completed_at': None,
            'feedback': None
        }
    
    @classmethod
    def process_human_feedback(cls, checkpoint_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process feedback from a human interaction at a checkpoint
        Returns processed feedback with impact analysis
        """
        # Example feedback structure:
        # {
        #     'rating': 4,  # 1-5 scale
        #     'comments': 'Good overall approach but need more emphasis on data validation',
        #     'suggestions': ['Add input validation', 'Consider edge cases'],
        #     'specific_corrections': {
        #         'data_model': 'Add timestamp field to user table'
        #     }
        # }
        
        # In a production system, this would analyze feedback and determine how
        # it should impact subsequent layer processing
        
        # Calculate satisfaction score (0.0 to 1.0)
        rating = feedback.get('rating', 3)
        satisfaction = rating / 5.0
        
        # Determine impact level
        impact_level = 'low'
        if satisfaction < 0.4:
            impact_level = 'high'
        elif satisfaction < 0.7:
            impact_level = 'medium'
            
        # Identify areas for adjustment
        adjustment_areas = []
        if 'suggestions' in feedback:
            adjustment_areas.extend(feedback['suggestions'])
            
        if 'specific_corrections' in feedback:
            for area, correction in feedback['specific_corrections'].items():
                adjustment_areas.append(f"{area}: {correction}")
                
        # Process comments for additional insights
        comments = feedback.get('comments', '')
        if 'improve' in comments.lower() or 'enhance' in comments.lower() or 'add' in comments.lower():
            adjustment_areas.append('General improvements based on comments')
            
        # Create processed feedback
        processed = {
            'checkpoint_id': checkpoint_id,
            'satisfaction': satisfaction,
            'impact_level': impact_level,
            'adjustment_areas': adjustment_areas,
            'processed_at': datetime.utcnow().isoformat()
        }
        
        return processed