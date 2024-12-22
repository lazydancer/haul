import logging
from dataclasses import dataclass, field
from typing import Optional

from tqdm import tqdm

from graph import Graph
from pathfinder import Ship
from arbitrage import Trade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_TRADES_TO_CONSIDER = 20_000
MAX_CAPITAL = 100_000_000

@dataclass
class RouteStep:
    location_id: int
    station_name: str
    actions: list[dict] = field(default_factory=list)

Route = list[RouteStep]

def route(trades: list[Trade], graph: Graph, ship: Ship) -> tuple[Optional[Route], Optional[dict]]:
    """
    Given a list of trades, find the best route starting from the ship's location.

    Args:
        trades: List of Trade instances.
        graph: Navigation graph.
        ship: Ship parameters.

    Returns:
        A tuple containing the best route and route information.
    """
    trades.sort(
        key=lambda trade: trade.gross_profit / (trade.from_price * trade.quantity) if trade.from_price * trade.quantity > 0 else 0,
        reverse=True
    )

    best_profit_rate = 0.0
    best_route: Optional[Route] = None
    best_route_info: Optional[dict] = None

    seen_routes = set()

    for trade in tqdm(trades[:MAX_TRADES_TO_CONSIDER], desc="Evaluating trades"):
        route_stations = (ship.location, trade.from_station, trade.to_station)

        if route_stations in seen_routes:
            continue
        seen_routes.add(route_stations)

        optimized_trades = select_trades(list(route_stations), trades, ship)
        total_profit = sum(t.gross_profit for t in optimized_trades)

        if not optimized_trades or total_profit <= 0:
            continue

        try:
            path = graph.shortest_path(ship.location, trade.from_station)[:-1]
            path += graph.shortest_path(trade.from_station, trade.to_station)
        except Exception as e:
            logger.error(f"Error finding path: {e}")
            continue

        risk = sum(graph.graph[u][v]['risk'] for u, v in zip(path, path[1:]))
        transport_time = sum(graph.graph[u][v]['time'] for u, v in zip(path, path[1:]))

        capital = getattr(ship, 'ship_cost', 0.0) + sum(t.from_price * t.quantity for t in optimized_trades)

        if transport_time == 0:
            logger.warning("Transport time is zero, skipping this route to avoid division by zero.")
            continue

        net_profit = total_profit - risk * capital
        profit_rate = net_profit / transport_time

        if profit_rate > best_profit_rate:
            logger.info(
                f"New best profit rate: {profit_rate * 3600:.2f} per hour, "
                f"Risk: {risk:.4f}, Capital: {capital:.2f}, "
                f"Transport time: {transport_time:.2f} sec, Gross profit: {total_profit:.2f}"
            )
            formatted_route = graph.formatted_route(path)
            final_route = set_actions(formatted_route, optimized_trades)
            best_route = final_route
            best_route_info = {
                "profit_rate": profit_rate,
                "risk": risk,
                "capital": capital,
                "transport_time": transport_time,
                "gross_profit": total_profit,
                "net_profit": net_profit,
            }
            best_profit_rate = profit_rate

    return best_route, best_route_info

def select_trades(stations: list[int], trades: list[Trade], ship: Ship) -> list[Trade]:
    """
    Given a list of stations, find the optimal trades to add.

    Args:
        stations: List of station IDs.
        trades: List of Trade instances.
        ship: Ship parameters.

    Returns:
        A list of optimized Trade instances.
    """
    filtered_trades = [
        trade for trade in trades
        if trade.from_station in stations and trade.to_station in stations and
           stations.index(trade.from_station) < stations.index(trade.to_station)
    ]

    filtered_trades.sort(
        key=lambda trade: trade.gross_profit / trade.cargo if trade.cargo > 0 else 0,
        reverse=True
    )

    used_orders = {}
    optimized_trades = []
    cargo = 0.0
    capital = 0.0

    for trade in filtered_trades:
        quantity = trade.quantity
        from_order, to_order = trade.from_order_id, trade.to_order_id

        from_remaining = used_orders.get(from_order, quantity)
        to_remaining = used_orders.get(to_order, quantity)

        max_quantity_by_cargo = int((ship.cargo - cargo) // trade.item_cargo_volume)
        max_quantity_by_capital = int((MAX_CAPITAL - capital) // trade.from_price)

        max_quantity = min(quantity, from_remaining, to_remaining, max_quantity_by_cargo, max_quantity_by_capital)

        if max_quantity <= 0:
            continue

        cargo += trade.item_cargo_volume * max_quantity
        capital += trade.from_price * max_quantity
        used_orders[from_order] = from_remaining - max_quantity
        used_orders[to_order] = to_remaining - max_quantity

        # Create a new Trade instance with updated quantities
        updated_trade = Trade(
            from_station=trade.from_station,
            to_station=trade.to_station,
            from_order_id=trade.from_order_id,
            to_order_id=trade.to_order_id,
            item_name=trade.item_name,
            type_id=trade.type_id,
            item_cargo_volume=trade.item_cargo_volume,
            from_price=trade.from_price,
            to_price=trade.to_price,
            quantity=max_quantity,
            cargo=trade.item_cargo_volume * max_quantity,
            gross_profit=(trade.to_price - trade.from_price) * max_quantity,
            net_profit=None  # Will be calculated later if needed
        )

        optimized_trades.append(updated_trade)

        if cargo >= ship.cargo or capital >= MAX_CAPITAL:
            break

    return optimized_trades

def set_actions(route: Route, trades: list[Trade]) -> Route:
    """
    Sets the actions (buy/sell) at each step in the route based on the trades.

    Args:
        route: The route steps.
        trades: List of Trade instances.

    Returns:
        The route with actions set.
    """
    bought_items = set()
    for trade in trades:
        for step in route:
            if trade.from_station == step.location_id:
                step.actions.append({
                    "action_type": "buy",
                    "item": trade.item_name,
                    "type_id": trade.type_id,
                    "quantity": trade.quantity,
                    "price": trade.from_price,
                })
                bought_items.add(trade.type_id)
            if trade.to_station == step.location_id and trade.type_id in bought_items:
                step.actions.append({
                    "action_type": "sell",
                    "item": trade.item_name,
                    "type_id": trade.type_id,
                    "quantity": trade.quantity,
                    "price": trade.to_price,
                })

    for step in route:
        step.actions.sort(key=lambda action: (action["action_type"], action["item"], action["price"]))

    return route
