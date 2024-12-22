import logging
import os
import pickle
import networkx as nx
from math import sqrt, log
from pathlib import Path
from typing import Any, Optional

from loader import load_map_data, load_star_gate_connections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PATHS_FILE = Path(__file__).resolve().parent.parent / 'cache' / 'path_cache.pkl'


class NavigationGraph:
    """
    Represents the navigation graph for stations and solar systems,
    allowing computation of shortest paths based on time and risk.
    """

    def __init__(self, ship: dict[str, Any]):
        """
        Initializes the NavigationGraph.

        Args:
            ship: A dictionary containing ship parameters like
                  max warp speed, max subwarp speed, etc.
        """
        self.graph = nx.Graph()
        self.stations, self.solar_systems = load_map_data()
        self._add_intra_system_connections()
        self._load_star_gate_connections()
        self._add_time_and_risk(ship)
        self.paths = self._load_paths()

    def shortest_path(self, source: int, target: int) -> Optional[list[int]]:
        """
        Returns the shortest path between two stations.

        Args:
            source: The starting station ID.
            target: The target station ID.

        Returns:
            A list of station IDs representing the shortest path,
            or None if no path exists.
        """
        try:
            path = nx.shortest_path(self.graph, source, target, weight="weight")
            return path
        except nx.NetworkXNoPath:
            logger.warning(f"No path found between {source} and {target}")
            return None

    def shortest_path_length(self, source: int, target: int) -> Optional[float]:
        """
        Returns the length of the shortest path between two stations.

        Args:
            source: The starting station ID.
            target: The target station ID.

        Returns:
            The length of the shortest path, or None if no path exists.
        """
        try:
            return self.paths[source][target]
        except KeyError:
            logger.warning(f"No path length found between {source} and {target}")
            return None

    def formatted_route(self, path: list[int]) -> list[dict[str, Any]]:
        """
        Formats the route for the ESI API and frontend.

        Args:
            path: A list of station IDs representing the path.

        Returns:
            A list of dictionaries containing location information.
        """
        combined_path = self._combine_warp_gates(path)
        formatted_route = []

        for index, location_id in enumerate(combined_path):
            location_info = self._get_location_info(location_id, index)
            if location_info is not None:
                formatted_route.append(location_info)

        return formatted_route

    def _get_location_info(self, location_id: int, index: int) -> Optional[dict[str, Any]]:
        """
        Retrieves location information for a given ID.

        Args:
            location_id: The ID of the location (station or system).
            index: The position in the route.

        Returns:
            A dictionary with location details, or None if not found.
        """
        if location_id in self.stations:
            station_data = self.stations[location_id]
            solar_system = self.solar_systems.get(station_data['solar_system_id'], {})
            return {
                "id": index,
                "location_id": location_id,
                "station_id": location_id,
                "solar_system_id": station_data['solar_system_id'],
                "location_type": "station",
                "location": f"{station_data['region_name']} - {solar_system.get('item_name', '')} - {station_data['item_name']}",
                "actions": [],
            }
        elif location_id in self.solar_systems:
            solar_system_data = self.solar_systems[location_id]
            return {
                "id": index,
                "location_id": location_id,
                "solar_system_id": location_id,
                "location_type": "system",
                "location": f"{solar_system_data['region_name']} - {solar_system_data['item_name']}",
                "actions": [],
            }
        else:
            logger.warning(f"Location ID {location_id} not found in stations or solar systems")
            return None

    def _combine_warp_gates(self, path: list[int]) -> list[int]:
        """
        Combines warp gates in the path to reduce redundant entries.

        Args:
            path: A list of station IDs.

        Returns:
            A list of location IDs with combined warp gates.
        """
        combined_path = []

        for i, (current_id, next_id) in enumerate(zip(path, path[1:])):
            current_station = self.stations.get(current_id)
            next_station = self.stations.get(next_id)

            if current_station and current_station['is_station']:
                combined_path.append(current_id)
            elif (current_station and next_station and
                  not current_station['is_station'] and
                  not next_station['is_station'] and
                  current_station['solar_system_id'] == next_station['solar_system_id']):
                combined_path.append(current_station['solar_system_id'])

        last_station = self.stations.get(path[-1])
        if last_station and last_station['is_station']:
            combined_path.append(path[-1])

        return combined_path

    def _add_intra_system_connections(self) -> None:
        """
        Adds connections between stations within the same solar system.
        """
        stations_by_system: dict[int, list[int]] = {}
        for station_id, station_data in self.stations.items():
            system_id = station_data['solar_system_id']
            stations_by_system.setdefault(system_id, []).append(station_id)

        for system_stations in stations_by_system.values():
            for i in range(len(system_stations)):
                for j in range(i + 1, len(system_stations)):
                    self.graph.add_edge(system_stations[i], system_stations[j])

    def _load_star_gate_connections(self) -> None:
        """
        Loads stargate connections into the graph.
        """
        connections = load_star_gate_connections()
        for from_station, to_station in connections:
            if from_station in self.stations and to_station in self.stations:
                self.graph.add_edge(from_station, to_station)

    def _add_time_and_risk(self, ship: dict[str, Any]) -> None:
        """
        Calculates and adds time and risk attributes to graph edges.

        Args:
            ship: A dictionary containing ship parameters.
        """
        for u, v in self.graph.edges():
            time = self._calculate_time(u, v, ship)
            risk = self._calculate_risk(v, ship.get("gankers_areas", {}))
            weight = time * ship.get("player_cost", 1) + ship.get("risk_cost", 1) * risk
            self.graph[u][v]['time'] = time
            self.graph[u][v]['risk'] = risk
            self.graph[u][v]['weight'] = weight

    def _calculate_time(self, from_station: int, to_station: int, ship: dict[str, Any]) -> float:
        """
        Calculates the time to travel between two stations.

        Args:
            from_station: The starting station ID.
            to_station: The destination station ID.
            ship: A dictionary containing ship parameters.

        Returns:
            The time in seconds to travel between the two stations.
        """
        max_warp_speed = ship.get("max_warp_speed", 1)
        max_subwarp_speed = ship.get("max_subwarp_speed", 1)

        # Inter-system travel (using stargates)
        if self.stations[from_station]['solar_system_id'] != self.stations[to_station]['solar_system_id']:
            return 9.0  # Fixed time for stargate jumps

        # Intra-system travel
        position_from = self.stations[from_station]['position']
        position_to = self.stations[to_station]['position']
        warp_dist = sqrt(sum((position_from[i] - position_to[i]) ** 2 for i in range(3)))

        time_in_warp = self._calculate_time_in_warp(warp_dist, max_warp_speed, max_subwarp_speed)
        time_in_warp += 2.0  # Add 2 seconds for initial delay

        return time_in_warp

    def _calculate_time_in_warp(self, warp_dist: float, max_warp_speed: float, max_subwarp_speed: float) -> float:
        """
        Calculates the time spent in warp between two points.

        Args:
            warp_dist: The distance to warp in meters.
            max_warp_speed: The maximum warp speed of the ship in AU/s.
            max_subwarp_speed: The maximum sub-warp speed of the ship in m/s.

        Returns:
            The time in seconds spent in warp.
        """
        AU_IN_M = 149_597_870_700  # Astronomical Unit in meters

        k_accel = max_warp_speed
        k_decel = min(max_warp_speed / 3, 2)
        warp_dropout_speed = min(max_subwarp_speed / 2, 100)
        max_ms_warp_speed = max_warp_speed * AU_IN_M

        accel_dist = AU_IN_M
        decel_dist = max_ms_warp_speed / k_decel
        minimum_dist = accel_dist + decel_dist

        cruise_time = 0.0
        if minimum_dist > warp_dist:
            max_ms_warp_speed = warp_dist * k_accel * k_decel / (k_accel + k_decel)
        else:
            cruise_time = (warp_dist - minimum_dist) / max_ms_warp_speed

        accel_time = log(max_ms_warp_speed / k_accel) / k_accel
        decel_time = log(max_ms_warp_speed / warp_dropout_speed) / k_decel

        total_time = cruise_time + accel_time + decel_time
        return total_time

    def _calculate_risk(self, to_station: int, gankers_areas: dict[str, float]) -> float:
        """
        Calculates the risk of traveling to a station.

        Args:
            to_station: The destination station ID.
            gankers_areas: A dictionary mapping solar system names to risk factors.

        Returns:
            A risk score as a float.
        """
        station_data = self.stations[to_station]
        security = station_data.get('security', 1.0)
        solar_system_name = station_data.get('solar_system_name', '')

        # Base risk calculation based on security status
        risk = 0.00004 + (1 - security) * 0.0004
        if security < 0.5:
            risk += 0.005
        if security < 0.1:
            risk += 0.5

        risk += gankers_areas.get(solar_system_name, 0)

        return risk

    def _load_paths(self) -> dict[int, dict[int, float]]:
        """
        Loads or generates the shortest path lengths between all pairs.

        Returns:
            A dictionary of dictionaries containing path lengths.
        """
        if PATHS_FILE.exists():
            with PATHS_FILE.open("rb") as f:
                logger.info("Loading cached paths from file")
                return pickle.load(f)
        else:
            logger.info("Generating path lengths and caching to file")
            dist = dict(nx.all_pairs_dijkstra_path_length(self.graph))
            with PATHS_FILE.open("wb") as f:
                pickle.dump(dist, f)
            return dist
