import flwr as fl

# Define strategy: simple averaging of weights
strategy = fl.server.strategy.FedAvg(
    fraction_fit=1.0,  # Sample 100% of available clients
    min_fit_clients=1, # Minimum 1 client to start (for demo)
    min_available_clients=1,
)

if __name__ == "__main__":
    print("🌸 STARTING JIRACHI HIVE MIND (FEDERATED SERVER)...")
    fl.server.start_server(
        server_address="0.0.0.0:8080", 
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy
    )
