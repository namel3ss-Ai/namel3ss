"""Tests for HTTP client"""

import pytest
from unittest.mock import Mock, patch
from packs.official.web.http_client import get, post, HTTPResponse

@patch('requests.get')
def test_get_request(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_get.return_value = mock_response
    
    response = get("https://api.example.com/users")
    
    assert response.status == 200
    assert response.ok is True

@patch('requests.post')
def test_post_request(mock_post):
    mock_response = Mock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response
    
    response = post("https://api.example.com/users", json={"name": "John"})
    
    assert response.status == 201 
