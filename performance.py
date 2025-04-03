import os
import time
import json
import logging
import datetime
import threading
from functools import wraps
from typing import List, Dict, Any, Callable, Optional

from flask import request, current_app, g

# Configure logging
logger = logging.getLogger(__name__)

# Cache storage
_memory_cache = {}
_cache_expiry = {}
_cache_lock = threading.RLock()

class PerformanceMonitor:
    """Tracks and analyzes application performance metrics"""
    
    # Storage for performance metrics
    _request_times = []
    _endpoint_times = {}
    _database_queries = []
    _background_tasks = []
    
    # Maximum number of entries to keep
    MAX_ENTRIES = 1000
    
    @classmethod
    def track_request(cls, start_time, end_time, endpoint, status_code):
        """Record timing information for a request"""
        duration = end_time - start_time
        
        with _cache_lock:
            cls._request_times.append({
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code
            })
            
            # Keep list from growing too large
            if len(cls._request_times) > cls.MAX_ENTRIES:
                cls._request_times = cls._request_times[-cls.MAX_ENTRIES:]
            
            # Update endpoint average times
            if endpoint not in cls._endpoint_times:
                cls._endpoint_times[endpoint] = {
                    'count': 1,
                    'total_time': duration,
                    'min_time': duration,
                    'max_time': duration,
                    'avg_time': duration
                }
            else:
                stats = cls._endpoint_times[endpoint]
                stats['count'] += 1
                stats['total_time'] += duration
                stats['min_time'] = min(stats['min_time'], duration)
                stats['max_time'] = max(stats['max_time'], duration)
                stats['avg_time'] = stats['total_time'] / stats['count']
    
    @classmethod
    def track_database_query(cls, query, duration, row_count=None):
        """Record timing information for a database query"""
        with _cache_lock:
            cls._database_queries.append({
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'query': query,
                'duration': duration,
                'row_count': row_count
            })
            
            # Keep list from growing too large
            if len(cls._database_queries) > cls.MAX_ENTRIES:
                cls._database_queries = cls._database_queries[-cls.MAX_ENTRIES:]
    
    @classmethod
    def track_background_task(cls, task_name, start_time, end_time, status):
        """Record timing information for a background task"""
        duration = end_time - start_time
        
        with _cache_lock:
            cls._background_tasks.append({
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'task_name': task_name,
                'duration': duration,
                'status': status
            })
            
            # Keep list from growing too large
            if len(cls._background_tasks) > cls.MAX_ENTRIES:
                cls._background_tasks = cls._background_tasks[-cls.MAX_ENTRIES:]
    
    @classmethod
    def get_performance_metrics(cls):
        """Get collected performance metrics"""
        with _cache_lock:
            # Calculate overall request stats
            if cls._request_times:
                times = [entry['duration'] for entry in cls._request_times]
                avg_request_time = sum(times) / len(times)
                max_request_time = max(times)
                p95_request_time = sorted(times)[int(len(times) * 0.95)]
            else:
                avg_request_time = 0
                max_request_time = 0
                p95_request_time = 0
            
            # Get top 5 slowest endpoints
            endpoints = sorted(
                cls._endpoint_times.items(),
                key=lambda x: x[1]['avg_time'],
                reverse=True
            )[:5]
            
            # Get top 5 slowest database queries
            queries = sorted(
                cls._database_queries,
                key=lambda x: x['duration'],
                reverse=True
            )[:5]
            
            # Format results
            return {
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'request_stats': {
                    'count': len(cls._request_times),
                    'avg_time': avg_request_time,
                    'max_time': max_request_time,
                    'p95_time': p95_request_time
                },
                'slowest_endpoints': [
                    {
                        'endpoint': endpoint,
                        'avg_time': stats['avg_time'],
                        'count': stats['count']
                    }
                    for endpoint, stats in endpoints
                ],
                'slowest_queries': [
                    {
                        'query': query['query'],
                        'duration': query['duration'],
                        'row_count': query['row_count']
                    }
                    for query in queries
                ],
                'recent_background_tasks': cls._background_tasks[-5:]
            }

def cache_result(expiry=300):
    """
    Decorator to cache function results in memory
    expiry: Cache expiry time in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Check if result is cached and not expired
            with _cache_lock:
                if cache_key in _memory_cache:
                    if cache_key not in _cache_expiry or _cache_expiry[cache_key] > time.time():
                        return _memory_cache[cache_key]
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            
            with _cache_lock:
                _memory_cache[cache_key] = result
                _cache_expiry[cache_key] = time.time() + expiry
            
            return result
        return wrapper
    return decorator

def clear_cache(prefix=None):
    """
    Clear the memory cache
    prefix: Optional prefix to clear only matching entries
    """
    with _cache_lock:
        if prefix:
            keys_to_remove = [k for k in _memory_cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del _memory_cache[key]
                if key in _cache_expiry:
                    del _cache_expiry[key]
        else:
            _memory_cache.clear()
            _cache_expiry.clear()

def time_function(func):
    """Decorator to time function execution and log results"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        logger.debug(f"Function {func.__name__} took {duration:.4f} seconds")
        
        return result
    return wrapper

class BackgroundTaskManager:
    """Manages asynchronous background tasks"""
    
    # List of active background tasks
    _active_tasks = {}
    _task_results = {}
    _task_lock = threading.RLock()
    
    @classmethod
    def run_task(cls, func, *args, **kwargs):
        """Run a function as a background task"""
        task_id = f"task-{time.time()}-{threading.get_ident()}"
        
        def task_wrapper():
            start_time = time.time()
            status = 'success'
            result = None
            
            try:
                # Run the actual function
                result = func(*args, **kwargs)
            except Exception as e:
                status = 'error'
                logger.error(f"Background task {task_id} failed: {str(e)}")
                result = {'error': str(e)}
            finally:
                end_time = time.time()
                
                # Track task completion
                PerformanceMonitor.track_background_task(
                    func.__name__,
                    start_time,
                    end_time,
                    status
                )
                
                # Store result and update task status
                with cls._task_lock:
                    cls._task_results[task_id] = {
                        'status': status,
                        'result': result,
                        'execution_time': end_time - start_time,
                        'completed_at': datetime.datetime.utcnow().isoformat()
                    }
                    
                    # Remove task from active tasks
                    if task_id in cls._active_tasks:
                        del cls._active_tasks[task_id]
        
        # Create and start thread
        thread = threading.Thread(target=task_wrapper)
        thread.daemon = True
        
        with cls._task_lock:
            cls._active_tasks[task_id] = {
                'function': func.__name__,
                'started_at': datetime.datetime.utcnow().isoformat(),
                'thread': thread
            }
        
        thread.start()
        return task_id
    
    @classmethod
    def get_task_status(cls, task_id):
        """Get status of a background task"""
        with cls._task_lock:
            # If task is still active
            if task_id in cls._active_tasks:
                return {
                    'status': 'running',
                    'function': cls._active_tasks[task_id]['function'],
                    'started_at': cls._active_tasks[task_id]['started_at']
                }
            
            # If task is completed
            if task_id in cls._task_results:
                return cls._task_results[task_id]
            
            # Task not found
            return {'status': 'not_found'}
    
    @classmethod
    def get_active_tasks(cls):
        """Get a list of active tasks"""
        with cls._task_lock:
            return {
                task_id: {
                    'function': info['function'],
                    'started_at': info['started_at']
                }
                for task_id, info in cls._active_tasks.items()
            }
    
    @classmethod
    def cleanup_old_results(cls, max_age=86400):
        """Clean up old task results (older than max_age seconds)"""
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=max_age)
        cutoff_str = cutoff_time.isoformat()
        
        with cls._task_lock:
            # Find tasks to remove
            tasks_to_remove = [
                task_id for task_id, result in cls._task_results.items()
                if result.get('completed_at', '') < cutoff_str
            ]
            
            # Remove them
            for task_id in tasks_to_remove:
                del cls._task_results[task_id]
            
            return len(tasks_to_remove)

# Flask request performance middleware
def request_performance_middleware(response):
    """Middleware to track request performance"""
    if hasattr(g, 'request_start_time'):
        end_time = time.time()
        PerformanceMonitor.track_request(
            g.request_start_time,
            end_time,
            request.endpoint,
            response.status_code
        )
    return response

def before_request_handler():
    """Handler to record request start time"""
    g.request_start_time = time.time()

# Flask SQLAlchemy query performance middleware
def track_database_query(query, executed_query=None, row_count=None):
    """Track a database query execution"""
    if hasattr(query, 'statement') and hasattr(query, 'duration'):
        # Simplify query for logging
        query_str = str(query.statement)
        if len(query_str) > 1000:
            query_str = query_str[:1000] + '...'
        
        PerformanceMonitor.track_database_query(
            query_str,
            query.duration,
            row_count
        )

# Initialize performance tracking for a Flask app
def init_performance_tracking(app):
    """Set up performance tracking for a Flask application"""
    # Register before request handler
    app.before_request(before_request_handler)
    
    # Register after request handler
    app.after_request(request_performance_middleware)
    
    # Set up regular cache cleanup
    @app.before_first_request
    def setup_cache_cleanup():
        def cleanup_job():
            while True:
                # Clean up expired cache entries
                with _cache_lock:
                    now = time.time()
                    expired_keys = [k for k, v in _cache_expiry.items() if v < now]
                    for key in expired_keys:
                        if key in _memory_cache:
                            del _memory_cache[key]
                        del _cache_expiry[key]
                
                # Clean up old task results
                BackgroundTaskManager.cleanup_old_results()
                
                # Wait before next cleanup
                time.sleep(3600)  # Run hourly
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_job)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    logger.info("Performance tracking initialized")