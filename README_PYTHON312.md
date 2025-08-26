# Python 3.12 Compatibility Update

This document describes the changes made to support Python 3.12 compatibility in the Kafka Performance Comparison project.

## Changes Made

### 1. Updated Requirements (`requirements.txt`)

- **Added confluent-kafka**: Primary Kafka client with excellent Python 3.12 support
- **Updated version constraints**: Changed from exact versions to minimum versions for better compatibility
- **Added additional dependencies**: `requests` and `urllib3` for better compatibility

### 2. Enhanced Kafka Producer (`src/kafka_producer.py`)

- **Dual client support**: Automatically detects and uses either `confluent-kafka` or `kafka-python`
- **Improved error handling**: Better exception handling for both client types
- **Performance optimizations**: Uses confluent-kafka when available for better performance

### 3. Enhanced Kafka Consumer (`src/kafka_consumer.py`)

- **Dual client support**: Compatible with both Kafka client libraries
- **Message processing**: Handles different message formats from both clients
- **Latency calculations**: Works correctly with both client types

## Library Comparison

### confluent-kafka vs kafka-python

| Feature | confluent-kafka | kafka-python |
|---------|----------------|--------------|
| Python 3.12 Support | ✅ Full | ⚠️ Limited |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Memory Usage | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Maintenance | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Features | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## Installation

The project now automatically installs both libraries:

```bash
pip install -r requirements.txt
```

## Usage

The framework automatically detects which Kafka client is available and uses the best one:

1. **confluent-kafka** (preferred) - Better performance and Python 3.12 support
2. **kafka-python** (fallback) - Maintains backward compatibility

## Testing

All existing functionality works with both clients:

```bash
# Test the framework
python test_local.py

# Run performance comparison
python main.py compare --test medium_load --generate-report
```

## Benefits of Python 3.12 Support

1. **Better Performance**: Python 3.12 offers significant performance improvements
2. **Modern Features**: Access to latest Python language features
3. **Security**: Latest security patches and improvements
4. **Future-proofing**: Ensures long-term compatibility

## Migration Notes

- **No breaking changes**: Existing configurations and scripts work unchanged
- **Automatic detection**: Framework chooses the best available client
- **Fallback support**: Still works with older Python versions and kafka-python only

## Troubleshooting

If you encounter issues:

1. **Check Python version**: `python --version`
2. **Verify installations**: `pip list | grep kafka`
3. **Test imports**: `python -c "import confluent_kafka; print('OK')"`

For more details, see the main [README.md](README.md) file.
