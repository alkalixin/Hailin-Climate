"""Authentication module for HaiLin Climate integration."""
import logging
from typing import Optional

from homeassistant.helpers import aiohttp_client

from .const import AUTH_URL, HOUSE_URL

_LOGGER = logging.getLogger(__name__)


class HaiLinAuth:
    """HaiLin authentication handler."""

    def __init__(self, hass, session=None):
        """Initialize the auth handler."""
        self.hass = hass
        self.session = session
        self.token = None

    async def login(self, login_type: str, username: str, password: str) -> Optional[str]:
        """
        Login to HaiLin service and return access token.
        
        Args:
            login_type: Login type ('email' or 'mobile')
            username: Username/email/phone
            password: Password
            
        Returns:
            Access token if successful, None otherwise
        """
        _LOGGER.info("Attempting to login to HaiLin service")
        _LOGGER.debug("Login type: %s, Username: %s", login_type, username)
        
        if not self.session:
            _LOGGER.debug("Creating new HTTP session")
            self.session = aiohttp_client.async_get_clientsession(self.hass)
        
        data = {
            "clientId": 1,
            "client_secret": "d0404a5b1b5d6b6a6db049d441804188",
            "username": username,
            "password": password,
            "oauth_type": login_type,
        }
        
        headers = {
            "User-Agent": "okhttp/3.8.0",
            "Content-Type": "application/json",
        }
        
        _LOGGER.debug("Sending login request to: %s", AUTH_URL)
        _LOGGER.debug("Request headers: %s", headers)
        _LOGGER.debug("Request data (password hidden): %s", {**data, "password": "***"})
        
        try:
            async with self.session.post(
                AUTH_URL,
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                _LOGGER.debug("Received response with status: %s", response.status)
                _LOGGER.debug("Response headers: %s", dict(response.headers))
                
                if response.status == 200:
                    result = await response.json()
                    _LOGGER.debug("Response body: %s", result)
                    
                    if result and "access_token" in result:
                        access_token = result["access_token"]
                        self.token = access_token
                        _LOGGER.info("Successfully logged in to HaiLin for user: %s", username)
                        _LOGGER.debug("Access token received (first 10 chars): %s", 
                                    access_token[:10] + "...")
                        return access_token
                    else:
                        _LOGGER.error("Login response missing access_token. Response keys: %s", 
                                    list(result.keys()) if result else "None")
                        return None
                else:
                    response_text = await response.text()
                    _LOGGER.error("Login failed with status %s. Response: %s", response.status, response_text)
                    return None
                    
        except Exception as e:
            _LOGGER.error("Failed to login to HaiLin: %s", str(e))
            _LOGGER.debug("Exception type: %s", type(e).__name__)
            import traceback
            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            return None

    def get_token(self) -> Optional[str]:
        """Get the current access token."""
        return self.token

    def set_token(self, token: str) -> None:
        """Set the access token."""
        self.token = token

    def clear_token(self) -> None:
        """Clear the access token."""
        self.token = None

    async def request(self, url, data=None, method="POST"):
        """Make HTTP request."""
        _LOGGER.debug("Making %s request to: %s", method, url)
        if data:
            _LOGGER.debug("Request data: %s", data)

        if not self.session:
            _LOGGER.debug("Creating new HTTP session")
            self.session = aiohttp_client.async_get_clientsession(self.hass)

        headers = {
            "User-Agent": "okhttp/3.8.0",
            "Content-Type": "application/json",
        }

        token = self.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            _LOGGER.debug(
                "Using token for authentication (first 10 chars): %s",
                token[:10] + "...",
            )
        else:
            _LOGGER.debug("No token available for authentication")

        _LOGGER.debug("Request headers: %s", {**headers, "Authorization": "Bearer ***"})

        try:
            _LOGGER.debug("Sending %s request with timeout 30s", method)

            if method == "GET":
                async with self.session.get(
                    url, headers=headers, timeout=30
                ) as response:
                    _LOGGER.debug("Received response with status: %s", response.status)

                    if response.status == 200:
                        result = await response.json()
                        _LOGGER.debug("Request successful, response: %s", result)
                        return result
                    else:
                        response_text = await response.text()
                        _LOGGER.error(
                            "Request failed with status %s. Response: %s",
                            response.status,
                            response_text,
                        )
                        return None
            else:  # POST
                # 处理data可能是JSON字符串的情况
                if isinstance(data, str):
                    # 如果是JSON字符串，直接发送
                    async with self.session.post(
                        url,
                        headers=headers,
                        data=data,  # 使用data而不是json
                        timeout=30,
                    ) as response:
                        _LOGGER.debug(
                            "Received response with status: %s", response.status
                        )

                        if response.status == 200:
                            result = await response.json()
                            _LOGGER.debug("Request successful, response: %s", result)
                            return result
                        else:
                            response_text = await response.text()
                            _LOGGER.error(
                                "Request failed with status %s. Response: %s",
                                response.status,
                                response_text,
                            )
                            return None
                else:
                    # 如果是字典，使用json参数
                    async with self.session.post(
                        url, headers=headers, json=data, timeout=30
                    ) as response:
                        _LOGGER.debug(
                            "Received response with status: %s", response.status
                        )

                        if response.status == 200:
                            result = await response.json()
                            _LOGGER.debug("Request successful, response: %s", result)
                            return result
                        else:
                            response_text = await response.text()
                            _LOGGER.error(
                                "Request failed with status %s. Response: %s",
                                response.status,
                                response_text,
                            )
                            return None

        except Exception as e:
            _LOGGER.error("Request error: %s", str(e))
            _LOGGER.debug("Exception type: %s", type(e).__name__)
            import traceback

            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            return None

    async def get_houses(self) -> list:
        """
        Get all houses for the authenticated user.
        
        Returns:
            List of house dictionaries with house_id and other info
        """
        if not self.token:
            _LOGGER.error("No token available, cannot get houses")
            return []
        
        _LOGGER.info("Fetching houses from HaiLin service")
        
        headers = {
            "User-Agent": "okhttp/3.8.0",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        _LOGGER.debug("Sending GET request to: %s", HOUSE_URL)
        _LOGGER.debug("Request headers: %s", {**headers, "Authorization": "Bearer ***"})
        
        try:
            async with self.session.get(
                HOUSE_URL,
                headers=headers,
                timeout=30
            ) as response:
                _LOGGER.debug("Received response with status: %s", response.status)
                
                if response.status == 200:
                    result = await response.json()
                    _LOGGER.debug("Houses response: %s", result)
                    
                    if result and "id" in result:
                        # API返回单个房屋对象，转换为列表格式
                        house = {
                            "house_id": result["id"],
                            "name": result.get("house_name", "Unknown"),
                            "user_id": result.get("user_id"),
                            "position": result.get("position", "")
                        }
                        houses = [house]
                        _LOGGER.info("Successfully got 1 house from HaiLin service: %s", house["name"])
                        return houses
                    else:
                        _LOGGER.error("Houses response missing id. Response keys: %s", 
                                    list(result.keys()) if result else "None")
                        return []
                else:
                    response_text = await response.text()
                    _LOGGER.error("Failed to get houses with status %s. Response: %s", response.status, response_text)
                    return []
                    
        except Exception as e:
            _LOGGER.error("Failed to get houses: %s", str(e))
            _LOGGER.debug("Exception type: %s", type(e).__name__)
            import traceback
            _LOGGER.debug("Full traceback: %s", traceback.format_exc())
            return []
