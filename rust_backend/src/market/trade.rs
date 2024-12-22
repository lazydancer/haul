use crate::order::Order;

pub struct Trade<'a> {
    from: &'a Order,
    to: &'a Order,
    quantity: usize,
    gross_profit: f64,
}

const TAX_RATE: f64 = 0.08

impl<'a> Trade<'a> {
    pub fn new(from: &'a Order, to: &'a Order, quantity: usize) -> Self {
        Self { from, to, quantity }
    }

    pub fn create_trades(sell_orders: &'a [Order], buy_orders: &'a [Order]) -> Vec<Trade<'a>> {
        let mut trades: Vec<Trade<'a>> = Vec::new();
        let mut grouped_orders: HashMap<i32, (Vec<&'a Order>, Vec<&'a Order>)> = HashMap::new();

        // Grouping sell orders
        for order in sell_orders {
            grouped_orders.entry(order.type_id)
                .or_insert((Vec::new(), Vec::new()))
                .0
                .push(order);
        }

        // Grouping buy orders
        for order in buy_orders {
            grouped_orders.entry(order.type_id)
                .or_insert((Vec::new(), Vec::new()))
                .1
                .push(order);
        }

        // Iterating over each type_id's sell and buy orders to create trades
        for (_type_id, (sells, buys)) in grouped_orders {
            for &sell_order in sells {
                for &buy_order in buys {
                    let quantity = std::cmp::min(sell_order.volume_remain, buy_order.volume_remain);
                    let gross_profit = quantity as f64 * (buy_order.price * (1-TAX_RATE) - sell_order.price);

                    if gross_profit <= 0.0 {
                        continue;
                    }

                    let trade = Trade::new(
                        sell_order,  
                        buy_order,
                        quantity,
                        gross_profit,
                    );

                    trades.push(trade);
                }
            }
        }

        trades
    }

}
