mod models;
mod parser;
mod graph;
pub use models::{Location, Graph};


use crate::pathfinding::parser::parse_stations;
use crate::pathfinding::graph::generate_graph;

pub fn build() {
    let stations = parse_stations().unwrap();
    let gates_connnections = parse_gate_connections().unwrap()
    let graph = generate_graph(&stations, &gates_connnections);

}
