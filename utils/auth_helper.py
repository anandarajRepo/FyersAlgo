import hashlib
import logging

logger = logging.getLogger(__name__)


class FyersAuthHelper:
    """Helper for Fyers authentication"""

    @staticmethod
    def generate_auth_url(client_id: str, redirect_uri: str) -> str:
        """Generate authorization URL"""
        auth_url = "https://api-t1.fyers.in/api/v3/generate-authcode"
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'state': 'sample_state'
        }

        url = f"{auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    @staticmethod
    def generate_access_token(client_id: str, secret_key: str, auth_code: str) -> str:
        """Generate access token from auth code"""
        import requests

        try:
            url = "https://api-t1.fyers.in/api/v3/validate-authcode"

            data = {
                'grant_type': 'authorization_code',
                'appIdHash': hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest(),
                'code': auth_code
            }

            response = requests.post(url, json=data)

            if response.status_code == 200:
                result = response.json()
                if result['s'] == 'ok':
                    return result['access_token']
                else:
                    logger.error(f"Token generation failed: {result['message']}")
                    return None
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            return None