import logging

import aiohttp
import bs4

from .error import GreenchoiceError

from .const import BASE_URL, SSO_URL


class LoginError(GreenchoiceError):
    pass


_logger = logging.getLogger(__name__)


async def _get_antiforgery_token(session: aiohttp.ClientSession) -> str | None:
    """Get the antiforgery token from the API."""
    response = await session.get(f"{SSO_URL}/api/antiforgery")
    response.raise_for_status()
    body = await response.json()
    return body.get("requestToken")


def _get_oidc_params(html_txt: str) -> dict[str, str]:
    soup = bs4.BeautifulSoup(html_txt, "html.parser")

    code_elem = soup.find("input", {"name": "code"})
    scope_elem = soup.find("input", {"name": "scope"})
    state_elem = soup.find("input", {"name": "state"})
    session_state_elem = soup.find("input", {"name": "session_state"})

    if not (code_elem and scope_elem and state_elem and session_state_elem):
        raise LoginError("Login failed, check your credentials?")

    return {
        "code": code_elem.attrs.get("value"),
        "scope": scope_elem.attrs.get("value").replace(" ", "+"),
        "state": state_elem.attrs.get("value"),
        "session_state": session_state_elem.attrs.get("value"),
    }


async def _login(session: aiohttp.ClientSession, username: str, password: str):
    _logger.info("Retrieving login cookies")

    # Get the antiforgery token
    antiforgery_token = await _get_antiforgery_token(session)
    if not antiforgery_token:
        raise LoginError("Failed to retrieve antiforgery token")

    # Get the login page to extract returnUrl
    login_page = await session.get(BASE_URL)
    return_url = login_page.url.query.get("ReturnUrl", "")

    # Perform actual sign in with new parameters
    _logger.debug("Logging in with username and password")
    login_data = {
        "username": username,
        "password": password,
        "returnUrl": return_url,
        "rememberMe": True,
    }
    # Set the required headers
    headers = {
        "requestverificationtoken": antiforgery_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": SSO_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    login_url = f"{SSO_URL}/api/login"
    auth_page = await session.post(login_url, json=login_data, headers=headers)
    auth_page.raise_for_status()
    # Handle the JSON response with redirect URI
    login_response: dict = await auth_page.json()
    if login_response.get("validationProblemDetails"):
        raise LoginError(
            f"Login validation failed: {login_response['validationProblemDetails']}"
        )

    redirect_uri = login_response.get("redirectUri")
    if not redirect_uri:
        raise LoginError("No redirect URI received from login")

    # Follow the redirect to complete OAuth flow
    _logger.debug("Following OAuth redirect")
    oauth_response = await session.get(f"{SSO_URL}{redirect_uri}")
    oauth_response.raise_for_status()

    # Continue with OIDC flow
    _logger.debug("Signing in using OIDC")
    oauth_content = await oauth_response.text()
    oidc_params = _get_oidc_params(oauth_content)
    response = await session.post(f"{BASE_URL}/signin-oidc", data=oidc_params)
    response.raise_for_status()

    _logger.debug("Login success")


async def setup_auth(session: aiohttp.ClientSession, username: str, password: str):
    try:
        await _login(session, username, password)
    except aiohttp.ClientError as ex:
        _logger.error("Login failed! Please check your credentials and try again.")
        raise GreenchoiceError from ex
