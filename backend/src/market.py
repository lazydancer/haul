import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from loader import load_items
from esi.api import get_region_orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORDERS_CACHE = Path(__file__).resolve().parent.parent / "cache" / "orders_snapshot_orders.json"

REGION_IDS = [
    10000002,  # The Forge
    10000016,  # Lonetrek
    10000030,  # Heimatar
    10000033,  # The Citadel
    10000032,  # Sinq Laison
    10000042,  # Metropolis
    10000064,  # Essence
    10000037,  # Everyshore
    10000043,  # Domain
    10000036,  # Devoid
    10000052,  # Kador
    10000067,  # Genesis
    10000068,  # Verge Vendor
    10000001,  # Derelik
    10000020,  # Tash-Murkon
]

@dataclass
class Order:
    order_id: int
    region_id: int
    location_id: int
    type_id: int
    is_buy_order: bool
    price: float
    issued: datetime
    volume_remain: int
    item_name: str = ''
    item_cargo_volume: float = 1.0

class Market:
    """
    Manages market orders, including fetching, updating, and caching.
    """

    def __init__(self):
        self.orders: List[Order] = []
        self.expires_times: Dict[int, datetime] = {}

    def get_orders(self) -> List[Order]:
        """Retrieves the current list of market orders."""
        self.update_orders()
        return self.orders

    def update_orders(self) -> List[int]:
        """
        Updates market orders by fetching new data for expired regions.

        Returns:
            A list of region IDs that were updated.
        """
        updated_orders: List[Order] = []
        regions_updated: List[int] = []

        for region_id in REGION_IDS:
            if self.check_expired(region_id):
                logger.info(f"Downloading orders for region {region_id}")
                orders = self.download_orders(region_id)
                updated_orders.extend(orders)
                regions_updated.append(region_id)
            else:
                # Include existing orders for this region
                updated_orders.extend(
                    [order for order in self.orders if order.region_id == region_id]
                )

        self.orders = updated_orders
        return regions_updated

    def check_expired(self, region_id: int) -> bool:
        """
        Checks if the cached orders for a region have expired.

        Args:
            region_id: The ID of the region to check.

        Returns:
            True if the orders have expired or are not cached, False otherwise.
        """
        current_time = datetime.utcnow()
        expiry_time = self.expires_times.get(region_id)
        return expiry_time is None or current_time >= expiry_time

    def download_orders(self, region_id: int) -> List[Order]:
        """
        Downloads orders for a given region and updates the expiry time.

        Args:
            region_id: The ID of the region to download orders for.

        Returns:
            A list of Order instances for the region.
        """
        raw_orders, expiry = get_region_orders(region_id)
        expiry_time = datetime.strptime(expiry, "%a, %d %b %Y %H:%M:%S %Z")
        self.expires_times[region_id] = expiry_time

        orders = self.add_item_info_to_orders(raw_orders)
        return orders

    def add_item_info_to_orders(self, raw_orders: List[Dict]) -> List[Order]:
        """
        Enhances raw order data with item information and converts them into Order instances.

        Args:
            raw_orders: A list of raw order dictionaries from the API.

        Returns:
            A list of Order instances with additional item information.
        """
        items = load_items()
        orders: List[Order] = []

        for raw_order in raw_orders:
            item_info = items.get(raw_order['type_id'], {})
            order = Order(
                order_id=raw_order['order_id'],
                region_id=raw_order['region_id'],
                location_id=raw_order['location_id'],
                type_id=raw_order['type_id'],
                is_buy_order=raw_order['is_buy_order'],
                price=raw_order['price'],
                issued=datetime.strptime(raw_order['issued'], "%Y-%m-%dT%H:%M:%S%z"),
                volume_remain=raw_order['volume_remain'],
                item_name=item_info.get('type_name', f"Not found: {raw_order['type_id']}"),
                item_cargo_volume=item_info.get('volume', 1.0),
            )
            orders.append(order)

        return orders

    def cache_orders(self) -> None:
        """Caches the current list of orders to a JSON file."""
        try:
            with ORDERS_CACHE.open("w", encoding="utf-8") as f:
                # Serialize orders to dictionaries and handle datetime serialization
                orders_data = [self._serialize_order(order) for order in self.orders]
                json.dump(orders_data, f, ensure_ascii=False, indent=4)
            logger.info("Orders cached successfully.")
        except IOError as e:
            logger.error(f"Error caching orders: {e}")

    def load_orders(self) -> List[Order]:
        """
        Loads orders from the cache file.

        Returns:
            A list of Order instances loaded from the cache.
        """
        try:
            with ORDERS_CACHE.open("r", encoding="utf-8") as f:
                orders_data = json.load(f)
                self.orders = [self._deserialize_order(data) for data in orders_data]
            logger.info("Orders loaded from cache successfully.")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading orders from cache: {e}")
            self.orders = []

        return self.orders

    def _serialize_order(self, order: Order) -> Dict:
        """
        Serializes an Order instance to a dictionary suitable for JSON serialization.

        Args:
            order: The Order instance to serialize.

        Returns:
            A dictionary representation of the Order.
        """
        order_dict = asdict(order)
        # Convert datetime objects to ISO format strings
        order_dict['issued'] = order.issued.isoformat()
        return order_dict

    def _deserialize_order(self, data: Dict) -> Order:
        """
        Deserializes a dictionary into an Order instance.

        Args:
            data: The dictionary representation of an Order.

        Returns:
            An Order instance.
        """
        data['issued'] = datetime.fromisoformat(data['issued'])
        return Order(**data)
