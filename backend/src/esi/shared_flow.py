"""
Contains shared OAuth 2.0 flow functions for EVE Online examples.

This module contains shared functions used between the two different OAuth 2.0
flows recommended for web-based and mobile/desktop applications. The functions
found here are used by the OAuth 2.0 examples contained in this project.
"""

import requests

from .validate_jwt import validate_eve_jwt


def print_auth_url(client_id: str, code_challenge: str = "") -> None:
    """
    Prints the URL to redirect users to for OAuth authorization.

    Args:
        client_id: The client ID of an EVE SSO application.
        code_challenge: A PKCE code challenge (optional).
    """
    base_auth_url = "https://login.eveonline.com/v2/oauth/authorize/"
    params = {
        "response_type": "code",
        "redirect_uri": "https://localhost/callback/",
        "client_id": client_id,
        "state": "unique-state",
    }

    # Define the required scopes
    scopes = [
        "esi-assets.read_assets.v1",
        "esi-location.read_location.v1",
        "esi-location.read_online.v1",
        "esi-ui.open_window.v1",
        "esi-ui.write_waypoint.v1",
    ]
    scope_param = "%20".join(scopes)
    params["scope"] = scope_param

    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    # Construct the full authorization URL
    request = requests.Request('GET', base_auth_url, params=params)
    prepared_request = request.prepare()
    full_auth_url = prepared_request.url

    print(
        "\nOpen the following link in your browser:\n\n"
        f"{full_auth_url}\n\n"
        "Once you have logged in as a character, you will be redirected to "
        "https://localhost/callback/."
    )


def send_token_request(form_values: dict[str, str], add_headers: dict[str, str] = {}) -> requests.Response:
    """
    Sends a request for an authorization token to the EVE SSO.

    Args:
        form_values: A dictionary containing the form-encoded values to send with the request.
        add_headers: A dictionary containing additional headers to send (optional).

    Returns:
        A requests.Response object containing the server's response.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    headers.update(add_headers)

    response = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )

    print(
        f"Request sent to URL {response.url} with headers {headers} and form values: {form_values}\n"
    )
    response.raise_for_status()

    return response


def handle_sso_token_response(sso_response: requests.Response) -> None:
    """
    Handles the authorization code response from the EVE SSO.

    Args:
        sso_response: A requests.Response object from the EVE SSO /v2/oauth/token endpoint.
    """
    if sso_response.status_code == 200:
        data = sso_response.json()
        access_token = data.get("access_token")

        print("\nVerifying access token JWT...")

        jwt = validate_eve_jwt(access_token)
        character_id = jwt["sub"].split(":")[2]
        character_name = jwt["name"]
        blueprint_url = f"https://esi.evetech.net/latest/characters/{character_id}/blueprints/"

        print(
            f"\nSuccess! Here is the payload received from the EVE SSO: {data}\n"
            "You can use the access token to make an authenticated request to "
            f"{blueprint_url}"
        )

        input("\nPress Enter to have this program make the request for you:")

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        res = requests.get(blueprint_url, headers=headers)
        print(
            f"\nMade request to {blueprint_url} with headers: {res.request.headers}"
        )
        res.raise_for_status()

        blueprints = res.json()
        print(f"\n{character_name} has {len(blueprints)} blueprints.")
    else:
        print(
            "\nSomething went wrong! Please re-read the comments at the top of this "
            "file and ensure you completed all the prerequisites, then try again. "
            "Here's some debug info to help you out:"
        )
        request_info = sso_response.request
        print(
            f"\nSent request with URL: {request_info.url}\n"
            f"Body: {request_info.body}\n"
            f"Headers: {request_info.headers}"
        )
        print(f"\nSSO response code is: {sso_response.status_code}")
        try:
            error_data = sso_response.json()
            print(f"\nSSO response JSON is: {error_data}")
        except ValueError:
            print("\nNo JSON response received from the SSO.")
