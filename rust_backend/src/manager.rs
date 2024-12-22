use std::sync::Mutex;
use tokio::sync::watch;

use std::error::Error;

use crate::eve_service::EveService;
use crate::pathfinding::{Location, build};
use crate::market::{Order, Orders};

pub struct Manager {
    // route_state: Mutex<Route>
    // route_info_state: Mutex<RouteInfo>
    orders_state: Mutex<Orders>,
    location: Mutex<Option<Location>>,
    // log_state: Mutex<Log>
    eve_service: EveService,
    
}

impl Manager {
    pub fn new() -> Manager {

        build();

        Manager {
            location: Mutex::new( None ),
            eve_service: EveService::new().expect("Manager to generate EveService"),
            orders_state: Mutex::new( Orders::new() ),
        }

    }

    pub async fn run(&self, shutdown_signal: watch::Receiver<bool>) {
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
            if *shutdown_signal.borrow() {
                println!("Manager task is shutting down.");
                break;
            }
    
            match self.eve_service.location().await {
                Ok(result) => {
                    match self.location.lock() {
                        Ok(mut location) => *location = Some(result),
                        Err(e) => eprintln!("Error locking location mutex: {}", e),
                    }
                }
                Err(e) => {
                    eprintln!("Error fetching location {}", e);
                }
            }

            
            let orders_clone = match self.orders_state.lock() {
                Ok(orders_lock) => orders_lock.clone(),
                Err(e) => {
                    eprintln!("Error locking orders_state mutex: {}", e);
                    continue;
                }
            };
    
            match self.eve_service.updated_orders(&orders_clone).await {
                Ok(updated_orders) => {
                    match self.orders_state.lock() {
                        Ok(mut orders_state) => orders_state.update(updated_orders),
                        Err(e) => eprintln!("Error locking orders_state mutex: {}", e),
                    }
                }
                Err(e) => eprintln!("Error updating orders: {}", e),
            }
        }
    }
    pub fn get_authorization_url(&self) -> String {
        self.eve_service.get_authorization_url()
    }

    pub async fn exchange_code_for_token(&self, code: &str) -> Result<(), Box<dyn Error>> {
        self.eve_service.exchange_code_for_token(code).await
    }

    pub fn location(&self) -> Option<Location> {
        let location = self.location.lock().unwrap();
        location.clone()
    }

    pub fn orders(&self) -> Vec<Order> {
        let orders = self.orders_state.lock().unwrap();
        orders.orders()
    }
}