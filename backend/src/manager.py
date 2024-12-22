import threading

from graph import Graph
from esi.api import get_location, set_waypoints, open_market_window
from market import Market
from arbitrage import arbitrage, snipe
from pathfinder import pathfinder
import route



class Manager:
    
    def __init__(self):
        self.ship = {
            "location": get_location(),
            "cargo": 600,
            "max_warp_speed": 8.22, # AU/s
            "max_subwarp_speed": 216.5, # m/s
            "gankers_areas": {"Ahbazon": 0.5}, #["Miroitem", "Rancer", "Huola", "Ahbazon", "Uedama", "Sivala", "Tama", "Onatoh"],
            "player_cost": 15_000_000 / 3600,  # isk/second
            "risk_cost": 60_000_000, # isk
            "ship_cost": 50_000_000 # isk
        }
        self.graph = Graph(self.ship)
        self.route = []
        self.route_info = {}
        self.market = Market()
        self.updating_orders = False
        self.log = ["Test Log"]

    def route(self):
        return self.route
    
    def route_info(self):
        return self.route_info
    
    def get_log(self):
        result = self.log
        self.log = []
        return result

    def snipe_callback(self, updated_regions):

        if self.ship["location"] in self.graph.solar_systems:
            current_region = self.graph.solar_systems[self.ship["location"]]["region_id"]
        else:
            current_region = self.graph.stations[self.ship["location"]]["region_id"]

        if current_region in updated_regions:
            potential_snipe = snipe(self.market.orders, self.ship["cargo"], current_region)
            if potential_snipe:
                self.log.append("----------------")
                self.log.append("Snipe: " + str(potential_snipe[1]) + " orders for " + str(potential_snipe[0]) + " ISK")
                self.log.append("----------------")

                print("snipe possible", potential_snipe[0], "ISK", potential_snipe[1])

                open_market_window(potential_snipe[1]["type_id"])
                

    def update(self):
        self.log = self.log[-100:]

        location = get_location()
        self.ship["location"] = location

        if len(self.route) == 1:
            # Only the last step is left, so we are at the destination
            self.log.append("Arrived at Destination")
            self.route = []
            return

        for i, step in enumerate(self.route[:2]):
            if i != 0 and step["location_id"] == location:
                self.log.append("Arrived at " + step["location"])
                self.route = self.route[i:]
                break

        if not self.updating_orders:
            self.updating_orders = True

            def target_function(log):
                try:
                    updated_regions = self.market.update_orders(log)
                    if updated_regions:
                        self.snipe_callback(updated_regions)
                finally:
                    self.updating_orders = False

            update_thread = threading.Thread(target=target_function, args=(self.log,))
            update_thread.start()


    def create_route(self):
        order_matches = arbitrage(self.market.orders, self.ship["cargo"])
        order_matches = pathfinder(order_matches, self.graph, self.ship)
        self.route, self.route_info = route.route(order_matches, self.graph, self.ship)

        set_waypoints([r["location_id"] for r in self.route[1:]])

        print(self.route)
         
    