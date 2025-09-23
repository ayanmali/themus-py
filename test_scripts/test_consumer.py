#!/usr/bin/env python3
"""
Test script to verify the candidate invitation consumer setup
"""

import json
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

import pika
from app.messaging.candidate_invitation_consumer import CandidateInvitationConsumer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_connection():
    """Test RabbitMQ connection"""
    try:
        consumer = CandidateInvitationConsumer()
        consumer.connect()
        logger.info("✅ Successfully connected to RabbitMQ")
        
        # Test queue and exchange declaration
        channel = consumer.channel
        
        # Check if exchange exists
        try:
            channel.exchange_declare_passive(consumer.exchange_name)
            logger.info("✅ Exchange exists")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"❌ Exchange does not exist: {e}")
            return False
        
        # Check if queue exists
        try:
            method = channel.queue_declare_passive(consumer.queue_name)
            logger.info(f"✅ Queue exists with {method.method.message_count} messages")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"❌ Queue does not exist: {e}")
            return False
        
        consumer.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
        return False


def test_message_structure():
    """Test message structure validation"""
    try:
        from app.messaging.candidate_invitation_consumer import CandidateInvitationMessage
        
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


def main():
    """Run all tests"""
    logger.info("Running candidate invitation consumer tests...")
    
    tests = [
        ("RabbitMQ Connection", test_connection),
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
        logger.info("🎉 All tests passed! The consumer is ready to use.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the setup.")
        return 1


if __name__ == "__main__":
    exit(main()) 