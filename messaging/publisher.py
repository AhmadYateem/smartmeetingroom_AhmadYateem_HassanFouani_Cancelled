"""
RabbitMQ Message Publisher for async notifications.
Part II Enhancement: Asynchronous Messaging with RabbitMQ

Publishes messages for:
- Booking confirmations
- Booking cancellations
- Review notifications
- System alerts
"""

import pika
import json
from typing import Dict, Any
from configs.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MessagePublisher:
    """
    RabbitMQ message publisher for asynchronous notifications.

    Supports publishing messages to different queues for various events.
    """

    def __init__(self):
        """Initialize RabbitMQ connection."""
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                Config.RABBITMQ_USER,
                Config.RABBITMQ_PASSWORD
            )

            parameters = pika.ConnectionParameters(
                host=Config.RABBITMQ_HOST,
                port=Config.RABBITMQ_PORT,
                virtual_host=Config.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare queues
            self._declare_queues()

            logger.info("Connected to RabbitMQ successfully")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            self.connection = None
            self.channel = None

    def _declare_queues(self):
        """Declare all required queues."""
        queues = [
            'booking_notifications',
            'booking_cancellations',
            'review_notifications',
            'system_alerts'
        ]

        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)
            logger.debug(f"Queue declared: {queue}")

    def _publish_message(self, queue: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to queue.

        Args:
            queue: Queue name
            message: Message data

        Returns:
            Boolean indicating success
        """
        if not self.channel:
            logger.warning("Not connected to RabbitMQ. Attempting to reconnect...")
            self.connect()

        if not self.channel:
            logger.error("Cannot publish message - no RabbitMQ connection")
            return False

        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )

            logger.info(f"Message published to queue '{queue}': {message.get('type', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish message to '{queue}': {str(e)}")
            return False

    def publish_booking_confirmation(self, booking_data: Dict[str, Any]) -> bool:
        """
        Publish booking confirmation message.

        Args:
            booking_data: Booking information

        Returns:
            Boolean indicating success
        """
        message = {
            'type': 'booking_confirmation',
            'booking_id': booking_data.get('id'),
            'user_id': booking_data.get('user_id'),
            'room_id': booking_data.get('room_id'),
            'title': booking_data.get('title'),
            'start_time': booking_data.get('start_time'),
            'end_time': booking_data.get('end_time'),
            'timestamp': booking_data.get('timestamp')
        }

        return self._publish_message('booking_notifications', message)

    def publish_booking_cancellation(self, booking_data: Dict[str, Any]) -> bool:
        """
        Publish booking cancellation message.

        Args:
            booking_data: Booking information

        Returns:
            Boolean indicating success
        """
        message = {
            'type': 'booking_cancellation',
            'booking_id': booking_data.get('id'),
            'user_id': booking_data.get('user_id'),
            'room_id': booking_data.get('room_id'),
            'title': booking_data.get('title'),
            'cancellation_reason': booking_data.get('cancellation_reason'),
            'timestamp': booking_data.get('timestamp')
        }

        return self._publish_message('booking_cancellations', message)

    def publish_review_notification(self, review_data: Dict[str, Any]) -> bool:
        """
        Publish review notification message.

        Args:
            review_data: Review information

        Returns:
            Boolean indicating success
        """
        message = {
            'type': 'review_notification',
            'review_id': review_data.get('id'),
            'room_id': review_data.get('room_id'),
            'user_id': review_data.get('user_id'),
            'rating': review_data.get('rating'),
            'timestamp': review_data.get('timestamp')
        }

        return self._publish_message('review_notifications', message)

    def publish_system_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Publish system alert message.

        Args:
            alert_data: Alert information

        Returns:
            Boolean indicating success
        """
        message = {
            'type': 'system_alert',
            'severity': alert_data.get('severity', 'info'),
            'message': alert_data.get('message'),
            'service': alert_data.get('service'),
            'timestamp': alert_data.get('timestamp')
        }

        return self._publish_message('system_alerts', message)

    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")


# Global publisher instance
_publisher = None


def get_publisher() -> MessagePublisher:
    """
    Get global message publisher instance.

    Returns:
        MessagePublisher instance
    """
    global _publisher

    if _publisher is None:
        _publisher = MessagePublisher()

    return _publisher
