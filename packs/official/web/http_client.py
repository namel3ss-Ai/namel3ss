"""HTTP Client capability for namel3ss"""

from typing import Dict, Any, Optional
import requests

class HTTPResponse:
    def __init__(self, response):
        self._response = response
    
    @property
    def status(self) -> int:
        return self._response.status_code
    
    @property
    def ok(self) -> bool:
        return self._response.ok
    
    def json(self) -> Any:
        return self._response.json()
    
    @property
    def text(self) -> str:
        return self._response.text

def get(url: str, headers: Optional[Dict] = None) -> HTTPResponse:
    """Make a GET request"""
    response = requests.get(url, headers=headers, timeout=30)
    return HTTPResponse(response)

def post(url: str, json: Optional[Any] = None) -> HTTPResponse:
    """Make a POST request"""
    response = requests.post(url, json=json, timeout=30)
    return HTTPResponse(response)