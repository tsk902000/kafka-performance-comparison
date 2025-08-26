# Decision Log

This file records architectural and implementation decisions using a list format.
2025-08-26 13:42:37 - Initial decision log creation.

## Decision

* Use Docker containerization for both Kafka and Redpanda deployments

## Rationale 

* Ensures consistent testing environments across different systems
* Simplifies deployment and configuration management
* Enables easy scaling and resource control for performance testing
* Provides isolation between different test scenarios

## Implementation Details

* Docker Compose will be used for orchestrating multi-container setups
* Separate configurations for Kafka and Redpanda environments
* Standardized base images and versions for reproducible results
2025-08-26 13:12:05 - Added pure Apache Kafka testing capability alongside Confluent Kafka

## Decision

* Added separate Apache Kafka Docker environment and testing script
* Maintained existing Confluent Kafka setup for comparison
* Updated comparison script to handle three platforms: Apache Kafka, Confluent Kafka, and Redpanda

## Rationale 

* User requested pure Apache Kafka testing to distinguish from Confluent Kafka
* Apache Kafka 3.7.0 with KRaft mode (no Zookeeper) provides authentic Apache experience
* Enables comparison between official Apache distribution vs Confluent's enhanced distribution
* Provides comprehensive platform comparison across all major messaging solutions

## Implementation Details

* Apache Kafka uses official apache/kafka:3.7.0 image
* KRaft mode eliminates Zookeeper dependency
* Native Apache Kafka performance tools (kafka-producer-perf-test.sh, kafka-consumer-perf-test.sh)
* Separate UI on port 8083 to avoid conflicts
* Updated comparison script with apache-kafka option
* Enhanced README with platform comparison table
