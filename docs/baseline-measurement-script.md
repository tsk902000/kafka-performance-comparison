# Baseline Measurement Script for Node Exporter

## Overview
This document provides the baseline measurement script design for capturing initial CPU/IO state using Node Exporter metrics before starting long-term performance tests.

## Script Purpose
- Establish baseline system performance metrics
- Create reference points for degradation detection
- Generate initial system health report
- Validate monitoring infrastructure

## Baseline Measurement Script

```bash
#!/bin/bash

# Node Exporter Baseline Measurement Script
# This script collects baseline system metrics from Node Exporter
# Usage: ./baseline-measurement.sh [duration_minutes] [output_file]

set -euo pipefail

# Configuration
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
DURATION_MINUTES="${1:-30}"
OUTPUT_FILE="${2:-baseline-$(date +%Y%m%d-%H%M%S).json}"
MEASUREMENT_INTERVAL=5  # seconds between measurements

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Prometheus is accessible
check_prometheus() {
    log "Checking Prometheus connectivity..."
    if curl -s "${PROMETHEUS_URL}/api/v1/query?query=up" > /dev/null; then
        success "Prometheus is accessible at ${PROMETHEUS_URL}"
    else
        error "Cannot connect to Prometheus at ${PROMETHEUS_URL}"
        exit 1
    fi
}

# Query Prometheus for a metric
query_metric() {
    local query="$1"
    local result
    result=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" | jq -r '.data.result[0].value[1] // "null"')
    echo "$result"
}

# Collect baseline metrics
collect_baseline_metrics() {
    log "Collecting baseline metrics for ${DURATION_MINUTES} minutes..."
    
    local start_time=$(date +%s)
    local end_time=$((start_time + DURATION_MINUTES * 60))
    local measurements=()
    
    while [ $(date +%s) -lt $end_time ]; do
        local timestamp=$(date +%s)
        local measurement=$(cat <<EOF
{
    "timestamp": $timestamp,
    "datetime": "$(date -Iseconds)",
    "cpu": {
        "user": $(query_metric "rate(node_cpu_seconds_total{mode=\"user\"}[1m])"),
        "system": $(query_metric "rate(node_cpu_seconds_total{mode=\"system\"}[1m])"),
        "iowait": $(query_metric "rate(node_cpu_seconds_total{mode=\"iowait\"}[1m])"),
        "idle": $(query_metric "rate(node_cpu_seconds_total{mode=\"idle\"}[1m])")
    },
    "memory": {
        "total_bytes": $(query_metric "node_memory_MemTotal_bytes"),
        "free_bytes": $(query_metric "node_memory_MemFree_bytes"),
        "available_bytes": $(query_metric "node_memory_MemAvailable_bytes"),
        "cached_bytes": $(query_metric "node_memory_Cached_bytes"),
        "buffers_bytes": $(query_metric "node_memory_Buffers_bytes"),
        "swap_total_bytes": $(query_metric "node_memory_SwapTotal_bytes"),
        "swap_free_bytes": $(query_metric "node_memory_SwapFree_bytes")
    },
    "load": {
        "load1": $(query_metric "node_load1"),
        "load5": $(query_metric "node_load5"),
        "load15": $(query_metric "node_load15")
    },
    "disk": {
        "reads_completed": $(query_metric "rate(node_disk_reads_completed_total[1m])"),
        "writes_completed": $(query_metric "rate(node_disk_writes_completed_total[1m])"),
        "read_bytes": $(query_metric "rate(node_disk_read_bytes_total[1m])"),
        "written_bytes": $(query_metric "rate(node_disk_written_bytes_total[1m])"),
        "io_time": $(query_metric "rate(node_disk_io_time_seconds_total[1m])")
    },
    "network": {
        "receive_bytes": $(query_metric "rate(node_network_receive_bytes_total[1m])"),
        "transmit_bytes": $(query_metric "rate(node_network_transmit_bytes_total[1m])"),
        "receive_packets": $(query_metric "rate(node_network_receive_packets_total[1m])"),
        "transmit_packets": $(query_metric "rate(node_network_transmit_packets_total[1m])"),
        "receive_errors": $(query_metric "rate(node_network_receive_errs_total[1m])"),
        "transmit_errors": $(query_metric "rate(node_network_transmit_errs_total[1m])")
    },
    "filesystem": {
        "size_bytes": $(query_metric "node_filesystem_size_bytes{fstype!=\"tmpfs\"}"),
        "free_bytes": $(query_metric "node_filesystem_free_bytes{fstype!=\"tmpfs\"}"),
        "available_bytes": $(query_metric "node_filesystem_avail_bytes{fstype!=\"tmpfs\"}")
    }
}
EOF
)
        measurements+=("$measurement")
        
        # Progress indicator
        local elapsed=$(($(date +%s) - start_time))
        local progress=$((elapsed * 100 / (DURATION_MINUTES * 60)))
        printf "\rProgress: [%-50s] %d%%" $(printf "#%.0s" $(seq 1 $((progress / 2)))) $progress
        
        sleep $MEASUREMENT_INTERVAL
    done
    
    echo # New line after progress bar
    
    # Calculate averages and create final baseline report
    create_baseline_report "${measurements[@]}"
}

# Create baseline report with statistics
create_baseline_report() {
    local measurements=("$@")
    log "Generating baseline report..."
    
    # Create JSON array of measurements
    local measurements_json="["
    for i in "${!measurements[@]}"; do
        measurements_json+="${measurements[$i]}"
        if [ $i -lt $((${#measurements[@]} - 1)) ]; then
            measurements_json+=","
        fi
    done
    measurements_json+="]"
    
    # Generate summary statistics (this would need jq processing)
    local baseline_report=$(cat <<EOF
{
    "baseline_info": {
        "collection_start": "$(date -Iseconds -d @${start_time})",
        "collection_end": "$(date -Iseconds)",
        "duration_minutes": $DURATION_MINUTES,
        "measurement_count": ${#measurements[@]},
        "measurement_interval_seconds": $MEASUREMENT_INTERVAL
    },
    "system_info": {
        "hostname": "$(hostname)",
        "kernel": "$(uname -r)",
        "cpu_cores": $(nproc),
        "total_memory_gb": $(echo "scale=2; $(query_metric "node_memory_MemTotal_bytes") / 1024 / 1024 / 1024" | bc)
    },
    "baseline_averages": {
        "cpu_usage_percent": "calculated_from_measurements",
        "memory_usage_percent": "calculated_from_measurements",
        "disk_io_rate_mbps": "calculated_from_measurements",
        "network_io_rate_mbps": "calculated_from_measurements",
        "load_average": "calculated_from_measurements"
    },
    "measurements": $measurements_json
}
EOF
)
    
    echo "$baseline_report" > "$OUTPUT_FILE"
    success "Baseline report saved to: $OUTPUT_FILE"
}

# Validate baseline data
validate_baseline() {
    log "Validating baseline data..."
    
    # Check if critical metrics are available
    local cpu_check=$(query_metric "node_cpu_seconds_total")
    local memory_check=$(query_metric "node_memory_MemTotal_bytes")
    local disk_check=$(query_metric "node_disk_reads_completed_total")
    
    if [ "$cpu_check" = "null" ]; then
        error "CPU metrics not available from Node Exporter"
        return 1
    fi
    
    if [ "$memory_check" = "null" ]; then
        error "Memory metrics not available from Node Exporter"
        return 1
    fi
    
    if [ "$disk_check" = "null" ]; then
        warn "Disk metrics not available - this may affect IO monitoring"
    fi
    
    success "Baseline validation completed"
}

# Generate baseline summary
generate_summary() {
    log "Generating baseline summary..."
    
    cat <<EOF

=== BASELINE MEASUREMENT SUMMARY ===
Duration: ${DURATION_MINUTES} minutes
Output File: ${OUTPUT_FILE}
Prometheus URL: ${PROMETHEUS_URL}

Key Baseline Metrics:
- CPU Cores: $(nproc)
- Total Memory: $(echo "scale=2; $(query_metric "node_memory_MemTotal_bytes") / 1024 / 1024 / 1024" | bc) GB
- Current Load: $(query_metric "node_load1")
- Memory Usage: $(echo "scale=2; ($(query_metric "node_memory_MemTotal_bytes") - $(query_metric "node_memory_MemAvailable_bytes")) * 100 / $(query_metric "node_memory_MemTotal_bytes")" | bc)%

Next Steps:
1. Review baseline data in ${OUTPUT_FILE}
2. Start long-term performance test
3. Compare future metrics against this baseline
4. Monitor for degradation patterns

EOF
}

# Main execution
main() {
    log "Starting Node Exporter baseline measurement..."
    log "Duration: ${DURATION_MINUTES} minutes"
    log "Output: ${OUTPUT_FILE}"
    
    check_prometheus
    validate_baseline
    collect_baseline_metrics
    generate_summary
    
    success "Baseline measurement completed successfully!"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

## Usage Instructions

### Basic Usage
```bash
# Run 30-minute baseline measurement (default)
./baseline-measurement.sh

# Run custom duration baseline
./baseline-measurement.sh 60  # 60 minutes

# Specify custom output file
./baseline-measurement.sh 30 my-baseline.json
```

### Environment Variables
```bash
# Custom Prometheus URL
export PROMETHEUS_URL="http://prometheus:9090"
./baseline-measurement.sh
```

### Prerequisites
- Prometheus accessible and running
- Node Exporter metrics available
- `jq` and `bc` utilities installed
- `curl` for API queries

## Output Format

The script generates a JSON file containing:

### Baseline Information
- Collection timestamps
- Duration and measurement count
- System information

### System Metrics
- CPU usage patterns
- Memory utilization
- Disk IO rates
- Network IO rates
- Load averages
- Filesystem usage

### Statistical Summary
- Average values for key metrics
- Baseline thresholds for alerting
- System capacity information

## Integration with Performance Tests

### Pre-Test Execution
```bash
# Collect baseline before starting Kafka
./baseline-measurement.sh 30 kafka-baseline.json

# Collect baseline before starting Redpanda
./baseline-measurement.sh 30 redpanda-baseline.json
```

### Comparison Analysis
The baseline data can be used to:
- Set degradation alert thresholds
- Compare performance over time
- Identify system capacity limits
- Validate test environment consistency

## Next Steps

1. Implement the script in the scripts directory
2. Test with current monitoring infrastructure
3. Integrate with long-term performance test scenarios
4. Create automated baseline collection workflows