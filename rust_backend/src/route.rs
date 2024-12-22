use std::collections::HashMap;

struct Item {
    profit: f32,
    cost: f32,
    cargo: f32,
    quantity: usize,
}

#[derive(PartialEq, Eq, Hash, Clone)]
struct DiscreteState {
    cost: isize,
    cargo: isize,
}

type StateMap = HashMap<DiscreteState, (f32, Vec<(usize, usize)>)>;

fn discretize(value: f32, precision: f32) -> isize {
    (value / precision).round() as isize
}

fn knapsack(items: &[Item], max_cost: f32, max_cargo: f32) -> (f32, Vec<(usize, usize)>) {
    let mut best_state: StateMap = HashMap::new();
    let precision = 0.01; // Define the precision level for discretization
    best_state.insert(DiscreteState { cost: 0, cargo: 0 }, (0.0, vec![]));

    for (index, item) in items.iter().enumerate() {
        let mut new_state = best_state.clone();

        for (&DiscreteState { cost: current_cost, cargo: current_cargo }, &(current_profit, ref indices)) in &best_state {
            let max_quantity_cost = ((max_cost - current_cost as f32 * precision) / item.cost).floor() as usize;
            let max_quantity_cargo = ((max_cargo - current_cargo as f32 * precision) / item.cargo).floor() as usize;

            let quantity = *[
                item.quantity,
                max_quantity_cost,
                max_quantity_cargo,
            ]
            .iter()
            .min()
            .unwrap();

            if quantity == 0 {
                continue;
            }

            let total_cost = discretize(current_cost as f32 * precision + item.cost * (quantity as f32), precision);
            let total_cargo = discretize(current_cargo as f32 * precision + item.cargo * (quantity as f32), precision);
            let total_profit = current_profit + item.profit * (quantity as f32);

            let mut new_indices = indices.clone();
            new_indices.push((index, quantity));

            new_state
                .entry(DiscreteState { cost: total_cost, cargo: total_cargo })
                .and_modify(|(existing_profit, existing_indices)| {
                    if *existing_profit < total_profit {
                        *existing_profit = total_profit;
                        *existing_indices = new_indices.clone();
                    }
                })
                .or_insert((total_profit, new_indices));
        }

        best_state = new_state;
    }

    best_state.values().max_by(|&(p1, _), &(p2, _)| p1.partial_cmp(&p2).unwrap()).unwrap_or(&(0.0, vec![])).clone()
}

fn main() {
    // Example usage with some items defined
    let items = vec![
        Item {
            profit: 60.0,
            cost: 0.1,
            cargo: 0.2,
            quantity: 100,
        },
        Item {
            profit: 100.0,
            cost: 0.2,
            cargo: 0.5,
            quantity: 50,
        },
        Item {
            profit: 100.0,
            cost: 0.1,
            cargo: 0.5,
            quantity: 50,
        },
        Item {
            profit: 100.0,
            cost: 0.2,
            cargo: 0.3,
            quantity: 50,
        },
    ];

    let max_cost = 50.0;
    let max_cargo = 50.0;

    let (max_profit, item_selections) = knapsack(&items, max_cost, max_cargo);
    println!("Maximum profit: {}", max_profit);
    for (index, quantity) in item_selections {
        println!("Item {} taken with quantity: {}", index, quantity);
    }
}
