"""
Data canonicalization utilities for web traffic anomaly detection.
"""
import hashlib
import re
import json
from typing import Dict, Any, Union
from urllib.parse import quote


def hash_sensitive_value(value: str, prefix: str = "HASH_") -> str:
    """
    Hash sensitive values to protect privacy while maintaining uniqueness.
    
    Args:
        value: The value to hash
        prefix: Prefix for the hashed value
    
    Returns:
        Hashed representation of the value
    """
    if not value:
        return "EMPTY"
    
    # Create a SHA-256 hash and take first 8 characters
    hash_obj = hashlib.sha256(value.encode('utf-8'))
    return f"{prefix}{hash_obj.hexdigest()[:8]}"


def redact_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Redact or hash sensitive header values.
    
    Args:
        headers: Dictionary of HTTP headers
    
    Returns:
        Dictionary with sensitive headers redacted
    """
    sensitive_headers = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token', 
        'api-key', 'token', 'session-id', 'x-session-token'
    }
    
    redacted = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_headers):
            redacted[key] = hash_sensitive_value(value, "HDR_")
        else:
            redacted[key] = value
    
    return redacted


def truncate_if_needed(text: str, max_length: int = 2048) -> str:
    """
    Truncate text if it exceeds the maximum length.
    
    Args:
        text: Text to potentially truncate
        max_length: Maximum allowed length
    
    Returns:
        Truncated text with indicator if truncation occurred
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 12] + "...[TRUNC]"


def canonicalize_request(log_entry: Union[Dict[str, Any], str]) -> str:
    """
    Convert a raw log entry into a standardized canonical string format.
    
    Format: [METHOD] <method> [PATH] <path> [PARAMS] <query_params> [HEADERS] <key1>:<value1>|<key2>:<value2>
    
    Args:
        log_entry: Raw log entry as dictionary or JSON string
    
    Returns:
        Canonicalized request string
    """
    # Parse input if it's a JSON string
    if isinstance(log_entry, str):
        try:
            log_entry = json.loads(log_entry)
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text and create minimal structure
            return f"[METHOD] UNKNOWN [PATH] {truncate_if_needed(log_entry)} [PARAMS]  [HEADERS] "
    
    # Extract method
    method = log_entry.get('method', log_entry.get('http_method', log_entry.get('m', 'UNKNOWN'))).upper()
    
    # Extract path
    path = log_entry.get('path', log_entry.get('url', log_entry.get('uri', log_entry.get('p', '/'))))
    path = truncate_if_needed(path, 512)
    
    # Extract query parameters
    params = log_entry.get('query_params', log_entry.get('params', log_entry.get('q', {})))
    if isinstance(params, str):
        params_str = truncate_if_needed(params, 512)
    elif isinstance(params, dict):
        # Sort parameters for consistency
        param_pairs = []
        for key, value in sorted(params.items()):
            # Hash sensitive parameter values
            if any(sensitive in key.lower() for sensitive in ['password', 'token', 'key', 'secret', 'auth']):
                value = hash_sensitive_value(str(value), "PARAM_")
            param_pairs.append(f"{key}={quote(str(value))}")
        params_str = "&".join(param_pairs)
        params_str = truncate_if_needed(params_str, 512)
    else:
        params_str = ""
    
    # Extract and process headers
    headers = log_entry.get('headers', log_entry.get('h', {}))
    if isinstance(headers, dict):
        # Handle the special structure in your data where headers contain ua, ct, cl, cookieKeys
        processed_headers = {}
        
        # Map short names to full names
        if 'ua' in headers:
            processed_headers['user-agent'] = headers['ua']
        if 'ct' in headers:
            processed_headers['content-type'] = headers['ct']
        if 'cl' in headers:
            processed_headers['content-length'] = str(headers['cl'])
        if 'cookieKeys' in headers and isinstance(headers['cookieKeys'], list):
            # Convert cookie keys to a cookie-like header
            processed_headers['cookie-keys'] = ','.join(headers['cookieKeys'])
        
        # Add any other headers that don't match the short names
        for key, value in headers.items():
            if key not in ['ua', 'ct', 'cl', 'cookieKeys']:
                processed_headers[key.lower()] = str(value)
        
        headers = redact_sensitive_headers(processed_headers)
        # Sort headers for consistency and format as key:value pairs
        header_pairs = []
        for key, value in sorted(headers.items()):
            value = truncate_if_needed(str(value), 256)
            header_pairs.append(f"{key}:{value}")
        headers_str = "|".join(header_pairs)
        headers_str = truncate_if_needed(headers_str, 1024)
    else:
        headers_str = ""
    
    # Process request body if present
    body = log_entry.get('body', log_entry.get('request_body', ''))
    if body:
        body = truncate_if_needed(str(body), 512)
        # Add body to headers section with special prefix
        if headers_str:
            headers_str += f"|body:{hash_sensitive_value(body, 'BODY_')}"
        else:
            headers_str = f"body:{hash_sensitive_value(body, 'BODY_')}"
    
    # Construct canonical format
    canonical = f"[METHOD] {method} [PATH] {path} [PARAMS] {params_str} [HEADERS] {headers_str}"
    
    # Final truncation as safety measure
    return truncate_if_needed(canonical, 2048)


def canonicalize_batch(log_entries: list) -> list:
    """
    Canonicalize a batch of log entries.
    
    Args:
        log_entries: List of log entries to canonicalize
    
    Returns:
        List of canonicalized request strings
    """
    return [canonicalize_request(entry) for entry in log_entries]


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        {
            "method": "GET",
            "path": "/api/users",
            "query_params": {"page": "1", "limit": "10"},
            "headers": {
                "User-Agent": "Mozilla/5.0",
                "Authorization": "Bearer secret123",
                "Content-Type": "application/json"
            }
        },
        {
            "method": "POST",
            "path": "/login",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": "username=admin&password=secret"
        },
        '{"method": "PUT", "path": "/api/data", "headers": {"X-API-Key": "abc123"}}',
        "Invalid JSON string that should be handled gracefully"
    ]
    
    print("Testing canonicalization function:")
    for i, test_case in enumerate(test_cases, 1):
        result = canonicalize_request(test_case)
        print(f"\nTest {i}:")
        print(f"Input: {test_case}")
        print(f"Output: {result}")