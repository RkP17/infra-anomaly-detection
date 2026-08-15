import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict


# TODO: refactor to use a single function instead of two separate functions for business and batch metrics
def simulate_metric(timestamps, business_mean, business_scale, offhours_mean, offhours_scale, clip_min=0, clip_max=100):
    mean = np.where((timestamps.hour >= 9) & (timestamps.hour < 17) & (timestamps.dayofweek < 5), business_mean, offhours_mean)
    scale = np.where((timestamps.hour >= 9) & (timestamps.hour < 17) & (timestamps.dayofweek < 5), business_scale, offhours_scale)
    
    metric = np.random.normal(loc=mean, scale=scale, size=len(timestamps))
    metric = np.clip(metric, clip_min, clip_max)
    
    return metric

def simulate_batch_metrics(timestamps, server_type, batch_mean, batch_scale, clip_min=0, clip_max=100):
    if server_type == "batch_worker":
        mean = np.where((timestamps.hour >= 2) & (timestamps.hour < 3), batch_mean, 0)
        scale = np.where((timestamps.hour >= 2) & (timestamps.hour < 3), batch_scale, 0)
        
        metric = np.random.normal(loc=mean, scale=scale, size=len(timestamps))
        metric = np.clip(metric, clip_min, clip_max)
        
        return metric
    else:
        return np.zeros(len(timestamps))

def generate_row(server_id, server_type, cpu, memory_percent, disk_io, timestamps):
    df = pd.DataFrame({
        "timestamp": timestamps,
        "server_id": server_id,
        "server_type": server_type,
        "cpu_percent": cpu,
        "memory_percent": memory_percent,
        "disk_io": disk_io,
        "is_anomaly": np.zeros(len(timestamps), dtype=int)
    })
    
    return df

# Set the timeframe to be 3 weeks of 5-minute intervals
timestamps = pd.date_range(start="2025-01-01", periods=6048, freq="5min")
servers = []
# Defining the server types and Ids for each
serverTypes = ["web", "database", "cache", "load_balancer", "batch_worker" ]
serverProfiles = {
    "web": {"cpu_business_mean": 50, "cpu_business_scale": 10, "cpu_offhours_mean": 20, "cpu_offhours_scale": 5, "mem_business_mean": 60, "mem_business_scale": 10, "mem_offhours_mean": 30, "mem_offhours_scale": 5, "disk_io_business_mean": 100, "disk_io_business_scale": 10, "disk_io_offhours_mean": 50, "disk_io_offhours_scale": 10},
    "database": {"cpu_business_mean": 70, "cpu_business_scale": 15, "cpu_offhours_mean": 30, "cpu_offhours_scale": 10, "mem_business_mean": 80, "mem_business_scale": 5, "mem_offhours_mean": 50, "mem_offhours_scale": 2, "disk_io_business_mean": 300, "disk_io_business_scale": 50, "disk_io_offhours_mean": 150, "disk_io_offhours_scale": 20},
    "cache": {"cpu_business_mean": 40, "cpu_business_scale": 5, "cpu_offhours_mean": 10, "cpu_offhours_scale": 3, "mem_business_mean": 50, "mem_business_scale": 5, "mem_offhours_mean": 20, "mem_offhours_scale": 2, "disk_io_business_mean": 50, "disk_io_business_scale": 10, "disk_io_offhours_mean": 20, "disk_io_offhours_scale": 5},
    "load_balancer": { "cpu_business_mean":70, "cpu_business_scale": 25, "cpu_offhours_mean": 30, "cpu_offhours_scale": 5, "mem_business_mean": 70, "mem_business_scale": 20, "mem_offhours_mean": 40, "mem_offhours_scale": 5, "disk_io_business_mean": 50, "disk_io_business_scale": 10, "disk_io_offhours_mean": 20, "disk_io_offhours_scale": 5},
    "batch_worker": {"cpu_business_mean": 60, "cpu_business_scale": 20, "mem_business_mean": 70, "mem_business_scale": 20,"disk_io_business_mean": 200, "disk_io_business_scale": 30}
}

for server_type in serverTypes:
    for i in range(1, 4):
        server_id = f"{server_type}_{i}"
        profile = serverProfiles[server_type]
        if server_type == "batch_worker":
            batch_cpu = simulate_batch_metrics(timestamps, server_type, profile["cpu_business_mean"], profile["cpu_business_scale"])
            batch_memory_percent = simulate_batch_metrics(timestamps, server_type, profile["mem_business_mean"], profile["mem_business_scale"])
            batch_disk_io = simulate_batch_metrics(timestamps, server_type, profile["disk_io_business_mean"], profile["disk_io_business_scale"], clip_min=0, clip_max=200)
            servers.append(generate_row(server_id, server_type, batch_cpu, batch_memory_percent, batch_disk_io, timestamps))
        else:
            cpu = simulate_metric(timestamps, profile["cpu_business_mean"], profile["cpu_business_scale"], profile["cpu_offhours_mean"], profile["cpu_offhours_scale"])
            memory_percent = simulate_metric(timestamps, profile["mem_business_mean"], profile["mem_business_scale"], profile["mem_offhours_mean"], profile["mem_offhours_scale"])
            disk_io = simulate_metric(timestamps, profile["disk_io_business_mean"], profile["disk_io_business_scale"], profile["disk_io_offhours_mean"], profile["disk_io_offhours_scale"], clip_min=0, clip_max=500)
            servers.append(generate_row(server_id, server_type, cpu, memory_percent, disk_io, timestamps))

full_df = pd.concat(servers, ignore_index=True)

anomalies = {
    "web_1": [
        {"start": "2025-01-10 10:00:00", "end": "2025-01-10 12:00:00", "cpu_mean": 95, "cpu_scale": 5}
    ],
    "web_2": [
            {"start": "2025-01-16 16:00:00", "end": "2025-01-16 16:35:00", "memory_mean": 90, "memory_scale": 10},
            {"start": "2025-01-21 04:10:00", "end": "2025-01-21 07:10:00", "cpu_mean": 10, "cpu_scale": 5}
    ],

    "database_1": [
        {"start": "2025-01-15 14:00:00", "end": "2025-01-15 16:00:00", "disk_io_mean": 100, "disk_io_scale": 25}
    ],
    "database_2": [
        {"start": "2025-01-20 10:35:00", "end": "2025-01-20 11:40:00", "cpu_mean": 20, "cpu_scale": 5}
    ],
    "cache_3": [
        {"start": "2025-01-18 08:25:00", "end": "2025-01-18 08:50:00", "memory_mean": 80, "memory_scale": 10}
    ],
    "load_balancer_2": [
        {"start": "2025-01-12 13:10:00", "end": "2025-01-12 13:25:00", "cpu_mean": 20, "cpu_scale": 2}
    ],
    "load_balancer_3": [
        {"start": "2025-01-20 02:00:00", "end": "2025-01-20 02:30:00", "disk_io_mean": 40, "disk_io_scale": 5},
        {"start": "2025-01-06 15:00:00", "end": "2025-01-06 15:20:00", "disk_io_mean": 60, "disk_io_scale": 10}
    ],
    "batch_worker_1": [
        {"start": "2025-01-14 03:40:00", "end": "2025-01-14 06:00:00", "cpu_mean": 90, "cpu_scale": 10}
    ],
    "batch_worker_2": [
        {"start": "2025-01-19 02:00:00", "end": "2025-01-19 02:15:00", "memory_mean": 10, "memory_scale": 2}
    ],
    "batch_worker_3": [
        {"start": "2025-01-12 02:40:00", "end": "2025-01-12 03:00:00", "disk_io_mean": 300, "disk_io_scale": 30}
    ]
}

def inject_anomalies(df, anomalies) :
    for server_id, anomaly_list in anomalies.items():
        for anomaly in anomaly_list:
            start = pd.to_datetime(anomaly["start"])
            end = pd.to_datetime(anomaly["end"])
            
            condition = df.loc[(df['server_id'] == server_id) & (df['timestamp'].between(start, end))]
            if "cpu_mean" in anomaly:
                df.loc[condition.index, 'cpu_percent'] = np.random.normal(loc=anomaly["cpu_mean"], scale=anomaly["cpu_scale"], size=len(condition))
            elif "memory_mean" in anomaly:
                df.loc[condition.index, 'memory_percent'] = np.random.normal(loc=anomaly["memory_mean"], scale=anomaly["memory_scale"], size=len(condition))
            elif "disk_io_mean" in anomaly:
                df.loc[condition.index, 'disk_io'] = np.random.normal(loc=anomaly["disk_io_mean"], scale=anomaly["disk_io_scale"], size=len(condition))
            
            df.loc[condition.index, 'is_anomaly'] = 1
    

inject_anomalies(full_df, anomalies)

full_df.to_csv('../data/simulated_server_metrics.csv', index=False)


