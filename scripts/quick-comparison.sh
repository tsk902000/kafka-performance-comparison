#!/bin/bash

# Quick Kafka vs Redpanda Performance Comparison Script
# This script runs a basic performance comparison between Kafka and Redpanda

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
TEST_DURATION=${TEST_DURATION:-"5m"}
MESSAGE_SIZE=${MESSAGE_SIZE:-1024}
TARGET_THROUGHPUT=${TARGET_THROUGHPUT:-10000}
TOPIC_NAME="performance-test-$(date +%s)"
PARTITIONS=6
REPLICATION_FACTOR=3

# Check if monitoring is running
check_monitoring() {
    log "Checking monitoring stack..."
    
    if ! curl -s http://localhost:9090/api/v1/status/config > /dev/null; then
        error "Prometheus is not running. Please start monitoring stack first:"
        echo "  docker-compose -f docker/monitoring/docker-compose.yml up -d"
        exit 1
    fi
    
    if ! curl -s http://localhost:3000/api/health > /dev/null; then
        warn "Grafana may not be ready. Dashboard access might be limited."
    fi
    
    log "Monitoring stack is running."
}

# Start Kafka environment
start_kafka() {
    log "Starting Kafka environment..."
    
    cd docker/kafka
    docker-compose up -d
    cd ../..
    
    # Wait for Kafka to be ready
    info "Waiting for Kafka brokers to be ready..."
    sleep 60
    
    # Check if Kafka is ready
    for i in {1..30}; do
        if docker exec kafka-broker-1 kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; then
            log "Kafka is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Kafka failed to start within timeout"
            exit 1
        fi
        sleep 5
    done
}

# Start Redpanda environment
start_redpanda() {
    log "Starting Redpanda environment..."
    
    cd docker/redpanda
    docker-compose up -d
    cd ../..
    
    # Wait for Redpanda to be ready
    info "Waiting for Redpanda brokers to be ready..."
    sleep 60
    
    # Check if Redpanda is ready
    for i in {1..30}; do
        if docker exec redpanda-1 rpk cluster health &>/dev/null; then
            log "Redpanda is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Redpanda failed to start within timeout"
            exit 1
        fi
        sleep 5
    done
}

# Create test topics
create_topics() {
    log "Creating test topics..."
    
    # Create Kafka topic
    info "Creating Kafka topic: ${TOPIC_NAME}"
    docker exec kafka-broker-1 kafka-topics \
        --create \
        --topic "${TOPIC_NAME}" \
        --partitions ${PARTITIONS} \
        --replication-factor ${REPLICATION_FACTOR} \
        --bootstrap-server localhost:9092 \
        --config min.insync.replicas=2
    
    # Create Redpanda topic
    info "Creating Redpanda topic: ${TOPIC_NAME}"
    docker exec redpanda-1 rpk topic create "${TOPIC_NAME}" \
        --partitions ${PARTITIONS} \
        --replicas ${REPLICATION_FACTOR}
}

# Run Kafka performance test
test_kafka() {
    log "Running Kafka performance test..."
    
    local results_dir="results/kafka-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Producer test
    info "Starting Kafka producer test..."
    docker exec kafka-broker-1 kafka-producer-perf-test \
        --topic "${TOPIC_NAME}" \
        --num-records 100000 \
        --record-size ${MESSAGE_SIZE} \
        --throughput ${TARGET_THROUGHPUT} \
        --producer-props bootstrap.servers=localhost:9092 \
                          acks=1 \
                          batch.size=16384 \
                          linger.ms=5 \
                          compression.type=lz4 \
        > "${results_dir}/producer-results.txt" &
    
    local producer_pid=$!
    
    # Consumer test
    info "Starting Kafka consumer test..."
    timeout ${TEST_DURATION} docker exec kafka-broker-1 kafka-consumer-perf-test \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --messages 100000 \
        --group "perf-test-group-kafka" \
        > "${results_dir}/consumer-results.txt" &
    
    local consumer_pid=$!
    
    # Wait for tests to complete
    wait $producer_pid $consumer_pid 2>/dev/null || true
    
    log "Kafka performance test completed. Results saved to: ${results_dir}"
}

# Run Redpanda performance test
test_redpanda() {
    log "Running Redpanda performance test..."
    
    local results_dir="results/redpanda-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Producer test using rpk
    info "Starting Redpanda producer test..."
    docker exec redpanda-1 rpk topic produce "${TOPIC_NAME}" \
        --brokers localhost:9092 \
        --key-delimiter ":" \
        --partition-count ${PARTITIONS} \
        > "${results_dir}/producer-results.txt" &
    
    local producer_pid=$!
    
    # Consumer test using rpk
    info "Starting Redpanda consumer test..."
    timeout ${TEST_DURATION} docker exec redpanda-1 rpk topic consume "${TOPIC_NAME}" \
        --brokers localhost:9092 \
        --group "perf-test-group-redpanda" \
        --offset start \
        > "${results_dir}/consumer-results.txt" &
    
    local consumer_pid=$!
    
    # Wait for tests to complete
    wait $producer_pid $consumer_pid 2>/dev/null || true
    
    log "Redpanda performance test completed. Results saved to: ${results_dir}"
}

# Generate comparison report
generate_report() {
    log "Generating comparison report..."
    
    local report_file="results/comparison-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "${report_file}" <<EOF
# Kafka vs Redpanda Performance Comparison Report

**Test Date:** $(date)
**Test Duration:** ${TEST_DURATION}
**Message Size:** ${MESSAGE_SIZE} bytes
**Target Throughput:** ${TARGET_THROUGHPUT} messages/sec
**Topic Partitions:** ${PARTITIONS}
**Replication Factor:** ${REPLICATION_FACTOR}

## Test Configuration

- **Kafka Version:** confluentinc/cp-kafka:7.4.0
- **Redpanda Version:** redpandadata/redpanda:v23.2.15
- **Test Topic:** ${TOPIC_NAME}

## Results Summary

### Kafka Results
\`\`\`
$(find results -name "*kafka*" -path "*/producer-results.txt" -exec cat {} \; 2>/dev/null | tail -1 || echo "No Kafka producer results found")
\`\`\`

### Redpanda Results
\`\`\`
$(find results -name "*redpanda*" -path "*/producer-results.txt" -exec cat {} \; 2>/dev/null | tail -1 || echo "No Redpanda producer results found")
\`\`\`

## Monitoring Data

- **Grafana Dashboard:** http://localhost:3000
- **Prometheus Metrics:** http://localhost:9090
- **Kafka UI:** http://localhost:8081
- **Redpanda Console:** http://localhost:8082

## Next Steps

1. Review detailed metrics in Grafana dashboards
2. Analyze resource utilization patterns
3. Run extended tests with different configurations
4. Compare latency percentiles and error rates

---
*Generated by quick-comparison.sh*
EOF

    log "Comparison report generated: ${report_file}"
}

# Cleanup function
cleanup() {
    log "Cleaning up test resources..."
    
    # Delete test topics
    docker exec kafka-broker-1 kafka-topics --delete --topic "${TOPIC_NAME}" --bootstrap-server localhost:9092 2>/dev/null || true
    docker exec redpanda-1 rpk topic delete "${TOPIC_NAME}" 2>/dev/null || true
    
    log "Cleanup completed."
}

# Display access information
display_access_info() {
    log "Quick comparison completed!"
    echo
    info "Access your results:"
    echo "- Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    echo "- Prometheus Metrics: http://localhost:9090"
    echo "- Kafka UI: http://localhost:8081"
    echo "- Redpanda Console: http://localhost:8082"
    echo "- Results Directory: results/"
    echo
    info "To stop environments:"
    echo "- Stop Kafka: docker-compose -f docker/kafka/docker-compose.yml down"
    echo "- Stop Redpanda: docker-compose -f docker/redpanda/docker-compose.yml down"
    echo "- Stop Monitoring: docker-compose -f docker/monitoring/docker-compose.yml down"
}

# Main execution
main() {
    log "Starting quick Kafka vs Redpanda comparison..."
    
    # Create results directory
    mkdir -p results
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    check_monitoring
    start_kafka
    start_redpanda
    create_topics
    
    # Run tests in parallel
    test_kafka &
    test_redpanda &
    
    # Wait for both tests to complete
    wait
    
    generate_report
    display_access_info
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --duration DURATION Set test duration (default: 5m)"
        echo "  --throughput NUM    Set target throughput (default: 10000)"
        echo "  --message-size SIZE Set message size in bytes (default: 1024)"
        echo
        echo "Environment variables:"
        echo "  TEST_DURATION       Test duration (default: 5m)"
        echo "  MESSAGE_SIZE        Message size in bytes (default: 1024)"
        echo "  TARGET_THROUGHPUT   Target throughput (default: 10000)"
        exit 0
        ;;
    --duration)
        TEST_DURATION="$2"
        shift 2
        ;;
    --throughput)
        TARGET_THROUGHPUT="$2"
        shift 2
        ;;
    --message-size)
        MESSAGE_SIZE="$2"
        shift 2
        ;;
esac

# Run main function
main "$@"