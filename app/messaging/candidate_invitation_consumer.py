import json
import logging
from datetime import datetime
import os
from typing import Optional

from dotenv import load_dotenv
import pika
from pydantic import BaseModel

from app.data.database import get_db_session
from app.data.schemas.assessments import Assessment
from app.data.schemas.candidates import Candidate

logger = logging.getLogger(__name__)

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
CANDIDATE_INVITATION_QUEUE = os.getenv("CANDIDATE_INVITATION_QUEUE")
CANDIDATE_INVITATION_EXCHANGE = os.getenv("CANDIDATE_INVITATION_EXCHANGE")
CANDIDATE_INVITATION_ROUTING_KEY = os.getenv("CANDIDATE_INVITATION_ROUTING_KEY")

if RABBITMQ_URL is None:
    raise Exception("RABBITMQ_URL is not set in the environment variables")
if CANDIDATE_INVITATION_QUEUE is None:
    raise Exception("CANDIDATE_INVITATION_QUEUE is not set in the environment variables")
if CANDIDATE_INVITATION_EXCHANGE is None:
    raise Exception("CANDIDATE_INVITATION_EXCHANGE is not set in the environment variables")
if CANDIDATE_INVITATION_ROUTING_KEY is None:
    raise Exception("CANDIDATE_INVITATION_ROUTING_KEY is not set in the environment variables")

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


class CandidateInvitationConsumer:
    def __init__(self, rabbitmq_url: str = RABBITMQ_URL):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.exchange_name = "candidate.invitation.topic"
        self.queue_name = "candidate.invitation.queue"
        self.routing_key = "topic.candidate.invitation"

    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            # TODO: use async connection
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            
            # Declare exchange and queue
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key=self.routing_key
            )
            
            logger.info(f"Connected to RabbitMQ and bound to queue: {self.queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def process_message(self, ch, method, properties, body):
        """Process incoming candidate invitation message"""
        try:
            # Parse the message
            message_data = json.loads(body.decode('utf-8'))
            message = CandidateInvitationMessage(**message_data)
            
            logger.info(f"Processing candidate invitation for assessment: {message.assessment_name}")
            
            # Update database
            self.update_database(message)
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.info(f"Successfully processed candidate invitation: {message.invitation_id}")
            
        except Exception as e:
            logger.error(f"Error processing candidate invitation message: {e}")
            # Reject the message and requeue it
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

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
                    assessment.updated_at = datetime.utcnow()
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
        """Start consuming messages from the queue"""
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message
            )
            
            logger.info("Starting to consume candidate invitation messages...")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop()
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            self.stop()

    def stop(self):
        """Stop the consumer and close connections"""
        if self.channel:
            self.channel.stop_consuming()
        if self.connection:
            self.connection.close()
        logger.info("Consumer stopped")


def main():
    """Main function to run the consumer"""
    if RABBITMQ_URL is None:
        raise Exception("RABBITMQ_URL is not set in the environment variables")
    
    consumer = CandidateInvitationConsumer(RABBITMQ_URL)
    
    try:
        consumer.connect()
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")

if __name__ == "__main__":
    main() 