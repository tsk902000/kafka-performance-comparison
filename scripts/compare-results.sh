#!/bin/bash

# Results Comparison Script
# This script compares performance results between Apache Kafka, Confluent Kafka, and Redpanda

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Configuration
KAFKA_RESULTS_DIR=""
REDPANDA_RESULTS_DIR=""
COMPARISON_MODE=${1:-"auto"}

# Find latest results
find_latest_results() {
    log "Finding latest test results..."
    
    # Find latest Kafka results
    KAFKA_RESULTS_DIR=$(find results -name "*kafka*" -type d | sort | tail -1)
    if [ -z "$KAFKA_RESULTS_DIR" ]; then
        warn "No Kafka results found. Run: ./scripts/test-kafka-only.sh"
    else
        info "Latest Kafka results: $KAFKA_RESULTS_DIR"
    fi
    
    # Find latest Redpanda results
    REDPANDA_RESULTS_DIR=$(find results -name "*redpanda*" -type d | sort | tail -1)
    if [ -z "$REDPANDA_RESULTS_DIR" ]; then
        warn "No Redpanda results found. Run: ./scripts/test-redpanda-only.sh"
    else
        info "Latest Redpanda results: $REDPANDA_RESULTS_DIR"
    fi
}

# Extract performance metrics from results
extract_kafka_metrics() {
    local results_dir="$1"
    local producer_file="$results_dir/producer-results.txt"
    local consumer_file="$results_dir/consumer-results.txt"
    
    if [ -f "$producer_file" ]; then
        # Extract producer metrics (last line typically contains summary)
        KAFKA_PRODUCER_THROUGHPUT=$(tail -1 "$producer_file" | grep -oE '[0-9]+\.[0-9]+ records/sec' | head -1 || echo "N/A")
        KAFKA_PRODUCER_MBPS=$(tail -1 "$producer_file" | grep -oE '[0-9]+\.[0-9]+ MB/sec' | head -1 || echo "N/A")
        KAFKA_PRODUCER_LATENCY=$(tail -1 "$producer_file" | grep -oE 'avg latency [0-9]+\.[0-9]+ ms' | head -1 || echo "N/A")
    else
        KAFKA_PRODUCER_THROUGHPUT="N/A"
        KAFKA_PRODUCER_MBPS="N/A"
        KAFKA_PRODUCER_LATENCY="N/A"
    fi
    
    if [ -f "$consumer_file" ]; then
        # Extract consumer metrics
        KAFKA_CONSUMER_THROUGHPUT=$(tail -1 "$consumer_file" | grep -oE '[0-9]+\.[0-9]+ MB/sec' | head -1 || echo "N/A")
        KAFKA_CONSUMER_RECORDS=$(tail -1 "$consumer_file" | grep -oE '[0-9]+ records consumed' | head -1 || echo "N/A")
    else
        KAFKA_CONSUMER_THROUGHPUT="N/A"
        KAFKA_CONSUMER_RECORDS="N/A"
    fi
}

# Extract performance metrics from Redpanda results
extract_redpanda_metrics() {
    local results_dir="$1"
    local producer_file="$results_dir/producer-results.txt"
    local consumer_file="$results_dir/consumer-results.txt"
    
    if [ -f "$producer_file" ]; then
        # Extract producer metrics
        REDPANDA_PRODUCER_THROUGHPUT=$(tail -1 "$producer_file" | grep -oE '[0-9]+\.[0-9]+ records/sec' | head -1 || echo "N/A")
        REDPANDA_PRODUCER_MBPS=$(tail -1 "$producer_file" | grep -oE '[0-9]+\.[0-9]+ MB/sec' | head -1 || echo "N/A")
        REDPANDA_PRODUCER_LATENCY=$(tail -1 "$producer_file" | grep -oE 'avg latency [0-9]+\.[0-9]+ ms' | head -1 || echo "N/A")
    else
        REDPANDA_PRODUCER_THROUGHPUT="N/A"
        REDPANDA_PRODUCER_MBPS="N/A"
        REDPANDA_PRODUCER_LATENCY="N/A"
    fi
    
    if [ -f "$consumer_file" ]; then
        # Extract consumer metrics
        REDPANDA_CONSUMER_THROUGHPUT=$(tail -1 "$consumer_file" | grep -oE '[0-9]+\.[0-9]+ MB/sec' | head -1 || echo "N/A")
        REDPANDA_CONSUMER_RECORDS=$(tail -1 "$consumer_file" | grep -oE '[0-9]+ records consumed' | head -1 || echo "N/A")
    else
        REDPANDA_CONSUMER_THROUGHPUT="N/A"
        REDPANDA_CONSUMER_RECORDS="N/A"
    fi
}

# Calculate performance differences
calculate_differences() {
    log "Calculating performance differences..."
    
    # Extract numeric values for comparison
    KAFKA_PROD_NUM=$(echo "$KAFKA_PRODUCER_THROUGHPUT" | grep -oE '[0-9]+\.[0-9]+' || echo "0")
    REDPANDA_PROD_NUM=$(echo "$REDPANDA_PRODUCER_THROUGHPUT" | grep -oE '[0-9]+\.[0-9]+' || echo "0")
    
    if [ "$KAFKA_PROD_NUM" != "0" ] && [ "$REDPANDA_PROD_NUM" != "0" ]; then
        THROUGHPUT_DIFF=$(echo "scale=2; ($REDPANDA_PROD_NUM - $KAFKA_PROD_NUM) / $KAFKA_PROD_NUM * 100" | bc -l 2>/dev/null || echo "N/A")
        if [ "$THROUGHPUT_DIFF" != "N/A" ]; then
            THROUGHPUT_DIFF="${THROUGHPUT_DIFF}%"
        fi
    else
        THROUGHPUT_DIFF="N/A"
    fi
}

# Generate comparison report
generate_comparison_report() {
    log "Generating performance comparison report..."
    
    local report_file="results/performance-comparison-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" <<EOF
# Kafka vs Redpanda Performance Comparison Report

**Generated:** $(date)
**Kafka Results:** $KAFKA_RESULTS_DIR
**Redpanda Results:** $REDPANDA_RESULTS_DIR

## Executive Summary

This report compares the performance characteristics between Apache Kafka and Redpanda based on recent test results.

## Performance Metrics Comparison

### Producer Performance

| Metric | Kafka | Redpanda | Difference |
|--------|-------|----------|------------|
| **Throughput** | $KAFKA_PRODUCER_THROUGHPUT | $REDPANDA_PRODUCER_THROUGHPUT | $THROUGHPUT_DIFF |
| **Bandwidth** | $KAFKA_PRODUCER_MBPS | $REDPANDA_PRODUCER_MBPS | - |
| **Latency** | $KAFKA_PRODUCER_LATENCY | $REDPANDA_PRODUCER_LATENCY | - |

### Consumer Performance

| Metric | Kafka | Redpanda | Difference |
|--------|-------|----------|------------|
| **Throughput** | $KAFKA_CONSUMER_THROUGHPUT | $REDPANDA_CONSUMER_THROUGHPUT | - |
| **Records Consumed** | $KAFKA_CONSUMER_RECORDS | $REDPANDA_CONSUMER_RECORDS | - |

## Architecture Differences

### Apache Kafka
- **Language:** Java/Scala
- **Dependencies:** Requires Zookeeper
- **Consensus:** Zookeeper-based coordination
- **JVM:** Garbage collection overhead
- **Maturity:** Highly mature, extensive ecosystem

### Redpanda
- **Language:** C++
- **Dependencies:** No Zookeeper required
- **Consensus:** Raft consensus algorithm
- **Performance:** Vectorized processing, SIMD optimizations
- **Maturity:** Newer, growing ecosystem

## Resource Utilization

Check the monitoring dashboards for detailed resource utilization:

- **Grafana Dashboard:** http://localhost:3000
- **Prometheus Metrics:** http://localhost:9090

### Key Metrics to Monitor
- CPU usage patterns
- Memory consumption
- Disk I/O performance
- Network bandwidth utilization
- Garbage collection impact (Kafka only)

## Test Configuration

Both tests were run with similar configurations:
- **Message Size:** 1024 bytes
- **Partitions:** 6
- **Replication Factor:** 3
- **Batch Size:** 16384
- **Compression:** LZ4

## Recommendations

### Choose Kafka if:
- You need maximum ecosystem compatibility
- You have existing Kafka expertise
- You require specific Kafka ecosystem tools
- You need proven enterprise-grade stability

### Choose Redpanda if:
- You want lower operational complexity (no Zookeeper)
- You need maximum performance per resource unit
- You prefer simpler deployment and management
- You want lower latency characteristics

## Next Steps

1. **Extended Testing:** Run longer duration tests (hours/days)
2. **Load Variation:** Test with different message sizes and patterns
3. **Failure Testing:** Test resilience and recovery scenarios
4. **Cost Analysis:** Compare operational costs and resource efficiency
5. **Specific Use Cases:** Test your actual workload patterns

## Detailed Results

### Kafka Results Directory
\`$KAFKA_RESULTS_DIR\`

### Redpanda Results Directory
\`$REDPANDA_RESULTS_DIR\`

---
*Generated by compare-results.sh*
EOF

    log "Comparison report generated: $report_file"
    
    # Display summary
    echo
    info "Performance Comparison Summary:"
    echo "================================"
    echo "Kafka Producer Throughput:    $KAFKA_PRODUCER_THROUGHPUT"
    echo "Redpanda Producer Throughput: $REDPANDA_PRODUCER_THROUGHPUT"
    if [ "$THROUGHPUT_DIFF" != "N/A" ]; then
        echo "Performance Difference:       $THROUGHPUT_DIFF"
    fi
    echo
    echo "Full report: $report_file"
}

# Run both tests sequentially
run_sequential_tests() {
    log "Running sequential performance tests..."
    
    info "Step 1: Testing Kafka performance..."
    ./scripts/test-kafka-only.sh
    
    info "Step 2: Testing Redpanda performance..."
    ./scripts/test-redpanda-only.sh
    
    info "Step 3: Comparing results..."
    find_latest_results
    
    if [ -n "$KAFKA_RESULTS_DIR" ] && [ -n "$REDPANDA_RESULTS_DIR" ]; then
        extract_kafka_metrics "$KAFKA_RESULTS_DIR"
        extract_redpanda_metrics "$REDPANDA_RESULTS_DIR"
        calculate_differences
        generate_comparison_report
    else
        error "Could not find results from both platforms"
        exit 1
    fi
}

# Display usage information
show_usage() {
    echo "Usage: $0 [mode]"
    echo
    echo "Modes:"
    echo "  auto      - Find and compare latest results (default)"
    echo "  run       - Run both tests sequentially then compare"
    echo "  kafka     - Run only Kafka test"
    echo "  redpanda  - Run only Redpanda test"
    echo "  help      - Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Compare latest results"
    echo "  $0 run               # Run both tests and compare"
    echo "  $0 kafka             # Test only Kafka"
    echo "  $0 redpanda          # Test only Redpanda"
}

# Main execution
main() {
    case "$COMPARISON_MODE" in
        "auto")
            log "Comparing latest available results..."
            find_latest_results
            if [ -n "$KAFKA_RESULTS_DIR" ] && [ -n "$REDPANDA_RESULTS_DIR" ]; then
                extract_kafka_metrics "$KAFKA_RESULTS_DIR"
                extract_redpanda_metrics "$REDPANDA_RESULTS_DIR"
                calculate_differences
                generate_comparison_report
            else
                warn "Missing results. Run tests first:"
                echo "  ./scripts/test-kafka-only.sh"
                echo "  ./scripts/test-redpanda-only.sh"
                echo "  Or run: $0 run"
            fi
            ;;
        "run")
            run_sequential_tests
            ;;
        "kafka")
            log "Running Kafka-only test..."
            ./scripts/test-kafka-only.sh
            ;;
        "redpanda")
            log "Running Redpanda-only test..."
            ./scripts/test-redpanda-only.sh
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            error "Unknown mode: $COMPARISON_MODE"
            show_usage
            exit 1
            ;;
    esac
}

# Create results directory if it doesn't exist
mkdir -p results

# Run main function
main