import requests
import logging
from typing import Dict, Any, Optional

class RestUtil:
    """Utility class for making REST API calls"""
    
    BASE_URL = "http://localhost:8000"  # Default base URL, can be configured
    
    @classmethod
    def set_base_url(cls, base_url: str) -> None:
        """Set the base URL for API calls
        
        Args:
            base_url: The base URL for the API server
        """
        cls.BASE_URL = base_url.rstrip('/')
    
    @classmethod
    def make_post_call(cls, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a POST request to the specified endpoint with the given payload
        
        Args:
            endpoint: The API endpoint (e.g., '/api/resource')
            payload: Dictionary containing the request payload
            
        Returns:
            Dictionary containing the response data if successful, None otherwise
        """
        try:
            # Ensure endpoint starts with /
            if not endpoint.startswith('/'):
                endpoint = f'/{endpoint}'
                
            url = f"{cls.BASE_URL}{endpoint}"
            
            logging.info(f"Making POST request to {url}")
            logging.debug(f"Request payload: {payload}")
            
            # Make the POST request
            response = requests.post(
                url,
                json=payload,
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            # Parse and return the response
            result = response.json()
            logging.debug(f"Response received: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP Request failed: {str(e)}", exc_info=True)
            return None
        except Exception as e:
            logging.error(f"Unexpected error in make_post_call: {str(e)}", exc_info=True)
            return None
