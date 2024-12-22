"""
A simplified API for interacting with the EVE Online ESI API.
"""

import datetime
import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .refresh_token import get_access_token_from_refresh_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ESI_BASE_URL = "https://esi.evetech.net/latest"
DATASOURCE = "tranquility"
USER_AGENT_HEADER = {'User-Agent': 'Haul (Hyperspace Asset Unloading and Loading)'}
CACHE_DIR = Path(__file__).resolve().parent.parent / 'cache'
AUTH_FILE = CACHE_DIR / 'auth.json'
ERROR_LIMIT_THRESHOLD = 50  # ESI Error limit threshold
REQUEST_RATE_LIMIT = 0.05  # Time in seconds between requests to avoid rate limiting


def get_location() -> int:
    """
    Gets the current location of the character.

    Returns:
        The location ID of the character (station ID or solar system ID).
    """
    character_id = os.getenv('character_id')
    if not character_id:
        logger.error("Character ID not found in environment variables.")
        raise EnvironmentError("Character ID not set in environment variables.")

    url = f"{ESI_BASE_URL}/characters/{character_id}/location/"

    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": f"Bearer {access_token()}",
        **USER_AGENT_HEADER,
    }

    params = {
        "datasource": DATASOURCE,
    }

    response = requests.get(url, params=params, headers=headers)
    logger.debug(f"Request URL: {response.url}")
    logger.debug(f"Response Status Code: {response.status_code}")

    if response.status_code == 401:
        logger.info("Access token expired, refreshing token.")
        access_token(force_refresh=True)
        headers["Authorization"] = f"Bearer {access_token()}"
        response = requests.get(url, params=params, headers=headers)

    if int(response.headers.get("X-Esi-Error-Limit-Remain", 100)) < ERROR_LIMIT_THRESHOLD:
        logger.warning("Approaching ESI Error Limit.")
        raise Exception("ESI Error Limit approaching threshold.")

    response.raise_for_status()
    data: dict[str, Any] = response.json()

    location_id = data.get("station_id") or data.get("solar_system_id")
    if not location_id:
        logger.error("Location ID not found in response.")
        raise ValueError("Unable to determine character's location.")

    logger.info(f"Character location ID: {location_id}")
    return location_id


def set_waypoints(waypoints: list[int]) -> None:
    """
    Sets the waypoints for the character's autopilot.

    Args:
        waypoints: A list of waypoint IDs to set.
    """
    if not waypoints:
        logger.warning("No waypoints provided.")
        return

    url = f"{ESI_BASE_URL}/ui/autopilot/waypoint/"

    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": f"Bearer {access_token()}",
        **USER_AGENT_HEADER,
    }

    for index, waypoint in enumerate(waypoints):
        params = {
            "add_to_beginning": False,
            "clear_other_waypoints": index == 0,
            "destination_id": waypoint,
            "datasource": DATASOURCE,
        }

        try:
            response = requests.post(url, params=params, headers=headers)
            response.raise_for_status()
            logger.info(f"Waypoint {waypoint} set successfully.")
            time.sleep(1)  # Rate limiting
        except requests.HTTPError as e:
            logger.error(f"Failed to set waypoint {waypoint}: {e}")
            continue


def open_market_window(type_id: int) -> None:
    """
    Opens the market window for a specific item type in the game client.

    Args:
        type_id: The type ID of the item.
    """
    url = f"{ESI_BASE_URL}/ui/openwindow/marketdetails/"

    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": f"Bearer {access_token()}",
        **USER_AGENT_HEADER,
    }

    params = {
        "type_id": type_id,
        "datasource": DATASOURCE,
    }

    try:
        response = requests.post(url, params=params, headers=headers)
        response.raise_for_status()
        logger.info(f"Market window opened for type ID {type_id}.")
    except requests.HTTPError as e:
        logger.error(f"Failed to open market window for type ID {type_id}: {e}")


def get_region_orders(region_id: int) -> tuple[list[dict[str, Any]], str]:
    """
    Retrieves all market orders for a given region.

    Args:
        region_id: The ID of the region.

    Returns:
        A tuple containing the list of orders and the expiry time.
    """
    def request_orders(region: int, page: int, q: queue.Queue) -> None:
        url = f"{ESI_BASE_URL}/markets/{region}/orders/"
        params = {
            'datasource': DATASOURCE,
            'order_type': 'all',
            'page': page,
        }
        headers = USER_AGENT_HEADER

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            logger.debug(f"Retrieved page {page} for region {region}.")
            q.put(response)
        except requests.HTTPError as e:
            logger.error(f"Error fetching page {page} for region {region}: {e}")

    order_queue = queue.Queue()
    request_orders(region_id, 1, order_queue)  # Get the first page
    first_response = order_queue.get()
    pages = int(first_response.headers.get('X-Pages', '1'))
    expires = first_response.headers.get('Expires', '')

    if pages > 1:
        threads = []
        for page in range(2, pages + 1):
            thread = threading.Thread(target=request_orders, args=(region_id, page, order_queue))
            threads.append(thread)
            thread.start()
            time.sleep(REQUEST_RATE_LIMIT)  # Rate limiting

        for thread in threads:
            thread.join()

    results: list[dict[str, Any]] = first_response.json()
    while not order_queue.empty():
        response = order_queue.get()
        results.extend(response.json())

    # Filter out orders with zero remaining volume
    results = [order for order in results if order.get('volume_remain', 0) > 0]

    # Add region ID to each order
    for order in results:
        order['region_id'] = region_id

    logger.info(f"Retrieved {len(results)} orders for region {region_id}.")
    return results, expires


def access_token(force_refresh: bool = False) -> str:
    """
    Retrieves an active access token, refreshing it if necessary.

    Args:
        force_refresh: If True, forces a refresh of the access token.

    Returns:
        The active access token as a string.
    """
    try:
        with AUTH_FILE.open("r", encoding="utf-8") as f:
            auth: dict[str, Any] = json.load(f)
    except FileNotFoundError:
        logger.error(f"Authentication file not found at {AUTH_FILE}.")
        raise FileNotFoundError("Authentication file is missing.")

    expires_at = auth.get("expires_at", 0)
    current_time = datetime.datetime.utcnow().timestamp()
    if not force_refresh and expires_at > current_time:
        return auth.get("access_token", "")

    logger.info("Access token expired or force refresh requested, refreshing token.")
    new_auth = get_access_token_from_refresh_token(auth["refresh_token"])

    # Update expiry time (assuming token is valid for 20 minutes)
    new_auth["expires_at"] = current_time + 1200

    with AUTH_FILE.open("w", encoding="utf-8") as f:
        json.dump(new_auth, f)

    logger.info("Access token refreshed successfully.")
    return new_auth["access_token"]
