"""
Kafka-based message queue system for LMS.
Handles real-time events, notifications, and async processing.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Callable, List
from datetime import datetime, timezone
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import redis
from config import settings

logger = logging.getLogger(__name__)

class MessageQueue:
    """Kafka-based message queue for LMS events."""

    def __init__(self):
        self.producer = None
        self.consumer = None
        self.redis_client = None
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.running = False

    async def initialize(self):
        """Initialize Kafka producer and consumer."""
        try:
            # Initialize Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers or ['localhost:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )

            # Initialize Redis for message deduplication and caching
            self.redis_client = redis.Redis(
                host=settings.redis_host or 'localhost',
                port=settings.redis_port or 6379,
                db=1,  # Use DB 1 for message queue
                decode_responses=True
            )

            logger.info("Message queue initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize message queue: {e}")
            raise

    async def publish_event(self, topic: str, event_type: str, data: Dict[str, Any],
                          key: str = None, headers: Dict[str, str] = None) -> bool:
        """
        Publish event to Kafka topic.

        Args:
            topic: Kafka topic name
            event_type: Type of event (user_action, course_update, etc.)
            data: Event data payload
            key: Message key for partitioning
            headers: Message headers

        Returns:
            bool: Success status
        """
        try:
            # Create event message
            message = {
                'event_id': f"{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                'event_type': event_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': data,
                'version': '1.0'
            }

            # Add headers
            kafka_headers = []
            if headers:
                kafka_headers.extend([(k, v.encode('utf-8')) for k, v in headers.items()])

            # Publish to Kafka
            future = self.producer.send(
                topic=topic,
                key=key,
                value=message,
                headers=kafka_headers
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)

            logger.info(f"Event published: {event_type} to topic {topic}, partition {record_metadata.partition}, offset {record_metadata.offset}")

            # Cache event for deduplication
            if self.redis_client:
                cache_key = f"event:{message['event_id']}"
                self.redis_client.setex(cache_key, 3600, json.dumps(message))  # Cache for 1 hour

            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    async def start_consumer(self, topics: List[str], group_id: str = 'lms_consumer_group'):
        """Start Kafka consumer to process events."""
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=settings.kafka_bootstrap_servers or ['localhost:9092'],
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000
            )

            self.running = True
            logger.info(f"Started Kafka consumer for topics: {topics}")

            # Start consuming messages
            await self._consume_messages()

        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            raise

    async def _consume_messages(self):
        """Consume and process messages from Kafka."""
        try:
            while self.running:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000, max_records=10)

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            await self._process_message(message)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            # Continue processing other messages

        except Exception as e:
            logger.error(f"Error in message consumption: {e}")
        finally:
            if self.consumer:
                self.consumer.close()

    async def _process_message(self, message):
        """Process individual Kafka message."""
        try:
            event_data = message.value
            event_type = event_data.get('event_type')

            logger.info(f"Processing event: {event_type}")

            # Check for duplicate events
            if self.redis_client:
                event_id = event_data.get('event_id')
                cache_key = f"processed:{event_id}"
                if self.redis_client.exists(cache_key):
                    logger.info(f"Skipping duplicate event: {event_id}")
                    return

                # Mark as processed
                self.redis_client.setex(cache_key, 3600, '1')  # Cache for 1 hour

            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(event_data)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {e}")

            # Handle specific event types
            await self._handle_specific_event(event_type, event_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_specific_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle specific event types with custom logic."""
        try:
            if event_type == 'user_registered':
                await self._handle_user_registration(event_data)
            elif event_type == 'course_completed':
                await self._handle_course_completion(event_data)
            elif event_type == 'assignment_submitted':
                await self._handle_assignment_submission(event_data)
            elif event_type == 'ai_generation_requested':
                await self._handle_ai_generation_request(event_data)
            elif event_type == 'notification_sent':
                await self._handle_notification_event(event_data)

        except Exception as e:
            logger.error(f"Error handling specific event {event_type}: {e}")

    async def _handle_user_registration(self, event_data: Dict[str, Any]):
        """Handle user registration events."""
        user_id = event_data['data'].get('user_id')

        # Publish welcome notification event
        await self.publish_event(
            topic='notifications',
            event_type='welcome_notification',
            data={
                'user_id': user_id,
                'type': 'welcome',
                'message': 'Welcome to the LMS platform!'
            }
        )

        # Trigger onboarding process
        await self.publish_event(
            topic='user_onboarding',
            event_type='start_onboarding',
            data={'user_id': user_id}
        )

    async def _handle_course_completion(self, event_data: Dict[str, Any]):
        """Handle course completion events."""
        user_id = event_data['data'].get('user_id')
        course_id = event_data['data'].get('course_id')

        # Generate certificate
        await self.publish_event(
            topic='certificates',
            event_type='generate_certificate',
            data={
                'user_id': user_id,
                'course_id': course_id
            }
        )

        # Send completion notification
        await self.publish_event(
            topic='notifications',
            event_type='course_completion_notification',
            data={
                'user_id': user_id,
                'course_id': course_id,
                'type': 'achievement',
                'message': 'Congratulations on completing the course!'
            }
        )

        # Update user progress analytics
        await self.publish_event(
            topic='analytics',
            event_type='update_user_progress',
            data={
                'user_id': user_id,
                'course_id': course_id,
                'action': 'completed'
            }
        )

    async def _handle_assignment_submission(self, event_data: Dict[str, Any]):
        """Handle assignment submission events."""
        submission_id = event_data['data'].get('submission_id')
        user_id = event_data['data'].get('user_id')
        assignment_id = event_data['data'].get('assignment_id')

        # Trigger AI grading
        await self.publish_event(
            topic='ai_processing',
            event_type='grade_submission',
            data={
                'submission_id': submission_id,
                'user_id': user_id,
                'assignment_id': assignment_id
            }
        )

        # Check for plagiarism
        await self.publish_event(
            topic='ai_processing',
            event_type='check_plagiarism',
            data={
                'submission_id': submission_id,
                'user_id': user_id
            }
        )

    async def _handle_ai_generation_request(self, event_data: Dict[str, Any]):
        """Handle AI generation requests."""
        request_type = event_data['data'].get('type')
        user_id = event_data['data'].get('user_id')

        if request_type == 'course':
            # Trigger course generation
            await self.publish_event(
                topic='ai_processing',
                event_type='generate_course',
                data=event_data['data']
            )
        elif request_type == 'content':
            # Trigger content enhancement
            await self.publish_event(
                topic='ai_processing',
                event_type='enhance_content',
                data=event_data['data']
            )

    async def _handle_notification_event(self, event_data: Dict[str, Any]):
        """Handle notification events."""
        # Log notification for analytics
        await self.publish_event(
            topic='analytics',
            event_type='notification_sent',
            data={
                'notification_id': event_data['data'].get('notification_id'),
                'user_id': event_data['data'].get('user_id'),
                'type': event_data['data'].get('type')
            }
        )

    async def stop(self):
        """Stop the message queue system."""
        self.running = False

        if self.consumer:
            self.consumer.close()

        if self.producer:
            self.producer.close()

        logger.info("Message queue stopped")

# Global message queue instance
message_queue = MessageQueue()

# Convenience functions
async def publish_user_event(user_id: str, event_type: str, data: Dict[str, Any]):
    """Publish user-related event."""
    await message_queue.publish_event(
        topic='user_events',
        event_type=event_type,
        data={'user_id': user_id, **data},
        key=user_id
    )

async def publish_course_event(course_id: str, event_type: str, data: Dict[str, Any]):
    """Publish course-related event."""
    await message_queue.publish_event(
        topic='course_events',
        event_type=event_type,
        data={'course_id': course_id, **data},
        key=course_id
    )

async def publish_ai_event(event_type: str, data: Dict[str, Any]):
    """Publish AI processing event."""
    await message_queue.publish_event(
        topic='ai_events',
        event_type=event_type,
        data=data
    )

async def publish_notification_event(user_id: str, notification_type: str, data: Dict[str, Any]):
    """Publish notification event."""
    await message_queue.publish_event(
        topic='notification_events',
        event_type='notification',
        data={'user_id': user_id, 'type': notification_type, **data},
        key=user_id
    )