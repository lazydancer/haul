use std::error::Error;
use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::eve_service::EveService;


#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Order {
    duration: u64,
    is_buy_order: bool,
    issued: DateTime<Utc>,
    location_id: u64,
    min_volume: u64,
    order_id: u64,
    price: f64,
    range: String,
    system_id: u64,
    type_id: u64,
    volume_remain: u64,
    volume_total: u64
}

const REGIONS: [u64; 1] = [10000033];

#[derive(Clone, Serialize)]
pub struct Orders {
    region_orders: HashMap<u64, Vec<Order>>,
    expiry_times: HashMap<u64, DateTime<Utc>>, // region_id to expiration time
}


impl Orders {
    pub fn new() -> Self {
        Orders {
            region_orders: HashMap::new(),
            expiry_times: HashMap::new(),
        }
    }

    pub fn insert(&mut self, region: u64, orders: Vec<Order>, expiry: DateTime<Utc>) {
        self.region_orders.insert(region, orders);
        self.expiry_times.insert(region, expiry);
    }

    pub fn expired_regions(&self) -> Vec<u64> {
        let current_time = Utc::now();

        println!("expiry: {:?}, time now: {:?}", &self.expiry_times, &current_time);

        let mut expired: Vec<u64> = self.expiry_times.iter()
            .filter(|&(_region_id, &expiry_time)| expiry_time < current_time)
            .map(|(&region_id, _)| region_id)
            .collect();

        for &region in REGIONS.iter() {
            if !self.expiry_times.contains_key(&region) {
                expired.push(region);
            }
        }
    

        expired

    }

    pub fn update(&mut self, updated_orders: Orders) {
        for (key, value) in updated_orders.region_orders {
            self.region_orders.insert(key, value);

            if let Some(expiry_time) = updated_orders.expiry_times.get(&key) {
                self.expiry_times.insert(key, *expiry_time);
            }
        }
    }


    pub fn orders(&self) -> Vec<Order> {
        self.region_orders.values().flat_map(|orders| orders.clone()).collect()
    }
}