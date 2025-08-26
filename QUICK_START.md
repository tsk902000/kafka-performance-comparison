
# Quick Start Guide - Kafka vs Redpanda Performance Comparison

This guide gets you up and running with the performance comparison framework in under 5 minutes.

## ✅ Prerequisites Check

Your environment is already configured with:
- ✅ Python 3.12
- ✅ All required dependencies installed
- ✅ confluent-kafka and kafka-python clients
- ✅ Performance monitoring tools

## 🚀 Immediate Testing (No Docker Required)

### 1. Test the Framework

```bash
# Run the local test to verify everything works
python test_local.py
```

This will:
- Test performance monitoring
- Generate sample comparison reports
- Create charts and visualizations
- Verify all components are working

### 2. View Generated Results

```bash
# Check the results directory
ls -la results/

# View the HTML report (contains interactive charts)
# Open results/comparison_report_*.html in a browser
```

## 🐳 Docker Setup for Real Testing

### Option A: Quick Docker Setup (Container Environment)

```bash
# Start Docker daemon
sudo dockerd > /tmp/docker.log 2>&1 &

# Wait for Docker to start
sleep 10

# Verify Docker is working
sudo docker run hello-world
```

### Option B: Full Docker Installation (Ubuntu/Linux)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Test Docker
sudo docker run hello-world
```

## 🏃‍♂️ Run Performance Tests

### Quick Test (5 minutes)

```bash
python main.py compare --test quick --generate-report
```

### Medium Load Test (15 minutes)

```bash
python main.py compare --test medium_load --generate-report
```

### Heavy Load Test (30 minutes)

```bash
python main.py compare --test heavy_load --generate-report
```

## 📊 Understanding Results

### Key Metrics Compared

| Metric | Description | Winner Criteria |
|--------|-------------|-----------------|
| **Producer Throughput** | Messages/second sent | Higher is better |
| **Consumer Throughput** | Messages/second consumed | Higher is better |
| **Latency** | End-to-end message delay | Lower is better |
| **CPU Usage** | System CPU utilization | Lower is better |
| **Memory Usage** | RAM consumption | Lower is better |

### Result Files

```
results/
├── comparison_report_YYYYMMDD_HHMMSS.html    # Interactive web report
├── comparison_report_YYYYMMDD_HHMMSS.json    # Raw comparison data
├── producer_throughput_comparison.png         # Throughput charts
├── consumer_performance_comparison.png        # Consumer performance
└── resource_usage_comparison.png              # System resource usage
```

## 🔧 Customization

### Custom Test Configuration

```bash
# Custom test with specific parameters
python main.py compare \
  --duration 300 \
  --messages 25000 \
  --producers 3 \
  --consumers 2 \
  --message-size 1024 \
  --generate-report
```

### Test Individual Platforms

```bash
# Test only Kafka
python main.py test kafka --test medium_load

# Test only Redpanda
python main.py test redpanda --test medium_load
```

## 🎯 Expected Performance Characteristics

### Typical Results

**Apache Kafka:**
- Higher memory usage
- More CPU intensive
- Mature ecosystem
- Excellent for complex scenarios

**Redpanda:**
- Lower resource usage
- Better single-node performance
- Simpler deployment
- Optimized for speed

### Performance Factors

1. **Message Size**: Larger messages favor Kafka
2. **Concurrency**: High concurrency favors Redpanda
3. **Persistence**: Both handle persistence well
4. **Resource Constraints**: Redpanda better for limited resources

## 🐛 Troubleshooting

### Common Issues

1. **Docker not starting**
   ```bash
   # Check Docker status
   sudo systemctl status docker
   
   # View Docker logs
   cat /tmp/docker.log
   ```

2. **Permission errors**
   ```bash
   # Fix Docker permissions
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Port conflicts**
   ```bash
   # Check what's using ports 9092, 9644
   sudo netstat -tulpn | grep -E ':(9092|9644)'
   ```

4. **Memory issues**
   ```bash
   # Check available memory
   free -h
   
   # Reduce test load
   python main.py compare --test quick --generate-report
   ```

### Getting Help

1. **Check logs**: All test logs are saved in `logs/` directory
2. **View Docker logs**: `docker logs <container_name>`
3. **System resources**: `htop` or `top` to monitor system load

## 📈 Next Steps

1. **Run your first test**: `python test_local.py`
2. **Set up Docker**: Follow Docker setup instructions
3. **Run comparison**: `python main.py compare --test medium_load --generate-report`
4. **Analyze results**: Open the HTML report in your browser
5. **Customize tests**: Adjust parameters for your use case

## 🔗 Additional Resources

- [Full Documentation](README.md)
- [Docker Setup Guide](DOCKER_SETUP.md)
- [Python 3.12 Compatibility](README_PYTHON312.md)

---

**Ready to start?** Run `python test_local.py` now! 🚀

