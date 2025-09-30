import json
import logging
from datetime import datetime
import os
from typing import Optional
import signal
import sys
from threading import Event

from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError, KafkaException
from pydantic import BaseModel

from app.data.database import get_db_session
from app.data.schemas.assessments import Assessment
from app.data.schemas.candidates import Candidate

logger = logging.getLogger(__name__)

load_dotenv()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("CANDIDATE_INVITATION_TOPIC_EXCHANGE_NAME")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP")
KAFKA_CLIENT_ID = os.getenv("KAFKA_CLIENT_ID")
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL")
KAFKA_SASL_MECHANISM = os.getenv("KAFKA_SASL_MECHANISM")
KAFKA_SASL_JAAS_CONFIG = os.getenv("KAFKA_SASL_JAAS_CONFIG")
KAFKA_CLIENT_DNS_LOOKUP = os.getenv("KAFKA_CLIENT_DNS_LOOKUP")
KAFKA_SESSION_TIMEOUT_MS = os.getenv("KAFKA_SESSION_TIMEOUT_MS")
KAFKA_ACKS = os.getenv("KAFKA_ACKS")
KAFKA_AUTO_OFFSET_RESET = "earliest"
KAFKA_ENABLE_AUTO_COMMIT = "true"

# Validate required environment variables
if KAFKA_BOOTSTRAP_SERVERS is None:
    raise Exception("KAFKA_BOOTSTRAP_SERVERS is not set in the environment variables")
if KAFKA_TOPIC is None:
    raise Exception("CANDIDATE_INVITATION_TOPIC_EXCHANGE_NAME is not set in the environment variables")
if KAFKA_CONSUMER_GROUP is None:
    raise Exception("KAFKA_GROUP_ID is not set in the environment variables")

class CandidateInvitationMessage(BaseModel):
    assessment_id: int
    assessment_name: str
    assessment_description: Optional[str]
    assessment_type: str
    assessment_start_date: Optional[str]
    assessment_end_date: Optional[str]
    assessment_duration: Optional[int]
    candidate: dict
    user_id: int
    user_email: str
    invitation_date: str
    invitation_id: str


class CandidateInvitationKafkaConsumer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.topic = KAFKA_TOPIC
        self.group_id = KAFKA_CONSUMER_GROUP
        self.client_id = KAFKA_CLIENT_ID
        self.security_protocol = KAFKA_SECURITY_PROTOCOL
        self.sasl_mechanism = KAFKA_SASL_MECHANISM
        self.sasl_jaas_config = KAFKA_SASL_JAAS_CONFIG
        self.client_dns_lookup = KAFKA_CLIENT_DNS_LOOKUP
        self.session_timeout_ms = KAFKA_SESSION_TIMEOUT_MS
        self.acks = KAFKA_ACKS
        self.consumer = None
        self.running = True
        self.shutdown_event = Event()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        self.shutdown_event.set()

    def connect(self):
        """Establish connection to Kafka"""
        try:
            # Kafka consumer configuration
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.group_id,
                'auto.offset.reset': KAFKA_AUTO_OFFSET_RESET,
                'enable.auto.commit': KAFKA_ENABLE_AUTO_COMMIT,
                'session.timeout.ms': 30000,
                'heartbeat.interval.ms': 10000,
                'max.poll.interval.ms': 300000,
                'fetch.min.bytes': 1,
                'fetch.max.wait.ms': 500,
                'client.id': self.client_id,
                'security.protocol': self.security_protocol,
                'sasl.mechanism': self.sasl_mechanism,
                'sasl.jaas.config': self.sasl_jaas_config,
                'client.dns.lookup': self.client_dns_lookup,
                'session.timeout.ms': self.session_timeout_ms,
                'acks': self.acks,
            }
            
            self.consumer = Consumer(config)
            
            # Subscribe to the topic
            self.consumer.subscribe([self.topic])
            
            logger.info(f"Connected to Kafka and subscribed to topic: {self.topic}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def process_message(self, message):
        """Process incoming candidate invitation message"""
        try:
            # Parse the message
            message_data = json.loads(message.value().decode('utf-8'))
            message_obj = CandidateInvitationMessage(**message_data)
            
            logger.info(f"Processing candidate invitation for assessment: {message_obj.assessment_name}")
            
            # Update database
            self.update_database(message_obj)
            
            logger.info(f"Successfully processed candidate invitation: {message_obj.invitation_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
        except Exception as e:
            logger.error(f"Error processing candidate invitation message: {e}")

    def update_database(self, message: CandidateInvitationMessage):
        """Update the database with the candidate invitation information"""
        try:
            with get_db_session() as session:
                # Check if assessment exists, if not create it
                assessment = session.query(Assessment).filter(
                    Assessment.id == message.assessment_id
                ).first()
                
                if not assessment:
                    # Create new assessment
                    assessment = Assessment(
                        id=message.assessment_id,
                        name=message.assessment_name,
                        description=message.assessment_description,
                        assessment_type=message.assessment_type,
                        start_date=datetime.fromisoformat(message.assessment_start_date) if message.assessment_start_date else None,
                        end_date=datetime.fromisoformat(message.assessment_end_date) if message.assessment_end_date else None,
                        duration=message.assessment_duration,
                        user_id=message.user_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(assessment)
                    logger.info(f"Created new assessment: {message.assessment_name}")
                else:
                    # Update existing assessment
                    assessment.name = message.assessment_name
                    assessment.description = message.assessment_description
                    assessment.assessment_type = message.assessment_type
                    assessment.start_date = datetime.fromisoformat(message.assessment_start_date) if message.assessment_start_date else None
                    assessment.end_date = datetime.fromisoformat(message.assessment_end_date) if message.assessment_end_date else None
                    assessment.duration = message.assessment_duration
                    assessment.updated_at = datetime.now()
                    logger.info(f"Updated existing assessment: {message.assessment_name}")

                # Check if user exists, if not create it
                candidate = session.query(Candidate).filter(Candidate.id == message.user_id).first()
                if not candidate:
                    candidate = Candidate(
                        id=message.user_id,
                        email=message.user_email,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(candidate)
                    logger.info(f"Created new candidate: {message.user_email}")

                session.commit()
                logger.info(f"Database updated successfully for invitation: {message.invitation_id}")
                
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            raise

    def start_consuming(self):
        """Start consuming messages from the topic"""
        try:
            logger.info("Starting to consume candidate invitation messages from Kafka...")
            
            while self.running:
                try:
                    # Poll for messages with a timeout
                    msg = self.consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition event - not an error
                            logger.debug(f"Reached end of partition {msg.partition()}")
                            continue
                        else:
                            logger.error(f"Consumer error: {msg.error()}")
                            continue
                    
                    # Process the message
                    self.process_message(msg)
                    
                except KafkaException as e:
                    logger.error(f"Kafka exception: {e}")
                    if self.running:
                        # Wait a bit before retrying
                        self.shutdown_event.wait(5)
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    if self.running:
                        # Wait a bit before retrying
                        self.shutdown_event.wait(5)
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping consumer...")
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the consumer and close connections"""
        self.running = False
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
        logger.info("Consumer stopped")


def main():
    """Main function to run the consumer"""
    if KAFKA_BOOTSTRAP_SERVERS is None:
        raise Exception("KAFKA_BOOTSTRAP_SERVERS is not set in the environment variables")
    
    consumer = CandidateInvitationKafkaConsumer(KAFKA_BOOTSTRAP_SERVERS)
    
    try:
        consumer.connect()
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
