"""
Validates a given JWT access token originating from the EVE SSO.

Prerequisites:
    * Have a Python 3 environment available (possibly using a virtual environment).
    * Run pip install -r requirements.txt with this directory as your root.

This script can be run by executing:

>>> python validate_jwt.py

and providing a JWT access token that you have retrieved from the EVE SSO.
"""

import sys
from typing import Any

import requests
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

SSO_META_DATA_URL = "https://login.eveonline.com/.well-known/oauth-authorization-server"
JWK_ALGORITHM = "RS256"
JWK_ISSUERS = ("login.eveonline.com", "https://login.eveonline.com")
JWK_AUDIENCE = "EVE Online"


def validate_eve_jwt(token: str) -> dict[str, Any]:
    """
    Validates a JWT access token retrieved from the EVE SSO.

    Args:
        token: A JWT access token originating from the EVE SSO.

    Returns:
        The contents of the validated JWT access token.

    Raises:
        RuntimeError: If required data is missing from the SSO endpoints.
        jose.exceptions.JWTError: If the token is invalid or expired.
    """
    response = requests.get(SSO_META_DATA_URL)
    response.raise_for_status()
    metadata = response.json()

    jwks_uri = metadata.get("jwks_uri")
    if not jwks_uri:
        raise RuntimeError(f"Invalid data received from the SSO metadata endpoint: {metadata}")

    response = requests.get(jwks_uri)
    response.raise_for_status()
    jwks_data = response.json()

    jwk_keys = jwks_data.get("keys")
    if not jwk_keys:
        raise RuntimeError(f"Invalid data received from the JWKS endpoint: {jwks_data}")

    jwk = next((item for item in jwk_keys if item["alg"] == JWK_ALGORITHM), None)
    if not jwk:
        raise RuntimeError(f"No JWK found with algorithm {JWK_ALGORITHM}")

    # Decode and validate the token
    contents = jwt.decode(
        token=token,
        key=jwk,
        algorithms=[JWK_ALGORITHM],
        issuer=JWK_ISSUERS,
        audience=JWK_AUDIENCE,
    )
    return contents


def main() -> None:
    """
    Entry point of the script. Prompts the user for a JWT token and validates it.
    """
    token = input("Enter an access token to validate: ")

    try:
        token_contents = validate_eve_jwt(token)
    except ExpiredSignatureError:
        print("The JWT token has expired.")
        sys.exit(1)
    except JWTError as e:
        print(f"The JWT token is invalid: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    else:
        print("\nThe contents of the access token are:")
        for key, value in token_contents.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
