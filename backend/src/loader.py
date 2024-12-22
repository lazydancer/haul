import csv
import logging
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent / 'data'
MAP_DENORMALIZED_FILE = BASE_DIR / 'mapDenormalize.csv'
MAP_JUMPS_FILE = BASE_DIR / 'mapJumps.csv'
INV_TYPES_FILE = BASE_DIR / 'invTypes.csv'
REGION_IDS_FILE = BASE_DIR / 'mapRegions.csv'

# Define constants
TYPE_ID_SOLAR_SYSTEM = 5
GROUP_ID_STATION = 15
GROUP_ID_STARGATE = 10

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

def load_map_data() -> tuple[dict[int, Any], dict[int, Any]]:
    """
    Loads map data including stations and solar systems.

    Returns:
        Tuple containing dictionaries of stations and solar systems.
    """
    regions = read_regions()
    stations: dict[int, Any] = {}
    solar_systems: dict[int, Any] = {}

    with MAP_DENORMALIZED_FILE.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            process_row(row, solar_systems, stations, regions)

    # Update station data with additional solar system and region info
    for station_id, station_data in stations.items():
        ss_id = station_data['solar_system_id']
        solar_system = solar_systems.get(ss_id)
        if solar_system:
            station_data['solar_system_name'] = solar_system['item_name']
            station_data['solar_system_position'] = solar_system['position']
            station_data['region_id'] = solar_system['region_id']
            station_data['region_name'] = regions.get(station_data['region_id'], 'Unknown')

    return stations, solar_systems

def process_row(
    row: list[str],
    solar_systems: dict[int, Any],
    stations: dict[int, Any],
    regions: dict[int, str]
) -> None:
    """
    Processes a single row from the map denormalized CSV file.

    Args:
        row: A list of CSV fields.
        solar_systems: Dictionary to store solar system data.
        stations: Dictionary to store station data.
        regions: Dictionary of region IDs to region names.
    """
    (
        item_id, type_id, group_id, solar_system_id,
        _, region_id, _, x, y, z, _,
        item_name, security, _, _
    ) = row

    try:
        region_id_int = int(region_id)
    except (ValueError, TypeError):
        return

    if region_id_int not in REGION_IDS:
        return

    item_id_int = int(item_id)
    type_id_int = int(type_id)
    group_id_int = int(group_id)
    solar_system_id_int = int(solar_system_id)

    if type_id_int == TYPE_ID_SOLAR_SYSTEM:
        solar_systems[item_id_int] = {
            'item_name': item_name,
            'position': (float(x), float(y), float(z)),
            'region_id': region_id_int,
            'region_name': regions.get(region_id_int, 'Unknown')
        }
    elif group_id_int in (GROUP_ID_STATION, GROUP_ID_STARGATE):
        stations[item_id_int] = {
            'is_station': group_id_int == GROUP_ID_STATION,
            'item_name': item_name,
            'security': float(security),
            'position': (float(x), float(y), float(z)),
            'solar_system_id': solar_system_id_int,
            'region_id': region_id_int,
            'jumps': []
        }

def load_items() -> dict[int, Any]:
    """
    Loads item data from the inventory types CSV file.

    Returns:
        Dictionary of items with type IDs as keys.
    """
    items: dict[int, Any] = {}
    with INV_TYPES_FILE.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                type_id = int(row['typeID'])
                items[type_id] = {
                    'type_id': type_id,
                    'group_id': int(row['groupID']),
                    'type_name': row['typeName'],
                    'description': row['description'],
                    'mass': float(row['mass']) if row['mass'] else None,
                    'volume': float(row['volume']) if row['volume'] else None,
                    'capacity': float(row['capacity']) if row['capacity'] else None,
                }
            except ValueError as e:
                logger.warning(f"Could not parse item with typeID {row.get('typeID')}: {e}")
            except KeyError as e:
                logger.error(f"Missing expected field in inventory types CSV: {e}")
    return items

def read_regions() -> dict[int, str]:
    """
    Reads region data from the regions CSV file.

    Returns:
        Dictionary mapping region IDs to region names.
    """
    regions: dict[int, str] = {}
    with REGION_IDS_FILE.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                region_id = int(row['regionID'])
                regions[region_id] = row['regionName'].strip()
            except ValueError as e:
                logger.warning(f"Could not parse region ID: {e}")
            except KeyError as e:
                logger.error(f"Missing expected field in regions CSV: {e}")
    return regions

def load_star_gate_connections() -> list[tuple[int, int]]:
    """
    Loads stargate connections from the map jumps CSV file.

    Returns:
        List of tuples representing stargate connections.
    """
    star_gate_connections: list[tuple[int, int]] = []
    with MAP_JUMPS_FILE.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                from_stargate = int(row['stargateID'])
                to_stargate = int(row['destinationID'])
                star_gate_connections.append((from_stargate, to_stargate))
            except ValueError as e:
                logger.warning(f"Could not parse stargate connection: {e}")
            except KeyError as e:
                logger.error(f"Missing expected field in stargate jumps CSV: {e}")
    return star_gate_connections
