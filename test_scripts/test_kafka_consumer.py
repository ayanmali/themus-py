#!/usr/bin/env python3
"""
Test script to verify the Kafka consumer setup
"""

import json
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from confluent_kafka import Consumer, KafkaError
from app.messaging.candidate_invitation_kafka_consumer import CandidateInvitationKafkaConsumer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_kafka_connection():
    """Test Kafka connection"""
    try:
        consumer = CandidateInvitationKafkaConsumer()
        consumer.connect()
        logger.info("✅ Successfully connected to Kafka")
        
        # Test topic subscription
        try:
            # Create a test consumer to check topic
            config = {
                'bootstrap.servers': consumer.bootstrap_servers,
                'group.id': f"{consumer.group_id}-test",
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            
            test_consumer = Consumer(config)
            test_consumer.subscribe([consumer.topic])
            
            # Try to get metadata
            metadata = test_consumer.list_topics(timeout=10)
            if consumer.topic in metadata.topics:
                logger.info(f"✅ Topic '{consumer.topic}' exists")
            else:
                logger.error(f"❌ Topic '{consumer.topic}' does not exist")
                return False
            
            test_consumer.close()
            consumer.stop()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to verify topic: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Kafka: {e}")
        return False


def test_message_structure():
    """Test message structure validation"""
    try:
        from app.messaging.candidate_invitation_kafka_consumer import CandidateInvitationMessage
        
        # Create a test message
        test_message = {
            "assessment_id": 123,
            "assessment_name": "Test Assessment",
            "assessment_description": "Test Description",
            "assessment_type": "CODING",
            "assessment_start_date": "2024-01-15T10:00:00",
            "assessment_end_date": "2024-01-15T12:00:00",
            "assessment_duration": 120,
            "candidate": {
                "id": 456,
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com"
            },
            "user_id": 789,
            "user_email": "employer@company.com",
            "invitation_date": "2024-01-10T14:30:00",
            "invitation_id": "test-uuid-123"
        }
        
        # Validate the message
        message = CandidateInvitationMessage(**test_message)
        logger.info("✅ Message structure validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Message structure validation failed: {e}")
        return False


def test_environment_variables():
    """Test required environment variables"""
    import os
    
    required_vars = [
        "KAFKA_BOOTSTRAP_SERVERS"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True


def main():
    """Run all tests"""
    logger.info("Running Kafka consumer tests...")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Kafka Connection", test_kafka_connection),
        ("Message Structure", test_message_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name} passed")
        else:
            logger.error(f"❌ {test_name} failed")
    
    logger.info("\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! The Kafka consumer is ready to use.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the setup.")
        return 1


if __name__ == "__main__":
    exit(main())
