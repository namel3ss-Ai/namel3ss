"""
Web Development Capability Pack

Provides HTTP client, server, and JSON utilities for namel3ss applications.
"""

from .http_client import get, post, HTTPResponse

# Pack metadata
__version__ = '0.1.0'
__author__ = 'namel3ss contributors'
__description__ = 'Web development capabilities for namel3ss'


def register_capabilities(runtime):
    """
    Register web capabilities with the namel3ss runtime.
    
    This function is called by the runtime to add web-related
    functions to the namel3ss language.
    
    Args:
        runtime: The namel3ss runtime instance
    """
    
    # Register HTTP Client functions
    # Note: Adjust the registration method based on actual namel3ss runtime
    
    try:
        runtime.register_function('http.get', get)
        runtime.register_function('http.post', post)
        
        # TODO: Add more as we implement them
        # runtime.register_function('http.put', put)
        # runtime.register_function('http.delete', delete)
        
        print("Web pack registered successfully")
    except AttributeError as e:
        print(f"Warning: Could not register web pack: {e}")


# Export public API
__all__ = [
    'get',
    'post',
    'HTTPResponse',
    'register_capabilities',
    '__version__',
] 
