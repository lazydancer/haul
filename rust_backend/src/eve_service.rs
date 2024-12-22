use crate::eve_api::EveApiClient;
use crate::pathfinding::Location;
use crate::market::Orders;

use std::error::Error;

pub struct EveService {
    client: EveApiClient,
}

impl EveService {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let eve_api_client = EveApiClient::new()?;
        Ok(EveService { client: eve_api_client, })
    }

    pub fn get_authorization_url(&self) -> String {
        self.client.get_authorization_url()
    }

    pub async fn exchange_code_for_token(&self, code: &str) -> Result<(), Box<dyn Error>> {
        self.client.exchange_code_for_token(code).await
    }

    pub async fn location(&self) -> Result<Location, Box<dyn Error>> {
        self.client.request_location().await.map_err(|e| e.into())
    }

    pub async fn updated_orders(&self, current_orders: &Orders) -> Result<Orders, Box<dyn Error>> {
        let mut region_orders = Orders::new();

        let regions = current_orders.expired_regions();

        for &region in regions.iter() {
                let (orders, expiry) = self.client.request_orders(region).await?;
                region_orders.insert(region, orders, expiry);
        }
        
        Ok(region_orders)

    }
}
