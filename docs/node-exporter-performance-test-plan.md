# Node Exporter Long-Term Performance Test Plan

## Overview
This document outlines a comprehensive plan for using Node Exporter to monitor system-level CPU and IO performance degradation over extended periods (6-24 hours) during Kafka vs Redpanda performance testing.

## Current Node Exporter Configuration Analysis

### Deployment Details
- **Image**: `prom/node-exporter:v1.6.1`
- **Port**: 9100
- **Scrape Interval**: 5 seconds (high frequency for detailed monitoring)
- **Resource Limits**: 256M memory, 0.25 CPU cores

### Enabled Collectors
- `--collector.filesystem.mount-points-exclude` - Filesystem metrics
- `--collector.systemd` - Systemd service metrics
- `--collector.processes` - Process-level metrics
- Default collectors: CPU, memory, disk, network, load average

## Key Metrics for CPU/IO Degradation Detection

### CPU Degradation Indicators
```
node_cpu_seconds_total{mode="user"}     # User CPU time
node_cpu_seconds_total{mode="system"}   # System CPU time
node_cpu_seconds_total{mode="iowait"}   # IO wait time
node_cpu_seconds_total{mode="steal"}    # Stolen CPU time
node_load1                              # 1-minute load average
node_load5                              # 5-minute load average
node_load15                             # 15-minute load average
```

### Memory Degradation Indicators
```
node_memory_MemTotal_bytes              # Total memory
node_memory_MemFree_bytes               # Free memory
node_memory_MemAvailable_bytes          # Available memory
node_memory_Buffers_bytes               # Buffer cache
node_memory_Cached_bytes                # Page cache
node_memory_SwapTotal_bytes             # Swap total
node_memory_SwapFree_bytes              # Swap free
```

### Disk IO Degradation Indicators
```
node_disk_reads_completed_total         # Read operations
node_disk_writes_completed_total        # Write operations
node_disk_read_bytes_total              # Bytes read
node_disk_written_bytes_total           # Bytes written
node_disk_io_time_seconds_total         # Time spent on IO
node_disk_read_time_seconds_total       # Time spent reading
node_disk_write_time_seconds_total      # Time spent writing
```

### Network IO Degradation Indicators
```
node_network_receive_bytes_total        # Network bytes received
node_network_transmit_bytes_total       # Network bytes transmitted
node_network_receive_packets_total      # Packets received
node_network_transmit_packets_total     # Packets transmitted
node_network_receive_errs_total         # Receive errors
node_network_transmit_errs_total        # Transmit errors
```

### Filesystem Degradation Indicators
```
node_filesystem_size_bytes              # Filesystem size
node_filesystem_free_bytes              # Free space
node_filesystem_avail_bytes             # Available space
node_filesystem_files                   # Total inodes
node_filesystem_files_free              # Free inodes
```

## Long-Term Performance Test Design

### Test Duration Options
1. **6-Hour Test**: Quick degradation detection
2. **12-Hour Test**: Medium-term stability assessment
3. **24-Hour Test**: Full daily cycle analysis

### Test Phases
1. **Baseline Phase** (30 minutes): System at rest
2. **Ramp-Up Phase** (30 minutes): Gradual load increase
3. **Sustained Load Phase** (4-22 hours): Constant workload
4. **Cool-Down Phase** (30 minutes): Load reduction
5. **Recovery Phase** (30 minutes): System recovery monitoring

### Workload Patterns
1. **Steady State**: Constant producer/consumer rates
2. **Burst Pattern**: Periodic high-load spikes
3. **Gradual Increase**: Slowly increasing load over time
4. **Mixed Pattern**: Combination of all patterns

## Prometheus Configuration Enhancements

### Extended Retention for Long-Term Testing
```yaml
# Current: 30d retention, 10GB size
# Recommended for long-term testing:
--storage.tsdb.retention.time=90d
--storage.tsdb.retention.size=50GB
```

### High-Frequency Scraping for Node Exporter
```yaml
- job_name: 'node-exporter-detailed'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 1s  # Increased from 5s for detailed monitoring
  scrape_timeout: 5s
```

## Degradation Detection Thresholds

### CPU Degradation Alerts
- **CPU Usage > 80%** for more than 10 minutes
- **IO Wait > 30%** for more than 5 minutes
- **Load Average > CPU Cores * 2** for more than 15 minutes

### Memory Degradation Alerts
- **Available Memory < 20%** for more than 5 minutes
- **Swap Usage > 10%** for more than 10 minutes
- **Memory Growth Rate > 1GB/hour** sustained

### Disk IO Degradation Alerts
- **Disk Utilization > 90%** for more than 5 minutes
- **Average IO Wait > 100ms** for more than 10 minutes
- **Disk Queue Depth > 10** for more than 5 minutes

### Network Degradation Alerts
- **Network Errors > 1%** of total packets
- **Network Utilization > 80%** of interface capacity
- **Packet Loss > 0.1%** sustained

## Test Execution Strategy

### Pre-Test Setup
1. Establish baseline metrics (30-minute collection)
2. Document initial system state
3. Configure enhanced monitoring
4. Set up automated alerting

### During Test Execution
1. Monitor real-time dashboards
2. Collect detailed metrics every second
3. Log any anomalies or alerts
4. Track resource utilization trends

### Post-Test Analysis
1. Generate degradation trend reports
2. Identify performance bottlenecks
3. Compare Kafka vs Redpanda resource usage
4. Document findings and recommendations

## Expected Degradation Patterns

### Memory Leaks
- Gradual increase in memory usage over time
- Decreasing available memory
- Increasing swap usage

### CPU Performance Degradation
- Increasing CPU usage under same workload
- Growing IO wait times
- Rising load averages

### Disk IO Bottlenecks
- Increasing disk queue depths
- Growing IO wait times
- Decreasing throughput over time

### Network Saturation
- Increasing network utilization
- Growing packet loss rates
- Rising network errors

## Success Criteria

### Stable Performance
- CPU usage remains within ±5% of baseline
- Memory usage growth < 100MB/hour
- Disk IO latency remains stable
- Network performance maintains baseline levels

### Degradation Detection
- Early warning alerts trigger before critical thresholds
- Clear trend identification in monitoring data
- Actionable insights for performance optimization
- Comparative analysis between Kafka and Redpanda

## Next Steps

1. Implement enhanced Prometheus configuration
2. Create custom Grafana dashboards for degradation monitoring
3. Set up automated alerting rules
4. Develop baseline measurement scripts
5. Design and execute long-term test scenarios