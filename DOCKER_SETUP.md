
# Docker Setup Guide for Kafka Performance Comparison

This guide helps you set up Docker to run the Kafka vs Redpanda performance comparison tests.

## Prerequisites

- Ubuntu/Linux environment
- Python 3.12+ (already configured)
- Root/sudo access

## Docker Installation and Setup

### 1. Install Docker (if not already installed)

```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2. Start Docker Service

```bash
# Start Docker daemon
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Verify Docker is running
sudo docker run hello-world
```

### 3. Add User to Docker Group (Optional)

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Test without sudo
docker run hello-world
```

## Container Environment Setup

If you're running in a container environment (like this one), Docker requires special setup:

### 1. Start Docker Daemon in Container

```bash
# Start Docker daemon in background
sudo dockerd > /tmp/docker.log 2>&1 &

# Wait for Docker to initialize
sleep 10

# Check if Docker is running
sudo docker ps
```

### 2. Troubleshooting Container Docker Issues

If you encounter permission errors:

```bash
# Check Docker daemon logs
cat /tmp/docker.log

# Try starting with different options
sudo dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2376 > /tmp/docker.log 2>&1 &
```

## Running Performance Tests

### 1. Test Framework (No Docker Required)

```bash
# Test the framework with simulated data
python test_local.py
```

### 2. Run Kafka vs Redpanda Comparison

```bash
# Quick test (5 minutes)
python main.py compare --test quick --generate-report

# Medium load test (15 minutes)
python main.py compare --test medium_load --generate-report

# Heavy load test (30 minutes)
python main.py compare --test heavy_load --generate-report
```

### 3. Individual Platform Tests

```bash
# Test only Kafka
python main.py test kafka --test medium_load

# Test only Redpanda
python main.py test redpanda --test medium_load
```

## Test Configuration

### Available Test Profiles

| Profile | Duration | Messages | Producers | Consumers | Message Size |
|---------|----------|----------|-----------|-----------|--------------|
| quick | 5 min | 10,000 | 2 | 2 | 1KB |
| medium_load | 15 min | 100,000 | 5 | 3 | 1KB |
| heavy_load | 30 min | 500,000 | 10 | 5 | 2KB |

### Custom Configuration

Create a custom test configuration:

```bash
python main.py compare \
  --duration 600 \
  --messages 50000 \
  --producers 3 \
  --consumers 2 \
  --message-size 1024 \
  --generate-report
```

## Performance Metrics Tracked

### Producer Metrics
- **Throughput**: Messages per second
- **Bandwidth**: Megabytes per second
- **Latency**: Message send latency (P50, P95, P99)
- **Error Rate**: Failed message percentage

### Consumer Metrics
- **Throughput**: Messages consumed per second
- **Latency**: End-to-end message latency
- **Lag**: Consumer lag behind producer

### System Metrics
- **CPU Usage**: Average and peak CPU utilization
- **Memory Usage**: RAM consumption
- **Disk I/O**: Read/write operations per second
- **Network I/O**: Network bandwidth utilization

## Output and Reports

### Generated Files

```
results/
├── kafka_metrics_YYYYMMDD_HHMMSS.json
├── redpanda_metrics_YYYYMMDD_HHMMSS.json
├── comparison_report_YYYYMMDD_HHMMSS.html
├── comparison_report_YYYYMMDD_HHMMSS.json
├── producer_throughput_comparison.png
├── consumer_performance_comparison.png
└── resource_usage_comparison.png
```

### Viewing Results

```bash
# View summary in terminal
python main.py report --file results/comparison_report_*.json

# Open HTML report in browser
# The HTML file contains interactive charts and detailed analysis
```

## Docker Compose Alternative

For easier setup, you can use Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'
services:
  kafka-test:
    build: .
    volumes:
      - ./results:/app/results
    command: python main.py compare --test medium_load --generate-report
    
  performance-monitor:
    build: .
    volumes:
      - ./results:/app/results
    command: python -c "from src.performance_monitor import PerformanceMonitor; PerformanceMonitor().monitor_system(duration=900)"
```

```bash
# Run with Docker Compose
docker-compose up
```

## Troubleshooting

### Common Issues

1. **Docker daemon not starting**
   ```bash
   sudo systemctl status docker
   sudo journalctl -u docker.service
   ```

2. **Permission denied errors**
   ```bash
   sudo chown $USER:$USER /var/run/docker.sock
   ```

3. **Container networking issues**
   ```bash
   docker network ls
   docker network create kafka-test-network
   ```

4. **Resource constraints**
   ```bash
   # Check available resources
   free -h
   df -h
   ```

### Performance Optimization

1. **Increase Docker resources**
   ```bash
   # Edit Docker daemon configuration
   sudo nano /etc/docker/daemon.json
   ```
   
   ```json
   {
     "default-ulimits": {
       "nofile": {
         "Name": "nofile",
         "Hard": 64000,
         "Soft": 64000
       }
     }
   }
   ```

2. **Optimize system settings**
   ```bash
   # Increase file descriptor limits
   echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
   echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
   ```

## Next Steps

1. **Run the test framework**: `python test_local.py`
2. **Set up Docker**: Follow the installation steps above
3. **Run performance tests**: `python main.py compare --test medium_load --generate-report`
4. **Analyze results**: Check the generated HTML report and charts

For more detailed information, see the main [README.md](README.md) file.

