import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Set a random seed for reproducibility
np.random.seed(42)

# ========= Configuration =========

# Set the timeframe to be 6 weeks of 5-minute intervals
TIMESTAMPS = pd.date_range(
    start="2025-01-01", 
    periods=12096, 
    freq="5min"
)

# Defining the server types
SERVER_TYPES = [
    "web", 
    "database", 
    "cache", 
    "load_balancer", 
    "batch_worker" 
]

# Defining the server profiles for each server type
SERVER_PROFILES = {
    "web": {
        "cpu_base": 25,
        "cpu_amplitude": 30,
        "memory_base": 35,
        "memory_amplitude": 20,
        "disk_base": 50,
        "disk_amplitude": 60,
        "noise": 3,
    },

    "database": {
        "cpu_base": 30,
        "cpu_amplitude": 35,
        "memory_base": 55,
        "memory_amplitude": 20,
        "disk_base": 120,
        "disk_amplitude": 150,
        "noise": 5,
    },

    "cache": {
        "cpu_base": 15,
        "cpu_amplitude": 25,
        "memory_base": 55,
        "memory_amplitude": 20,
        "disk_base": 20,
        "disk_amplitude": 30,
        "noise": 2,
    },

    "load_balancer": {
        "cpu_base": 25,
        "cpu_amplitude": 35,
        "memory_base": 30,
        "memory_amplitude": 20,
        "disk_base": 20,
        "disk_amplitude": 25,
        "noise": 4,
    },

    "batch_worker": {
        "cpu_base": 5,
        "cpu_amplitude": 5,
        "memory_base": 15,
        "memory_amplitude": 5,
        "disk_base": 10,
        "disk_amplitude": 10,
        "noise": 2,
    }
}

# ========= Time based workload simulation =========

def generate_workload(timestamps, server_type):
    hour = timestamps.hour + timestamps.minute / 60.0
    weekday = timestamps.dayofweek
    
    # Generate a cycle that peaks during business hours but is more quiet during off hours
    daily_cycle = (
        0.5 + 0.5 * np.sin(2 * np.pi * (hour - 6) / 24)
    )
    
    # Weekends
    weekend = np.where(weekday >= 5, 0.5, 1.0)  # Reduce workload on weekends
    
    # Combine the daily cycle and the weekend factor
    workload = daily_cycle * weekend
    
    # Generate a batch worker specfic
    if server_type == "batch_worker":
        # Batch workers have a spike in workload during the night (2 AM to 3 AM)
        batch_spike = np.where((hour >= 2) & (hour < 3), 1.5, 1.0)
        workload *= batch_spike
    
    return workload



# ========= Add realistic noise to metrics =========

def add_noise(metric, noise_level):
    noise = np.random.normal(loc=0, scale=noise_level, size=len(metric))
    return metric + noise



# ========= Generate server metrics =========
def simulate_server_metrics(server_id, server_type, timestamps, profile):
    workload = generate_workload(timestamps, server_type)
    
    # server specific variation to simulate different servers of the same type
    server_variation = np.random.normal(
        1,
        0.05
    )    
    
    # ==== CPU ====
    
    cpu = (
        profile["cpu_base"] +
        profile["cpu_amplitude"] * workload * server_variation
    )
    
    cpu = add_noise(cpu, profile["noise"])
    
    cpu = np.clip(cpu, 0, 100)  # Ensure CPU percentage stays within 0-100
    
    # ==== Memory ==== 
    memory = (
        profile["memory_base"] +
        profile["memory_amplitude"] * workload * server_variation
    )
    
    memory = add_noise(memory, profile["noise"])
    
    memory = np.clip(memory, 0, 100)  # Ensure memory percentage stays within 0-100
    
    # ==== Disk I/O ==== 
    disk_io = (
        profile["disk_base"] +
        profile["disk_amplitude"] * workload * server_variation
    )
    
    disk_io = add_noise(disk_io, profile["noise"])
    
    disk_io = np.clip(disk_io, 0, None)  # Ensure disk I/O is non-negative

    return pd.DataFrame({
        "timestamp": timestamps,
        "server_id": server_id,
        "server_type": server_type,
        "cpu_percent": cpu,
        "memory_percent": memory,
        "disk_io": disk_io,
        "is_anomaly": 0,
        "anomaly_type": "normal"
    })

# ========= Generate the simulated data for each server type and server id =========

servers = []

for server_type in SERVER_TYPES:
    for i in range(1,4):
        server_id = f"{server_type}_{i}"
        profile = SERVER_PROFILES[server_type]
        server_metrics = simulate_server_metrics(server_id, server_type, TIMESTAMPS, profile)
        servers.append(server_metrics)

full_df = pd.concat(servers, ignore_index=True)

# ========= Define the anomalies =========

anomalies = {

    "web_1": [
        {
            "start": "2025-01-10 10:00",
            "end": "2025-01-10 12:00",
            "metric": "cpu_percent",
            "anomaly_type": "cpu_spike",
            "mean": 92,
            "scale": 3
        }
    ],

    "web_2": [
        {
            "start": "2025-01-16 16:00",
            "end": "2025-01-16 16:35",
            "metric": "memory_percent",
            "anomaly_type": "memory_spike",
            "mean": 92,
            "scale": 3
        },
        {
            "start": "2025-01-21 04:10",
            "end": "2025-01-21 07:10",
            "metric": "cpu_percent",
            "anomaly_type": "cpu_drop",
            "mean": 3,
            "scale": 1
        }
    ],

    "database_1": [
        {
            "start": "2025-01-15 14:00",
            "end": "2025-01-15 16:00",
            "metric": "disk_io",
            "anomaly_type": "disk_io_drop",
            "mean": 25,
            "scale": 5
        }
    ],

    "database_2": [
        {
            "start": "2025-01-20 10:35",
            "end": "2025-01-20 11:40",
            "metric": "cpu_percent",
            "anomaly_type": "cpu_drop",
            "mean": 8,
            "scale": 2
        }
    ],

    "cache_3": [
        {
            "start": "2025-01-18 08:25",
            "end": "2025-01-18 08:50",
            "metric": "memory_percent",
            "anomaly_type": "memory_spike",
            "mean": 95,
            "scale": 2
        }
    ],

    "load_balancer_2": [
        {
            "start": "2025-01-12 13:10",
            "end": "2025-01-12 13:25",
            "metric": "cpu_percent",
            "anomaly_type": "cpu_drop",
            "mean": 8,
            "scale": 2
        }
    ],

    "load_balancer_3": [
        {
            "start": "2025-01-20 02:00",
            "end": "2025-01-20 02:30",
            "metric": "disk_io",
            "anomaly_type": "disk_io_spike",
            "mean": 250,
            "scale": 10
        },
        {
            "start": "2025-01-06 15:00",
            "end": "2025-01-06 15:20",
            "metric": "disk_io",
            "anomaly_type": "disk_io_spike",
            "mean": 120,
            "scale": 5
        }
    ],

    "batch_worker_1": [
        {
            "start": "2025-01-14 03:40",
            "end": "2025-01-14 06:00",
            "metric": "cpu_percent",
            "anomaly_type": "cpu_spike",
            "mean": 90,
            "scale": 5
        }
    ],

    "batch_worker_2": [
        {
            "start": "2025-01-19 02:00",
            "end": "2025-01-19 02:15",
            "metric": "memory_percent",
            "anomaly_type": "memory_drop",
            "mean": 3,
            "scale": 1
        }
    ],

    "batch_worker_3": [
        {
            "start": "2025-01-12 02:40",
            "end": "2025-01-12 03:00",
            "metric": "disk_io",
            "anomaly_type": "disk_io_spike",
            "mean": 180,
            "scale": 10
        }
    ]
}


# ========= Inject Anomalies =========

def inject_anomalies(df, anomalies):
    for server_id, anomaly_list in anomalies.items():
        for anomaly in anomaly_list:
            start = pd.to_datetime(anomaly["start"])
            end = pd.to_datetime(anomaly["end"])
            
            condition = (
                df.loc[(df['server_id'] == server_id) & 
                       (df['timestamp'].between(start, end)
                )]
            )
            
            if anomaly["metric"] == "cpu_percent":
                values = np.random.normal(loc=anomaly['mean'], scale=anomaly['scale'], size=len(condition))
                df.loc[condition.index, 'anomaly_type'] = anomaly['anomaly_type']
                df.loc[condition.index, 'cpu_percent'] = np.clip(values, 0, 100)
            elif anomaly["metric"] == "memory_percent":
                values = np.random.normal(loc=anomaly['mean'], scale=anomaly['scale'], size=len(condition))
                df.loc[condition.index, 'anomaly_type'] = anomaly['anomaly_type']
                df.loc[condition.index, 'memory_percent'] = np.clip(values, 0, 100)
            elif anomaly["metric"] == "disk_io":
                values = np.random.normal(loc=anomaly['mean'], scale=anomaly['scale'], size=len(condition))
                df.loc[condition.index, 'anomaly_type'] = anomaly['anomaly_type']
                df.loc[condition.index, 'disk_io'] = np.clip(values, 0, None)
            
            df.loc[condition.index, 'is_anomaly'] = 1
    return df

inject_anomalies(full_df, anomalies)

# Save the simulated data to a CSV file
full_df.to_csv('../data/simulated_server_metrics.csv', index=False)
print("Simulated server metrics with anomalies have been saved to 'simulated_server_metrics.csv'.")


