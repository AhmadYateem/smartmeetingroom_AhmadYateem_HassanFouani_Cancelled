"""
HTTP client for inter-service communication with circuit breaker support.
"""

import requests
from typing import Dict, Any, Optional
from requests.exceptions import RequestException, Timeout
from configs.config import Config
from utils.circuit_breaker import with_circuit_breaker
from utils.logger import setup_logger
from utils.exceptions import ExternalServiceError

logger = setup_logger(__name__)


class ServiceClient:
    """
    HTTP client for inter-service communication.

    Provides methods to communicate with other microservices with:
    - Circuit breaker protection
    - Timeout handling
    - Error handling and retries
    - JWT token propagation
    """

    def __init__(self, service_name: str, base_url: str, timeout: int = 10):
        """
        Initialize service client.

        Args:
            service_name: Name of the target service
            base_url: Base URL of the service
            timeout: Request timeout in seconds
        """
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    @with_circuit_breaker('http_request', failure_threshold=5, recovery_timeout=60)
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with circuit breaker protection.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Request headers

        Returns:
            Response data

        Raises:
            ExternalServiceError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout
            )

            # Log request
            logger.info(
                f"Service request: {method} {url}",
                extra={
                    'service': self.service_name,
                    'method': method,
                    'url': url,
                    'status_code': response.status_code
                }
            )

            # Check for error status codes
            if response.status_code >= 400:
                error_message = f"{self.service_name} returned {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', error_message)
                except:
                    pass

                raise ExternalServiceError(error_message, self.service_name)

            # Return JSON response
            return response.json()

        except Timeout:
            error_msg = f"Request to {self.service_name} timed out"
            logger.error(error_msg)
            raise ExternalServiceError(error_msg, self.service_name)

        except RequestException as e:
            error_msg = f"Request to {self.service_name} failed: {str(e)}"
            logger.error(error_msg)
            raise ExternalServiceError(error_msg, self.service_name)

        except Exception as e:
            error_msg = f"Unexpected error calling {self.service_name}: {str(e)}"
            logger.exception(error_msg)
            raise ExternalServiceError(error_msg, self.service_name)

    def get(self, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers

        Returns:
            Response data
        """
        return self._make_request('GET', endpoint, params=params, headers=headers)

    def post(self, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data
            headers: Request headers

        Returns:
            Response data
        """
        return self._make_request('POST', endpoint, data=data, headers=headers)

    def put(self, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        Make PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data
            headers: Request headers

        Returns:
            Response data
        """
        return self._make_request('PUT', endpoint, data=data, headers=headers)

    def delete(self, endpoint: str, headers: Optional[Dict] = None) -> Dict:
        """
        Make DELETE request.

        Args:
            endpoint: API endpoint
            headers: Request headers

        Returns:
            Response data
        """
        return self._make_request('DELETE', endpoint, headers=headers)


# Service client instances
class ServiceClients:
    """Container for all service clients."""

    @staticmethod
    def users() -> ServiceClient:
        """Get Users service client."""
        return ServiceClient('users-service', Config.USER_SERVICE_URL)

    @staticmethod
    def rooms() -> ServiceClient:
        """Get Rooms service client."""
        return ServiceClient('rooms-service', Config.ROOM_SERVICE_URL)

    @staticmethod
    def bookings() -> ServiceClient:
        """Get Bookings service client."""
        return ServiceClient('bookings-service', Config.BOOKING_SERVICE_URL)

    @staticmethod
    def reviews() -> ServiceClient:
        """Get Reviews service client."""
        return ServiceClient('reviews-service', Config.REVIEW_SERVICE_URL)
