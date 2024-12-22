"""
Python 3 Web Application OAuth 2.0 Example.

This script demonstrates how to perform the OAuth 2.0 authorization code flow
for a web-based application using the EVE Online SSO.

Prerequisites:
    * Create an SSO application at https://developers.eveonline.com with the
      scope "esi-characters.read_blueprints.v1" and the callback URL
      "https://localhost/callback/". Note: Never use localhost as a callback
      in production applications.
    * Have a Python 3 environment available (possibly by using a virtual
      environment: https://virtualenv.pypa.io/en/stable/).
    * Install the required packages by running:
      pip install -r requirements.txt

To run this example, make sure you have completed the prerequisites and then
run the following command:

>>> python esi_oauth_web.py

Then follow the prompts.
"""

import base64
import os
from typing import Optional

from dotenv import load_dotenv

from shared_flow import (
    handle_sso_token_response,
    print_auth_url,
    send_token_request,
)


def main() -> None:
    """
    Guides you through a local example of the OAuth 2.0 web flow.
    """
    print(
        "This program will take you through an example OAuth 2.0 flow "
        "that you should be using if you are building a web-based "
        "application. Follow the prompts and enter the information requested."
    )

    client_id: Optional[str] = os.getenv('CLIENT_ID')
    if not client_id:
        raise ValueError("CLIENT_ID not found in environment variables.")

    print_auth_url(client_id)

    auth_code: str = input('Copy the "code" query parameter and enter it here: ')

    # Basic auth can be handled by the requests library with the auth parameter,
    # but we're constructing it manually for educational purposes.
    secret_key: Optional[str] = os.getenv('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY not found in environment variables.")

    user_pass: str = f"{client_id}:{secret_key}"
    basic_auth: str = base64.urlsafe_b64encode(user_pass.encode('utf-8')).decode()
    auth_header: str = f"Basic {basic_auth}"

    form_values: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": auth_code,
    }

    headers: dict[str, str] = {"Authorization": auth_header}

    print(
        "\nThe following request uses basic authentication, as a web-based "
        "app you should do the same."
    )

    input("\nPress Enter to continue...")

    res = send_token_request(form_values, add_headers=headers)

    handle_sso_token_response(res)


if __name__ == "__main__":
    load_dotenv()
    main()
