import logging
from dataclasses import dataclass
from typing import Optional, List

from market import Order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TAX_RATE = 0.08
PROFIT_THRESHOLD = 100_000
MAX_CAPITAL = 100_000_000
SNIPE_PROFIT_THRESHOLD = 20_000_000

@dataclass
class Trade:
    from_station: int
    to_station: int
    from_order_id: int
    to_order_id: int
    item_name: str
    type_id: int
    item_cargo_volume: float
    from_price: float
    to_price: float
    quantity: int
    cargo: float
    gross_profit: float
    net_profit: Optional[float] = None

def arbitrage(orders: List[Order], cargo_space: int) -> List[Trade]:
    sell_orders = sorted(
        (order for order in orders if not order.is_buy_order),
        key=lambda x: x.price
    )
    buy_orders = sorted(
        (order for order in orders if order.is_buy_order),
        key=lambda x: x.price, reverse=True
    )

    logger.info("Initial sell orders: %d, buy orders: %d", len(sell_orders), len(buy_orders))

    sell_orders = filter_orders_for_cargo(sell_orders, cargo_space)
    buy_orders = filter_orders_for_cargo(buy_orders, cargo_space)
    logger.info("After cargo filter - sell orders: %d, buy orders: %d", len(sell_orders), len(buy_orders))

    sell_orders = filter_orders_for_capital_risk(sell_orders, MAX_CAPITAL)
    buy_orders = filter_orders_for_capital_risk(buy_orders, MAX_CAPITAL)
    logger.info("After capital risk filter - sell orders: %d, buy orders: %d", len(sell_orders), len(buy_orders))

    trades = create_trades(sell_orders, buy_orders)
    return trades

def create_trades(sell_orders: List[Order], buy_orders: List[Order]) -> List[Trade]:
    trades = []
    grouped_sell_orders = {}
    grouped_buy_orders = {}

    for order in sell_orders:
        grouped_sell_orders.setdefault(order.type_id, []).append(order)
    for order in buy_orders:
        grouped_buy_orders.setdefault(order.type_id, []).append(order)

    for type_id in grouped_sell_orders.keys() & grouped_buy_orders.keys():
        for sell_order in grouped_sell_orders[type_id]:
            for buy_order in grouped_buy_orders[type_id]:
                effective_buy_price = buy_order.price * (1 - TAX_RATE)
                if effective_buy_price < sell_order.price:
                    continue

                quantity = min(sell_order.volume_remain, buy_order.volume_remain)
                gross_profit = quantity * (effective_buy_price - sell_order.price)

                if gross_profit < PROFIT_THRESHOLD:
                    continue

                cargo_volume = quantity * sell_order.item_cargo_volume

                trade = Trade(
                    from_station=sell_order.location_id,
                    to_station=buy_order.location_id,
                    from_order_id=sell_order.order_id,
                    to_order_id=buy_order.order_id,
                    item_name=sell_order.item_name,
                    type_id=sell_order.type_id,
                    item_cargo_volume=sell_order.item_cargo_volume,
                    from_price=sell_order.price,
                    to_price=buy_order.price,
                    quantity=quantity,
                    cargo=cargo_volume,
                    gross_profit=gross_profit
                )
                trades.append(trade)
    return trades

def filter_orders_for_cargo(orders: List[Order], cargo_space: int) -> List[Order]:
    filtered_orders = []
    for order in orders:
        item_volume = order.item_cargo_volume
        if item_volume == 0:
            continue
        max_quantity = int(cargo_space // item_volume)
        volume_remain = min(order.volume_remain, max_quantity)
        if volume_remain > 0:
            order = Order(**vars(order))
            order.volume_remain = volume_remain
            filtered_orders.append(order)
    return filtered_orders

def filter_orders_for_capital_risk(orders: List[Order], max_amount: int) -> List[Order]:
    filtered_orders = []
    for order in orders:
        price = order.price
        if price == 0:
            continue
        max_quantity = int(max_amount // price)
        volume_remain = min(order.volume_remain, max_quantity)
        if volume_remain > 0:
            order = Order(**vars(order))
            order.volume_remain = volume_remain
            filtered_orders.append(order)
    return filtered_orders

def snipe(orders: List[Order], cargo_space: int, current_region: int) -> Optional[Trade]:
    trades = arbitrage(orders, cargo_space)

    order_regions = {order.order_id: order.region_id for order in orders}

    region_trades = [
        trade for trade in trades
        if order_regions.get(trade.from_order_id) == current_region
    ]

    region_trades.sort(key=lambda x: x.gross_profit, reverse=True)

    logger.info("Reviewing potential snipes for region %d: %d trades found", current_region, len(region_trades))

    if region_trades and region_trades[0].gross_profit > SNIPE_PROFIT_THRESHOLD:
        return region_trades[0]
    else:
        return None
