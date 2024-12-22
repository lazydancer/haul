import logging
from dataclasses import dataclass
from tqdm import tqdm

from arbitrage import Trade
from graph import Graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Ship:
    location: int
    cargo: int
    max_warp_speed: float
    max_subwarp_speed: float
    gankers_areas: list[str]
    player_cost: float
    risk_cost: float


def pathfinder(order_matches: list[Trade], graph: Graph, ship: Ship) -> list[Trade]:
    """
    Processes order matches by filtering and calculating net profit.

    Args:
        order_matches: List of trade opportunities.
        graph: Navigation graph.
        ship: Ship parameters.

    Returns:
        A list of filtered and annotated trade opportunities.
    """
    order_matches = filter_order_matches_not_in_graph(order_matches, graph)
    logger.info("After filtering order matches not in graph: %d", len(order_matches))
          
    order_matches = filter_order_matches_same_region(order_matches, graph)
    logger.info("After filtering order matches to same region: %d", len(order_matches))

    order_matches = calculate_net_profit(order_matches, graph, ship)

    order_matches = filter_order_matches_low_profit(order_matches)
    logger.info("After filtering low profit order matches: %d", len(order_matches))

    return order_matches

def filter_order_matches_not_in_graph(order_matches: list[Trade], graph: Graph) -> list[Trade]:
    """
    Filters out order matches where either the from_station or to_station is not in the graph.

    Args:
        order_matches: List of trade opportunities.
        graph: Navigation graph.

    Returns:
        Filtered list of trade opportunities.
    """
    return [
        order_match for order_match in order_matches
        if order_match.from_station in graph.graph.nodes and order_match.to_station in graph.graph.nodes
    ]

def filter_order_matches_same_region(order_matches: list[Trade], graph: Graph) -> list[Trade]:
    """
    Filters out order matches where the from_region and to_region are different.
    Keeps only order matches within the same region.

    Args:
        order_matches: List of trade opportunities.
        graph: Navigation graph.

    Returns:
        Filtered list of trade opportunities where both stations are in the same region.
    """
    filtered_order_matches = []

    for order_match in order_matches:
        from_station = order_match.from_station
        to_station = order_match.to_station

        from_station_data = graph.stations.get(from_station)
        to_station_data = graph.stations.get(to_station)

        if not from_station_data or not to_station_data:
            continue  # Skip if station data is missing

        from_solar_system_id = from_station_data["solar_system_id"]
        to_solar_system_id = to_station_data["solar_system_id"]

        from_region = graph.solar_systems[from_solar_system_id]["region_id"]
        to_region = graph.solar_systems[to_solar_system_id]["region_id"]

        if from_region == to_region:
            filtered_order_matches.append(order_match)

    return filtered_order_matches

def calculate_net_profit(order_matches: list[Trade], graph: Graph, ship: Ship) -> list[Trade]:
    """
    Calculates the net profit for each order match by subtracting transport cost from gross profit.

    Args:
        order_matches: List of trade opportunities.
        graph: Navigation graph.
        ship: Ship parameters.

    Returns:
        List of trade opportunities with net_profit calculated.
    """
    logger.info("Calculating estimated profits")
    for order_match in tqdm(order_matches):
        try:
            # Calculate transport cost from ship location to from_station
            cost_to_source = graph.shortest_path_length(ship.location, order_match.from_station)
            # Calculate transport cost from from_station to to_station
            cost_to_destination = graph.shortest_path_length(order_match.from_station, order_match.to_station)

            # Check if paths exist
            if cost_to_source is None or cost_to_destination is None:
                logger.warning(f"No path found for order match: {order_match}")
                order_match.net_profit = None
                continue

            total_transport_cost = cost_to_source + cost_to_destination
            order_match.net_profit = order_match.gross_profit - total_transport_cost
        except Exception as e:
            logger.error(f"Error calculating net profit for order match {order_match}: {e}")
            order_match.net_profit = None

    return order_matches

def filter_order_matches_low_profit(order_matches: list[Trade]) -> list[Trade]:
    """
    Filters out order matches with non-positive net profit.

    Args:
        order_matches: List of trade opportunities with net_profit calculated.

    Returns:
        Filtered list of profitable trade opportunities.
    """
    return [
        order_match for order_match in order_matches
        if order_match.net_profit and order_match.net_profit > 0
    ]
