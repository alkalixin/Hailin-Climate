"""Authentication module for HaiLin Climate integration."""

import asyncio
import logging
from typing import Any, Optional

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
        self.login_type = None
        self.username = None
        self.password = None

    async def login(
        self, login_type: str, username: str, password: str
    ) -> Optional[str]:
        """
        Login to HaiLin service and return access token.

        Args:
            login_type: Login type ("email" or "mobile")
            username: Username/email/phone
            password: Password

        Returns:
            Access token if successful, None otherwise
        """
        _LOGGER.info("Attempting to login to HaiLin service")
        _LOGGER.debug("Login type: %s, Username: %s", login_type, username)

        self.login_type = login_type
        self.username = username
        self.password = password

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
                timeout=30,
            ) as response:
                _LOGGER.debug("Received response with status: %s", response.status)
                _LOGGER.debug("Response headers: %s", dict(response.headers))

                if response.status == 200:
                    result = await response.json()
                    _LOGGER.debug("Response body: %s", result)

                    if result and "access_token" in result:
                        access_token = result["access_token"]
                        self.token = access_token
                        _LOGGER.info(
                            "Successfully logged in to HaiLin for user: %s", username
                        )
                        _LOGGER.debug(
                            "Access token received (first 10 chars): %s",
                            access_token[:10] + "...",
                        )
                        return access_token

                    _LOGGER.error(
                        "Login response missing access_token. Response keys: %s",
                        list(result.keys()) if result else "None",
                    )
                    return None

                response_text = await response.text()
                _LOGGER.error(
                    "Login failed with status %s. Response: %s",
                    response.status,
                    response_text,
                )
                return None

        except Exception as err:
            _LOGGER.error("Failed to login to HaiLin: %s", str(err))
            _LOGGER.debug("Exception type: %s", type(err).__name__)
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

    async def _retry_after_auth_failure(
        self,
        url: str,
        data: Any = None,
        method: str = "POST",
        retry_on_auth: bool = True,
    ):
        """Retry the request once after refreshing an expired token."""
        if not retry_on_auth:
            return None

        if not all([self.login_type, self.username, self.password]):
            _LOGGER.error(
                "Cannot retry request after authentication failure: credentials unavailable"
            )
            self.clear_token()
            return None

        _LOGGER.warning(
            "Authentication expired for %s request, attempting to re-login", method
        )
        self.clear_token()

        token = await self.login(self.login_type, self.username, self.password)
        if not token:
            _LOGGER.error("Re-login failed after authentication expiry")
            return None

        _LOGGER.info("Re-login succeeded, retrying %s request", method)
        return await self.request(url, data=data, method=method, retry_on_auth=False)

    async def request(
        self,
        url,
        data=None,
        method="POST",
        retry_on_auth: bool = True,
        retry_on_error: bool = True,
    ):
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
                async with self.session.get(url, headers=headers, timeout=30) as response:
                    _LOGGER.debug("Received response with status: %s", response.status)

                    if response.status == 200:
                        result = await response.json()
                        _LOGGER.debug("Request successful, response: %s", result)
                        return result

                    response_text = await response.text()
                    if response.status == 401:
                        _LOGGER.warning(
                            "Request failed with status 401. Response: %s",
                            response_text,
                        )
                        return await self._retry_after_auth_failure(
                            url,
                            data=data,
                            method=method,
                            retry_on_auth=retry_on_auth,
                        )

                    _LOGGER.error(
                        "Request failed with status %s. Response: %s",
                        response.status,
                        response_text,
                    )
                    return None

            if isinstance(data, str):
                async with self.session.post(
                    url,
                    headers=headers,
                    data=data,
                    timeout=30,
                ) as response:
                    _LOGGER.debug("Received response with status: %s", response.status)

                    if response.status == 200:
                        result = await response.json()
                        _LOGGER.debug("Request successful, response: %s", result)
                        return result

                    response_text = await response.text()
                    if response.status == 401:
                        _LOGGER.warning(
                            "Request failed with status 401. Response: %s",
                            response_text,
                        )
                        return await self._retry_after_auth_failure(
                            url,
                            data=data,
                            method=method,
                            retry_on_auth=retry_on_auth,
                        )

                    _LOGGER.error(
                        "Request failed with status %s. Response: %s",
                        response.status,
                        response_text,
                    )
                    return None

            async with self.session.post(
                url,
                headers=headers,
                json=data,
                timeout=30,
            ) as response:
                _LOGGER.debug("Received response with status: %s", response.status)

                if response.status == 200:
                    result = await response.json()
                    _LOGGER.debug("Request successful, response: %s", result)
                    return result

                response_text = await response.text()
                if response.status == 401:
                    _LOGGER.warning(
                        "Request failed with status 401. Response: %s",
                        response_text,
                    )
                    return await self._retry_after_auth_failure(
                        url,
                        data=data,
                        method=method,
                        retry_on_auth=retry_on_auth,
                    )

                _LOGGER.error(
                    "Request failed with status %s. Response: %s",
                    response.status,
                    response_text,
                )
                return None

        except Exception as err:
            if retry_on_error:
                _LOGGER.warning(
                    "Request error: %s. Retrying %s request once.",
                    str(err),
                    method,
                )
                await asyncio.sleep(1)
                return await self.request(
                    url,
                    data=data,
                    method=method,
                    retry_on_auth=retry_on_auth,
                    retry_on_error=False,
                )

            _LOGGER.error("Request error: %s", str(err))
            _LOGGER.debug("Exception type: %s", type(err).__name__)
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

        result = await self.request(HOUSE_URL, method="GET")
        _LOGGER.debug("Houses response: %s", result)

        if result and "id" in result:
            house = {
                "house_id": result["id"],
                "name": result.get("house_name", "Unknown"),
                "user_id": result.get("user_id"),
                "position": result.get("position", ""),
            }
            houses = [house]
            _LOGGER.info(
                "Successfully got 1 house from HaiLin service: %s",
                house["name"],
            )
            return houses

        _LOGGER.error(
            "Houses response missing id. Response keys: %s",
            list(result.keys()) if result else "None",
        )
        return []
