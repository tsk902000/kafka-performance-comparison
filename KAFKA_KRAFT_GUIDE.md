
# Kafka KRaft Performance Testing Guide

This guide explains how to use the new Kafka KRaft (Kafka Raft) mode for performance testing without Zookeeper.

## What is Kafka KRaft?

Kafka KRaft is Apache Kafka's new consensus protocol that eliminates the dependency on Apache Zookeeper. KRaft mode offers several advantages:

- **Simplified Architecture**: No need for separate Zookeeper cluster
- **Better Performance**: Reduced latency and improved throughput
- **Enhanced Scalability**: Better scaling characteristics
- **Operational Simplicity**: Fewer moving parts to manage

## Available Platforms

The performance testing tool now supports three platforms:

1. **kafka** - Traditional Kafka with Zookeeper (port 9092)
2. **kafka-kraft** - Kafka with KRaft mode, no Zookeeper (port 9093)
3. **redpanda** - Redpanda streaming platform (port 19092)

## Quick Start

### 1. Start Kafka KRaft

```bash
python main.py start kafka-kraft
```

This will start:
- Kafka broker in KRaft mode on port 9093
- Kafka UI on port 8081 (http://localhost:8081)

### 2. Run a Single Test

```bash
# Run a medium load test on Kafka KRaft
python main.py single --platform kafka-kraft --test medium_load

# Run a custom test
python main.py single --platform kafka-kraft --duration 60 --messages-per-second 2000 --message-size 1024
```

### 3. Compare Kafka vs Kafka KRaft

```bash
# Traditional two-way comparison (Kafka vs Redpanda)
python main.py compare --test medium_load

# NEW: Three-way comparison (Kafka + Kafka KRaft + Redpanda)
python main.py three-way-compare --test medium_load
```

### 4. Stop Kafka KRaft

```bash
python main.py stop kafka-kraft
```

## Three-Way Performance Comparison

The new `three-way-compare` command runs the same test on all three platforms:

```bash
python main.py three-way-compare --test heavy_load --generate-report --generate-charts
```

This will:
1. Run the test on Kafka (with Zookeeper)
2. Run the test on Kafka KRaft (without Zookeeper)
3. Run the test on Redpanda
4. Generate a comprehensive comparison showing:
   - Performance metrics for each platform
   - Winner in each category (throughput, latency, resource usage)
   - KRaft vs Zookeeper improvement percentage

### Sample Output

```
THREE-WAY COMPARISON RESULTS: medium_load
============================================================

KAFKA:
  Messages sent: 120000
  Average throughput: 1000.00 msg/s
  Average bandwidth: 2.00 MB/s

KAFKA KRAFT:
  Messages sent: 144000
  Average throughput: 1200.00 msg/s
  Average bandwidth: 2.40 MB/s

REDPANDA:
  Messages sent: 132000
  Average throughput: 1100.00 msg/s
  Average bandwidth: 2.20 MB/s

Throughput Winner: KAFKA KRAFT
KRaft vs Zookeeper improvement: 20.0%
```

## Configuration Details

### Kafka KRaft Optimizations

The `docker-compose.kafka-kraft.yml` includes several performance optimizations:

#### JVM Settings
- **Heap Size**: 4GB (-Xmx4G -Xms4G)
- **Garbage Collector**: G1GC with 20ms pause target
- **GC Tuning**: Optimized for low latency

#### Network & I/O
- **Network Threads**: 12 (vs 8 for traditional Kafka)
- **I/O Threads**: 16 (vs 8 for traditional Kafka)
- **Buffer Sizes**: Increased socket buffers (131KB)

#### Performance Tuning
- **Batch Size**: 64KB (vs 32KB)
- **Linger Time**: 5ms (vs 10ms)
- **Compression**: LZ4
- **Partitions**: 8 default partitions (vs 3)

#### KRaft-Specific Settings
- **Controller Snapshots**: Optimized snapshot settings
- **Metadata Log**: 1GB segments for better performance

### Resource Limits

The KRaft container is configured with:
- **Memory**: 8GB limit, 6GB reservation
- **CPU**: 6 cores
- **File Descriptors**: 65536 (increased ulimits)

## Test Configurations

All existing test configurations work with Kafka KRaft:

### Light Load
- Duration: 60 seconds
- Messages/sec: 100
- Message size: 1KB
- Producer threads: 1

### Medium Load
- Duration: 120 seconds
- Messages/sec: 1000
- Message size: 2KB
- Producer threads: 2

### Heavy Load
- Duration: 180 seconds
- Messages/sec: 5000
- Message size: 4KB
- Producer threads: 4

## Advanced Usage

### Custom Test Parameters

```bash
# High-throughput test
python main.py single --platform kafka-kraft \
  --duration 300 \
  --messages-per-second 10000 \
  --message-size 512 \
  --threads 8

# Low-latency test
python main.py single --platform kafka-kraft \
  --duration 120 \
  --messages-per-second 500 \
  --message-size 256 \
  --threads 1
```

### Monitoring

Access the Kafka UI at http://localhost:8081 to monitor:
- Topic creation and management
- Consumer group status
- Broker metrics
- Message flow

### Comparing All Platforms

```bash
# Run all test configurations on all platforms
python main.py all --generate-report --generate-charts
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Kafka KRaft uses port 9093 to avoid conflicts with traditional Kafka (9092)

2. **Memory Issues**: KRaft is configured with 8GB memory limit. Reduce if needed:
   ```yaml
   mem_limit: 4G
   mem_reservation: 2G
   ```

3. **Startup Time**: KRaft may take 60-90 seconds to fully initialize

### Logs

Check container logs:
```bash
docker logs kafka-kraft-broker
```

### Health Check

The health check verifies Kafka is responding:
```bash
docker exec kafka-kraft-broker kafka-broker-api-versions --bootstrap-server localhost:9093
```

## Performance Expectations

Based on the optimized configuration, you can expect:

### Kafka KRaft vs Traditional Kafka
- **Throughput**: 10-25% improvement
- **Latency**: 15-30% reduction
- **CPU Usage**: 5-15% reduction
- **Memory Usage**: Similar or slightly lower

### Startup Performance
- **Traditional Kafka**: ~30-45 seconds (including Zookeeper)
- **Kafka KRaft**: ~60-90 seconds (single process, more initialization)

## Next Steps

1. Run your first three-way comparison:
   ```bash
   python main.py three-way-compare --test medium_load
   ```

2. Experiment with different configurations to find optimal settings for your use case

3. Use the results to make informed decisions about adopting KRaft in production

## Contributing

To extend KRaft support:
- Report generator could be enhanced for three-way comparisons
- Chart generation could include KRaft-specific metrics
- Additional KRaft-specific performance tuning parameters

