use std::error::Error;
use std::fs::File;
use csv;

use crate::pathfinding::models::{RawNode, MapNode};

pub fn parse_stations() -> Result<Vec<MapNode>, Box<dyn Error>> {
    let file_path = "../mapDenormalize.csv";
    let file = File::open(file_path)?;

    let mut rdr = csv::Reader::from_reader(file);

    let mut raw_nodes: Vec<RawNode> = Vec::new();
    for result in rdr.deserialize() {
        match result {
            Ok(node) => raw_nodes.push(node),
            Err(e) => println!("Error deserializing record: {}", e),
        }
    }

    println!("raw nodes: {:?}", raw_nodes.len());

    let processed_nodes: Vec<MapNode> = raw_nodes.into_iter()
        .filter(|node| [15, 10].contains(&node.groupID))
        .map(|node| MapNode {
            item_id: node.itemID,
            is_station: node.groupID == 15,
            solar_system_id: node.solarSystemID.unwrap_or_default(),
            region_id: node.regionID.unwrap_or_default(),
            x: node.x.unwrap_or_default(),
            y: node.y.unwrap_or_default(),
            z: node.z.unwrap_or_default(),
            name: node.itemName.unwrap_or_default(),
            security: node.security.unwrap_or_default(),
        })
        .collect();

    println!("processed nodes: {:?}", processed_nodes.len());


    Ok(processed_nodes)
}

pub fn parse_gate_connections() -> Result<Vec<u64, u64>, Box<dyn Error>> {
    unimplemented!();
}