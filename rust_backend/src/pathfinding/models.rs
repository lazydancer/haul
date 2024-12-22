use serde::{Deserialize, Deserializer, Serialize};
use std::str::FromStr;
use std::collections::HashMap;


#[derive(Deserialize, Serialize, Clone)]
pub struct Location {
    pub solar_system_id: i32,
    pub station_id: Option<i32>,
    pub structure_id: Option<i32>,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct RawNode {
    pub itemID: u64,
    pub typeID: u64,
    pub groupID: u64,
    #[serde(deserialize_with = "deserialize_optional_u64")]
    pub solarSystemID: Option<u64>,
    #[serde(deserialize_with = "deserialize_optional_u64")]
    pub constellationID: Option<u64>,
    #[serde(deserialize_with = "deserialize_optional_u64")]
    pub regionID: Option<u64>,
    #[serde(deserialize_with = "deserialize_optional_u64")]
    pub orbitID: Option<u64>,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub z: Option<f64>,
    #[serde(deserialize_with = "deserialize_optional_f64")]
    pub radius: Option<f64>,
    pub itemName: Option<String>,
    #[serde(deserialize_with = "deserialize_optional_f64")]
    pub security: Option<f64>,
}


fn deserialize_optional_u64<'de, D>(deserializer: D) -> Result<Option<u64>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: Option<String> = Option::deserialize(deserializer)?;
    match s.as_deref() {
        Some("None") | Some("") => Ok(None), // Handle "None" and empty strings
        Some(str_val) => u64::from_str(str_val)
                            .map(Some)
                            .map_err(serde::de::Error::custom),
        None => Ok(None),
    }
}

fn deserialize_optional_f64<'de, D>(deserializer: D) -> Result<Option<f64>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: Option<String> = Option::deserialize(deserializer)?;
    match s.as_deref() {
        Some("None") | Some("") => Ok(None), // Handle "None" and empty strings
        Some(str_val) => str_val.parse::<f64>()
                                .map(Some)
                                .map_err(serde::de::Error::custom),
        None => Ok(None),
    }
}

#[derive(Debug)]
pub struct MapNode {
    pub item_id: u64,
    pub is_station: bool,
    pub solar_system_id: u64,
    pub region_id: u64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub name: String,
    pub security: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Connection {
    stargate_id: u64,
    destination_id: u64,
}



pub type Graph = HashMap<u64, Vec<u64>>;