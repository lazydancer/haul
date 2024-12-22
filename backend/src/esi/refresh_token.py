import base64
import datetime
import os

from .shared_flow import send_token_request

def get_access_token_from_refresh_token(refresh_token: str) -> dict[str, any]:
    """
    Obtains a new access token using a refresh token.

    This function uses the provided refresh token to request a new access token
    from the authentication server. It updates the expiration time of the token.

    Args:
        refresh_token: The refresh token used to obtain a new access token.

    Returns:
        A dictionary containing the new access token data, including 'expires_at'.
    """
    client_id = os.getenv('CLIENT_ID')
    secret_key = os.getenv('SECRET_KEY')

    if not client_id or not secret_key:
        raise EnvironmentError("CLIENT_ID and SECRET_KEY must be set in environment variables.")

    user_pass = f"{client_id}:{secret_key}"
    basic_auth = base64.urlsafe_b64encode(user_pass.encode('utf-8')).decode()
    auth_header = f"Basic {basic_auth}"

    form_values = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers = {"Authorization": auth_header}

    response = send_token_request(form_values, add_headers=headers)
    data = response.json()

    current_timestamp = int(datetime.datetime.now().timestamp())
    data["expires_at"] = current_timestamp + data.get("expires_in", 0)

    return data
