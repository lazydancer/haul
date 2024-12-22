use dotenv::dotenv;
use std::env;
use std::error::Error;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH, Duration};
use std::sync::Arc;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tokio::{task, time};
use tokio::sync::Semaphore;


use crate::pathfinding::Location;
use crate::market::Order;

const TOKEN_FILE: &str = "token.json"; 

use std::sync::Mutex;


#[derive(Deserialize, Serialize, Clone)]
struct TokenData {
    access_token: String,
    refresh_token: String,
    expires_at: u64,
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: String,
    refresh_token: String,
    expires_in: u64, 
}

pub struct EveApiClient {
    client_id: String,
    client_secret: String,
    character_id: String,
    redirect_url: String,
    access_token: Mutex<Option<String>>,
    expires_at: Mutex<Option<u64>>,
}


impl EveApiClient {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        dotenv().ok();

        let client_id = env::var("CLIENT_ID").map_err(|e| format!("CLIENT_ID error: {}", e))?;
        let client_secret = env::var("CLIENT_SECRET").map_err(|e| format!("CLIENT_SECRET error: {}", e))?;
        let character_id = env::var("CHARACTER_ID").map_err(|e| format!("CHARACTER_ID error: {}", e))?;
        let redirect_url = env::var("REDIRECT_URL").map_err(|e| format!("REDIRECT_URL error: {}", e))?;

        let token_data = match Self::load_token_from_file() {
            Ok(data) => Some(data),
            Err(_) => None,
        };

        Ok(EveApiClient {
            client_id,
            client_secret,
            character_id,
            redirect_url,
            access_token: Mutex::new(token_data.clone().map(|data| data.access_token)),
            expires_at: Mutex::new(token_data.map(|data| data.expires_at)),
        })
    }

    pub fn get_authorization_url(&self) -> String {
        let auth_url = format!(
            "https://login.eveonline.com/v2/oauth/authorize/?response_type=code&client_id={}&redirect_uri={}&scope={}",
            self.client_id,
            self.redirect_url,
            "esi-assets.read_assets.v1 esi-location.read_location.v1 esi-location.read_online.v1 esi-ui.open_window.v1 esi-ui.write_waypoint.v1".replace(" ", "%20")
        );
        auth_url
    }

    pub async fn exchange_code_for_token(&self, code: &str) -> Result<(), Box<dyn Error>> {
        let client = reqwest::Client::new();
        let res = client
            .post("https://login.eveonline.com/v2/oauth/token")
            .form(&[
                ("client_id", self.client_id.as_str()),
                ("client_secret", self.client_secret.as_str()),
                ("code", code),
                ("redirect_uri", self.redirect_url.as_str()),
                ("grant_type", "authorization_code"),
            ])
            .send()
            .await;
    
        let res = match res {
            Ok(response) => response,
            Err(e) => return Err(Box::new(e)),
        };
    
        let token_response: TokenResponse = match res.json().await {
            Ok(data) => data,
            Err(e) => return Err(Box::new(e)),
        };
    
        let expires_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards") // Handle this error as per your need
            .as_secs() + token_response.expires_in;
    
        let token_data = TokenData {
            access_token: token_response.access_token,
            refresh_token: token_response.refresh_token,
            expires_at,
        };
    
        if let Err(e) = Self::save_token_to_file(&token_data) {
            return Err(e);
        }

        let mut token = self.access_token.lock().unwrap();
        *token = Some(token_data.access_token);
            
        Ok(())
    }

    pub async fn refresh_access_token(&self) -> Result<(), Box<dyn Error>> {
        let token_data = match Self::load_token_from_file() {
            Ok(data) => data,
            Err(_) => return Err("Failed to load token data".into()),
        };


        let client = reqwest::Client::new();
        let res = client
            .post("https://login.eveonline.com/v2/oauth/token") // Replace with the actual token endpoint
            .form(&[
                ("client_id", self.client_id.as_str()),
                ("client_secret", self.client_secret.as_str()),
                ("refresh_token", token_data.refresh_token.as_str()),
                ("grant_type", "refresh_token"),
            ])
            .send()
            .await?;

        let refreshed_token_response: TokenResponse = res.json().await?;

        let current_timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_secs();

        let new_expires_at = current_timestamp + refreshed_token_response.expires_in;

        let new_token_data = TokenData {
            access_token: refreshed_token_response.access_token,
            refresh_token: refreshed_token_response.refresh_token, 
            expires_at: new_expires_at,
        };

        Self::save_token_to_file(&new_token_data)?;

        let mut access_token = self.access_token.lock().unwrap();
        *access_token = Some(new_token_data.access_token);
        let mut expires_at = self.expires_at.lock().unwrap();
        *expires_at = Some(new_expires_at);

        Ok(())
    }


    pub async fn request_location(&self) -> Result<Location, Box<dyn Error>> {
        self.ensure_valid_token().await?;

        let url = format!("https://esi.evetech.net/latest/characters/{}/location/", self.character_id);
    
        println!("{:?}", url);

        let client = reqwest::Client::new();
    
        let response = client.get(url)
            .bearer_auth(self.get_access_token().unwrap())
            .send()
            .await?;
    
        println!("{:?}", response);

        if response.status().is_success() {
            let data = response.json::<Location>().await?; 
            Ok(data)
        } else {
            Err(Box::new(response.error_for_status().unwrap_err()))
        }
    }

    pub async fn request_order_metadata(&self, region: u64) -> Result<(u64, DateTime<Utc>), Box<dyn Error>> {
        let url = format!("https://esi.evetech.net/latest/markets/{}/orders/?datasource=tranquility&order_type=all&page=1", region);
    
        let client = reqwest::Client::new();
        let response = client.get(&url)
            .send()
            .await
            .map_err(|e| e.to_string())?;
    
        let x_pages = match response.headers().get("x-pages") {
            Some(x_pages_value) => {
                match x_pages_value.to_str() {
                    Ok(value_str) => {
                        match value_str.parse::<u64>() {
                            Ok(value) => value,
                            Err(_) => return Err("Failed to parse x-pages value into u64".into()),
                        }
                    }
                    Err(_) => return Err("Invalid x-pages header value".into()),
                }
            }
            None => return Err("X-Pages header not found".into()),
        };
    
        let expiry_unix_time = match response.headers().get("expires") {
            Some(expiry_value) => {
                match expiry_value.to_str() {
                    Ok(value_str) => {
                        match DateTime::parse_from_rfc2822(value_str) {
                            Ok(expiry_date) => expiry_date.with_timezone(&Utc),
                            Err(_) => return Err("Failed to parse expiry date".into()),
                        }
                    }
                    Err(_) => return Err("Invalid expiry header value".into()),
                }
            }
            None => return Err("Expires header not found".into()),
        };
    
        Ok((x_pages, expiry_unix_time))
    }


    
    pub async fn request_orders(&self, region: u64) -> Result<(Vec<Order>, DateTime<Utc>), Box<dyn Error>> {
        let (x_pages, expiry) = self.request_order_metadata(region).await?;

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()?;

        let semaphore = Arc::new(Semaphore::new(10));
        let mut tasks = Vec::new();

        for page in 1..=x_pages {
            let permit = semaphore.clone().acquire_owned().await?;
            let client = client.clone();
            let url = format!("https://esi.evetech.net/latest/markets/{}/orders/?datasource=tranquility&order_type=all&page={}", region, page);

            let task = task::spawn(async move {
                time::sleep(Duration::from_millis(20)).await;
                let response = client.get(&url).send().await?;
                println!("{:?}", &url);
                drop(permit); 
                response.error_for_status()?.json::<Vec<Order>>().await
            });

            tasks.push(task);
        }

        let mut orders = Vec::new();
        for task in tasks {
            match task.await {
                Ok(result) => match result {
                    Ok(mut page_orders) => orders.append(&mut page_orders),
                    Err(e) => return Err(Box::new(e)),
                },
                Err(e) => return Err(Box::new(e)),
            }
        }

        Ok((orders, expiry))
    }

    pub async fn ensure_valid_token(&self) -> Result<(), Box<dyn Error>> {
        let current_timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|e| format!("System time error: {}", e))?
            .as_secs();

        let should_refresh = {
            let expires_at = self.expires_at.lock().unwrap();
            let expires_at_value = expires_at.unwrap_or(0);
            current_timestamp > expires_at_value
        };

        if should_refresh {
            self.refresh_access_token().await?;
        }

        Ok(())
    }
    pub fn get_access_token(&self) -> Option<String> {
        let token = self.access_token.lock().unwrap();
        token.clone()
    }

    pub fn save_token_to_file(token_data: &TokenData) -> Result<(), Box<dyn Error>> {
        let token_json = serde_json::to_string(token_data)?;
        fs::write(Path::new(TOKEN_FILE), token_json)?;
        Ok(())
    }

    fn load_token_from_file() -> Result<TokenData, Box<dyn Error>> {
        let token_json = match fs::read_to_string(Path::new(TOKEN_FILE)) {
            Ok(content) => content,
            Err(_) => return Err("Unable to read token file".into()),
        };
        let token_data: TokenData = serde_json::from_str(&token_json)?;
        Ok(token_data)
    }


}
