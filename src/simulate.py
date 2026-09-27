import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Set a random seed for reproducibility
np.random.seed(42)

# ========= Configuration =========

# Set the timeframe to be 3 weeks of 5-minute intervals
TIMESTAMPS = pd.date_range(
    start="2025-01-01", 
    periods=6048 , 
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
        "is_predictive_anomaly": 0,
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

anomalies = {}

# ========= Generate Anomalies =========

# The model strugled to detect the anomlies injected above, as this made the dataset extermely imbalanced. 
# To make the dataset more balanced, we will generate additional anomalies for each server.

def generate_anomalies(
    server_ids,
    start_date,
    end_date,
    seed=42
):
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    
    metrics = ["cpu_percent", "memory_percent", "disk_io"]
    generated_anomalies = {}

    available_intervals = int((end_date - start_date).total_seconds() // 300)
    if available_intervals < 13:
        raise ValueError("The simulation window must contain at least 65 minutes")

    for server_id in server_ids:
        server_anomalies = []
        anomalies_per_server = rng.integers(2, 8)
        for _ in range(anomalies_per_server):
            anomaly_type = rng.choice(["spike","drop"])
            
            anomaly_start_offset = rng.integers(0, int((end_date - start_date).total_seconds() // 300)) *5
            start_time = start_date + pd.Timedelta(minutes=anomaly_start_offset)
            anomaly_duration = rng.integers(2, 7) * 5
            end_time = start_time + pd.Timedelta(minutes=anomaly_duration)
            metric = rng.choice(metrics)
            
            available_minutes = int((end_date - start_date).total_seconds() // 60)
            
            if available_minutes < 5:
                raise ValueError("end_date must be at least 5 minutes after start_date")

            server_rows = full_df.loc[full_df["server_id"] == server_id]
            current_value = server_rows.iloc[
                (server_rows["timestamp"] - start_time).abs().argmin()
            ][metric]

            if anomaly_type == "spike":
                if (metric in ["cpu_percent", "memory_percent"]):
                    mean_value = current_value + rng.integers(20, 50)
                    mean_value = np.clip(mean_value, 0, 100)
                else:
                    mean_value = np.clip(current_value + rng.integers(50, 100), 0, None)
                scale_value = rng.integers(1, 5)
            else:
                if (metric == "cpu_percent") or (metric == "memory_percent"):
                    mean_value = current_value - rng.integers(20, 50)
                    mean_value = np.clip(mean_value, 0, 100)
                else:
                    mean_value = np.clip(current_value - rng.integers(50, 100), 0, None)
                scale_value = rng.integers(1, 5)
        
            server_anomalies.append({
                "start": start_time,
                "end": end_time,
                "metric": metric,
                "anomaly_type": f'{metric}_{anomaly_type}',
                "mean": mean_value,
                "scale": scale_value
            })
        
        generated_anomalies[server_id] = server_anomalies
        
    return generated_anomalies

# ========= Inject Anomalies =========

generated_anomalies = generate_anomalies(
    server_ids=full_df["server_id"].unique(),
    start_date=TIMESTAMPS.min(),
    end_date=TIMESTAMPS.max(),
    seed=42,
)

for server_id, anomaly_list in generated_anomalies.items():
    anomalies.setdefault(server_id, []).extend(anomaly_list)

# store the anomalies in a file for reference
anomaly_reference = pd.DataFrame(
    [
        {"server_id": server_id, **anomaly}
        for server_id, anomaly_list in generated_anomalies.items()
        for anomaly in anomaly_list
    ]
)
anomaly_reference.to_csv("../data/injected_anomalies_reference.csv", index=False)

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

# ========= Add recovery periods =========

def inject_recovery_period(df, anomalies, seed=42):
    rng = np.random.default_rng(seed)

    for server_id, anomaly_list in anomalies.items():
        for anomaly in anomaly_list:
            end_anomaly_time = pd.to_datetime(anomaly["end"])
            recovery_start = end_anomaly_time + pd.Timedelta(minutes=5)
            recovery_end = recovery_start + pd.Timedelta(rng.integers(3,7) * 5, unit='m')
            
            metric = anomaly['metric']
            
            recovery_mask = (
                (df['server_id'] == server_id) &
                (df['timestamp'].between(recovery_start, recovery_end))
            )
            recovery_indices = df.index[recovery_mask]
            if len(recovery_indices) == 0:
                continue

            end_value = df.loc[
                (df['server_id'] == server_id) &
                (df['timestamp'] == end_anomaly_time),
                metric,
            ].iloc[0] # extracts the row and coverts it into a pandas series, then extracts the value of the metric column
            target_value = df.loc[
                (df['server_id'] == server_id) &
                (df['timestamp'] == recovery_end),
                metric,
            ].iloc[0]

            recovery_values = np.linspace(end_value, target_value, len(recovery_indices))
            recovery_values += np.random.normal(0, anomaly['scale'] / 2, len(recovery_indices))

            if metric in ['cpu_percent', 'memory_percent']:
                recovery_values = np.clip(recovery_values, 0, 100)
            else:
                recovery_values = np.clip(recovery_values, 0, None)

            df.loc[recovery_indices, metric] = recovery_values
            df.loc[recovery_indices, 'anomaly_type'] = f"recovery_{anomaly['anomaly_type']}"
    return df

inject_recovery_period(full_df, anomalies)

# ========= Inject Predicitve Anomalies =========

def create_predictive_trend(start_value, end_value, length, noise_scale):
    progress = np.linspace(0, 1, length)
    smooth_progress = progress * progress * (3 - 2 * progress)
    trend = start_value + (end_value - start_value) * smooth_progress
    noise = np.cumsum(np.random.normal(0, noise_scale, length))
    noise -= np.linspace(noise[0], noise[-1], length)
    return trend + noise

def inject_predictive_anomalies(df, anomalies):
    rng = np.random.default_rng(42)
    
    for server_id, anomaly_list in anomalies.items():
        for anomaly in anomaly_list:
            random_num = rng.integers(10, 60)
            start = pd.Timestamp(anomaly["start"])
            
            precursor_start = start - pd.Timedelta(minutes=int(random_num))
            precursor_end = start - pd.Timedelta(minutes=5)  # Up to the start of the anomaly
            
            precursor_condition = df.loc[
                (df['server_id'] == server_id) & 
                (df['timestamp'].between(precursor_start, precursor_end))
            ]
            
            indices = precursor_condition.index
            
            metric = anomaly["metric"]
            
            
            start_value = df.loc[precursor_condition.index[0], metric] # Value at the start of the precursor period
            end_value = anomaly['mean'] # Value at the end of the precursor period (just before the anomaly starts)
            
            trend = create_predictive_trend(
                start_value,
                end_value,
                len(indices),
                anomaly['scale'] / 5,
            )
            
            if metric in ("cpu_percent", "memory_percent"):
                df.loc[indices, metric] = np.clip(trend, 0, 100)
            else:
                df.loc[indices, metric] = np.clip(trend, 0, None)
            
            df.loc[indices, 'anomaly_type'] = f"predictive_{anomaly['anomaly_type']}"
            df.loc[precursor_condition.index, 'is_predictive_anomaly'] = 1
    return df
        
inject_predictive_anomalies(full_df, anomalies)      
    

# Save the simulated data to a CSV file
full_df.to_csv('../data/simulated_server_metric_with_predictive_anomalies.csv', index=False)
print("Simulated server metrics with anomalies have been saved to 'simulated_server_metrics.csv'.")
