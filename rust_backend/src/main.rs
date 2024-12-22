mod manager;
mod eve_service;
mod eve_api;
mod pathfinding;
mod market;

use manager::Manager;

use actix_web::{web, App, HttpServer, Responder, HttpResponse, http::header};
use std::sync::Mutex;
use tokio::sync::watch;
use serde::Deserialize;


async fn index() -> impl Responder {
    "Hi"
}

async fn location(manager: web::Data<Manager>) -> impl Responder {
    match manager.location() {
        Some(location) => {
            let station_id = location.station_id.map_or("None".to_string(), |id| id.to_string());
            let structure_id = location.structure_id.map_or("None".to_string(), |id| id.to_string());
            format!(
                "Current location: Solar System ID: {}, Station ID: {}, Structure ID: {}",
                location.solar_system_id, station_id, structure_id
            )
        },
        None => "No location available".to_string(),
    }
}

async fn orders(manager: web::Data<Manager>) -> impl Responder {
    let orders = manager.orders();
    HttpResponse::Ok().json(orders)
}

async fn start_oauth(manager: web::Data<Manager>) -> HttpResponse {
    let auth_url = manager.get_authorization_url();
    HttpResponse::Found()
        .append_header((header::LOCATION, auth_url.as_str()))
        .finish()
}

#[derive(Deserialize)]
struct AuthCode {
    code: String,
}

async fn oauth_callback(
    query: web::Query<AuthCode>,
    manager: web::Data<Manager>,
) -> HttpResponse {
    match manager.exchange_code_for_token(&query.code).await {
        Ok(_) => HttpResponse::Ok().body("Token exchange successful"),
        Err(e) => HttpResponse::InternalServerError().body(format!("Error: {}", e)),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let manager = web::Data::new(Manager::new());


    let manager_clone = manager.clone();
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    let manager_handle = tokio::spawn(async move {
        manager_clone.run(shutdown_rx).await;
    });

    let server = HttpServer::new(move || {
        App::new()
            .app_data(manager.clone())
            .route("/", web::get().to(index))
            .route("/location", web::get().to(location))
            .route("/orders", web::get().to(orders))
            .route("/start_oauth", web::get().to(start_oauth))
            .route("/oauth_callback", web::get().to(oauth_callback))
    })
    .bind("127.0.0.1:8080")?
    .run();

    ctrlc::set_handler(move || {
        let _ = shutdown_tx.send(true);
    })
    .expect("Error setting Ctrl-C handler");

    tokio::select! {
        _ = server => {},
        _ = manager_handle => {},
    }

    Ok(())
}
