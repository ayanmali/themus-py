# RabbitMQ to Kafka Migration Guide

This guide explains how to migrate your Python service from RabbitMQ to Apache Kafka.

## Overview

The migration involves replacing the RabbitMQ consumer with a Kafka consumer while maintaining the same message processing logic and database operations.

## Key Changes

### 1. Dependencies

**Before (RabbitMQ):**
```toml
pika>=1.3.2
```

**After (Kafka):**
```toml
confluent-kafka>=2.3.0
```

### 2. Environment Variables

**Before (RabbitMQ):**
```bash
RABBITMQ_URL=amqp://user:password@localhost:5672/
CANDIDATE_INVITATION_QUEUE=candidate.invitation.queue
CANDIDATE_INVITATION_EXCHANGE=candidate.invitation.topic
CANDIDATE_INVITATION_ROUTING_KEY=topic.candidate.invitation
```

**After (Kafka):**
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=candidate-invitation
KAFKA_GROUP_ID=candidate-invitation-consumer
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ENABLE_AUTO_COMMIT=true
```

### 3. Consumer Implementation

**Before (RabbitMQ with Pika):**
- Uses `pika.BlockingConnection`
- Declares exchanges and queues
- Binds queues to exchanges with routing keys
- Uses `basic_consume` with callback functions

**After (Kafka with confluent-kafka):**
- Uses `confluent_kafka.Consumer`
- Subscribes to topics directly
- Uses polling mechanism for message consumption
- Handles partition assignment automatically

## Migration Steps

### Step 1: Install Dependencies

```bash
# Install the new Kafka dependency
pip install confluent-kafka>=2.3.0

# Or update your pyproject.toml and run:
pip install -e .
```

### Step 2: Update Environment Variables

Create a new `.env` file or update your existing one:

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=candidate-invitation
KAFKA_GROUP_ID=candidate-invitation-consumer
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ENABLE_AUTO_COMMIT=true
```

### Step 3: Update Your Application

Replace the RabbitMQ consumer with the Kafka consumer:

```python
# Old import
from app.messaging.candidate_invitation_consumer import CandidateInvitationConsumer

# New import
from app.messaging.candidate_invitation_kafka_consumer import CandidateInvitationKafkaConsumer
```

### Step 4: Update Consumer Initialization

```python
# Old RabbitMQ consumer
consumer = CandidateInvitationConsumer(RABBITMQ_URL)

# New Kafka consumer
consumer = CandidateInvitationKafkaConsumer(KAFKA_BOOTSTRAP_SERVERS)
```

### Step 5: Test the Migration

Run the test script to verify everything works:

```bash
python test_scripts/test_kafka_consumer.py
```

### Step 6: Run the Consumer

```bash
python test_scripts/run_kafka_consumer.py
```

## Key Differences

### Message Processing

**RabbitMQ:**
- Messages are processed via callback functions
- Automatic acknowledgment with `basic_ack`
- Manual queue binding and routing

**Kafka:**
- Messages are processed via polling
- Automatic offset management with consumer groups
- Topic-based message routing

### Error Handling

**RabbitMQ:**
- Uses `basic_nack` for message rejection
- Manual requeueing of failed messages

**Kafka:**
- Built-in retry mechanisms
- Automatic offset management
- Consumer group coordination

### Connection Management

**RabbitMQ:**
- Single connection with channels
- Manual connection lifecycle management

**Kafka:**
- Consumer instances with automatic rebalancing
- Built-in connection pooling and failover

## Configuration Options

### Kafka Consumer Configuration

```python
config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'candidate-invitation-consumer',
    'auto.offset.reset': 'earliest',  # or 'latest'
    'enable.auto.commit': True,
    'session.timeout.ms': 30000,
    'heartbeat.interval.ms': 10000,
    'max.poll.interval.ms': 300000,
    'fetch.min.bytes': 1,
    'fetch.max.wait.ms': 500,
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | Required |
| `KAFKA_TOPIC` | Topic name | `candidate-invitation` |
| `KAFKA_GROUP_ID` | Consumer group ID | `candidate-invitation-consumer` |
| `KAFKA_AUTO_OFFSET_RESET` | Offset reset strategy | `earliest` |
| `KAFKA_ENABLE_AUTO_COMMIT` | Enable auto-commit | `true` |

## Testing

### Unit Tests

The test script verifies:
- Environment variable configuration
- Kafka connection and topic existence
- Message structure validation

### Integration Tests

Run the consumer with test messages to verify:
- Message consumption
- Database updates
- Error handling

## Production Considerations

### Performance

- Kafka provides better throughput for high-volume scenarios
- Consumer groups enable horizontal scaling
- Built-in partitioning for parallel processing

### Reliability

- Kafka's distributed architecture provides better fault tolerance
- Automatic offset management prevents message loss
- Consumer group coordination ensures no duplicate processing

### Monitoring

- Use Kafka's built-in metrics for monitoring
- Monitor consumer lag and throughput
- Set up alerts for consumer group health

## Rollback Plan

If you need to rollback to RabbitMQ:

1. Revert the consumer import:
   ```python
   from app.messaging.candidate_invitation_consumer import CandidateInvitationConsumer
   ```

2. Restore RabbitMQ environment variables
3. Update consumer initialization
4. Test the rollback

## Troubleshooting

### Common Issues

1. **Connection Issues:**
   - Verify `KAFKA_BOOTSTRAP_SERVERS` is correct
   - Check network connectivity to Kafka brokers

2. **Topic Not Found:**
   - Ensure the topic exists in Kafka
   - Check topic permissions

3. **Consumer Group Issues:**
   - Verify `KAFKA_GROUP_ID` is unique
   - Check consumer group permissions

4. **Message Processing Errors:**
   - Verify message format matches `CandidateInvitationMessage`
   - Check database connectivity

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('confluent_kafka').setLevel(logging.DEBUG)
```

## Next Steps

1. **Deploy Kafka Infrastructure:**
   - Set up Kafka cluster
   - Configure topics and partitions
   - Set up monitoring

2. **Update Message Producers:**
   - Migrate message producers to use Kafka
   - Update message format if needed

3. **Monitor and Optimize:**
   - Monitor consumer performance
   - Tune configuration for your workload
   - Set up alerting

4. **Remove RabbitMQ Dependencies:**
   - Once migration is complete and stable
   - Remove Pika dependency
   - Clean up RabbitMQ infrastructure
