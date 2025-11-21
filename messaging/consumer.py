"""
RabbitMQ Message Consumer for processing async notifications.
Part II Enhancement: Asynchronous Messaging with RabbitMQ

Consumes and processes messages for:
- Booking confirmations (send emails)
- Booking cancellations (send emails)
- Review notifications
- System alerts
"""

import pika
import json
from typing import Callable
from configs.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MessageConsumer:
    """
    RabbitMQ message consumer for processing notifications.

    Listens to queues and processes messages asynchronously.
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

            logger.info("Consumer connected to RabbitMQ successfully")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            self.connection = None
            self.channel = None

    def _process_booking_confirmation(self, message: dict):
        """
        Process booking confirmation message.

        Args:
            message: Message data
        """
        logger.info(f"Processing booking confirmation: {message.get('booking_id')}")

        # In production, this would send an email
        # For now, just log it
        logger.info(
            f"Booking confirmation email would be sent to user {message.get('user_id')} "
            f"for booking {message.get('booking_id')}"
        )

        # TODO: Implement email sending via SMTP or SendGrid/Twilio
        # send_email(
        #     to=get_user_email(message['user_id']),
        #     subject='Booking Confirmation',
        #     body=format_booking_confirmation(message)
        # )

    def _process_booking_cancellation(self, message: dict):
        """
        Process booking cancellation message.

        Args:
            message: Message data
        """
        logger.info(f"Processing booking cancellation: {message.get('booking_id')}")

        logger.info(
            f"Booking cancellation email would be sent to user {message.get('user_id')} "
            f"for booking {message.get('booking_id')}"
        )

        # TODO: Implement email sending
        # send_email(
        #     to=get_user_email(message['user_id']),
        #     subject='Booking Cancelled',
        #     body=format_booking_cancellation(message)
        # )

    def _process_review_notification(self, message: dict):
        """
        Process review notification message.

        Args:
            message: Message data
        """
        logger.info(f"Processing review notification: {message.get('review_id')}")

        # Notify facility managers about new reviews
        logger.info(
            f"Review notification for room {message.get('room_id')} "
            f"with rating {message.get('rating')}"
        )

        # TODO: Send notification to facility managers

    def _process_system_alert(self, message: dict):
        """
        Process system alert message.

        Args:
            message: Message data
        """
        severity = message.get('severity', 'info')
        alert_message = message.get('message')
        service = message.get('service')

        logger.warning(
            f"System alert [{severity}] from {service}: {alert_message}"
        )

        # TODO: Send alerts to administrators based on severity

    def _callback_handler(self, queue_name: str, processor: Callable):
        """
        Create callback handler for queue.

        Args:
            queue_name: Queue name
            processor: Message processor function

        Returns:
            Callback function
        """
        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                logger.debug(f"Received message from '{queue_name}': {message.get('type')}")

                # Process message
                processor(message)

                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message from '{queue_name}': {str(e)}")
                # Reject message without requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            except Exception as e:
                logger.error(f"Error processing message from '{queue_name}': {str(e)}")
                # Reject message and requeue for retry
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        return callback

    def start_consuming(self):
        """
        Start consuming messages from all queues.

        This is a blocking operation that runs indefinitely.
        """
        if not self.channel:
            logger.error("Cannot start consuming - no RabbitMQ connection")
            return

        try:
            # Declare queues (in case they don't exist)
            self.channel.queue_declare(queue='booking_notifications', durable=True)
            self.channel.queue_declare(queue='booking_cancellations', durable=True)
            self.channel.queue_declare(queue='review_notifications', durable=True)
            self.channel.queue_declare(queue='system_alerts', durable=True)

            # Set QoS (prefetch count)
            self.channel.basic_qos(prefetch_count=10)

            # Setup consumers
            self.channel.basic_consume(
                queue='booking_notifications',
                on_message_callback=self._callback_handler(
                    'booking_notifications',
                    self._process_booking_confirmation
                )
            )

            self.channel.basic_consume(
                queue='booking_cancellations',
                on_message_callback=self._callback_handler(
                    'booking_cancellations',
                    self._process_booking_cancellation
                )
            )

            self.channel.basic_consume(
                queue='review_notifications',
                on_message_callback=self._callback_handler(
                    'review_notifications',
                    self._process_review_notification
                )
            )

            self.channel.basic_consume(
                queue='system_alerts',
                on_message_callback=self._callback_handler(
                    'system_alerts',
                    self._process_system_alert
                )
            )

            logger.info("Started consuming messages from all queues")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop_consuming()

        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            raise

    def stop_consuming(self):
        """Stop consuming messages."""
        try:
            if self.channel:
                self.channel.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping consumer: {str(e)}")


def main():
    """Main function to run the consumer."""
    logger.info("Starting RabbitMQ message consumer...")

    consumer = MessageConsumer()

    try:
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Consumer failed: {str(e)}")
    finally:
        consumer.stop_consuming()


if __name__ == '__main__':
    main()
