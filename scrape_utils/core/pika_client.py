"""pika_client.py."""
import json
import logging
import uuid
from typing import Callable, Optional

import pika
from aio_pika import Message, connect_robust
from pika.adapters.blocking_connection import (BlockingChannel,
                                               BlockingConnection)
from pika.spec import Queue

# from ...core.config import Settings
# from .schema import BaseAddRow, VerifyScrapingMessageSchema

logger = logging.getLogger(__name__)


class PikaClient:
    """Asynchronous PikaClient."""

    def __init__(
        self,
        process_callable: Callable,
        # settings: Settings,
        settings,
    ) -> None:
        self._connection_url = settings.rmq_url
        self.publish_queue_name = settings.rmq_publish_queue
        self.publish_add_row_queue_name = settings.rmq_add_row_queue
        self.consume_queue_name = settings.rmq_consume_queue
        self.verify_scraped_queue_name = settings.rmq_verify_scraped_queue

        self._conn_params = pika.URLParameters(self._connection_url)
        self._connection: Optional[BlockingConnection] = None
        # self._connection = pika.BlockingConnection(self._conn_params)
        # self._channel = self._connection.channel()
        self._channel: Optional[BlockingChannel] = None
        self.callback_queue: Optional[Queue.DeclareOk] = None
        # self.response = None
        self.publish_queue: Optional[Queue.DeclareOk] = None
        self.process_callable: Callable = process_callable

        self.connect()

    def connect(self) -> None:
        if not self._connection or self._connection.is_closed:
            logger.info(f"connecting to {self._connection_url}")
            self._connection = pika.BlockingConnection(self._conn_params)
            self._channel = self._connection.channel()
            # self._channel.exchange_declare(exchange=self.EXCHANGE, type=self.TYPE)

            self.publish_queue = self._channel.queue_declare(
                queue=self.publish_queue_name
            )
            # self.publish_queue = None
            self.callback_queue = self.publish_queue.method.queue
            logger.info("Pika connection initialized")

    def _publish(self, message: dict, queue_name: str):
        assert isinstance(message, dict), f"{type(message)=}"
        self._channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue, correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps(message).encode(),
        )

    def publish(self, message: dict, queue_name: str):
        """Publish message to queue.

        Auto reconnect pika if connection is lost.
        """
        try:
            self._publish(message, queue_name)
        except (
            pika.exceptions.ConnectionClosed,
            pika.exceptions.StreamLostError,
            ConnectionResetError,
        ):
            logging.debug("reconnecting to queue")
            self.connect()
            self._publish(message, queue_name)

    async def consume(self, loop):
        """Set up message listener with the current running loop."""
        connection = await connect_robust(url=self._connection_url, loop=loop)
        channel = await connection.channel()
        queue = await channel.declare_queue(self.consume_queue_name)
        await queue.consume(self.process_incoming_message, no_ack=False)
        logger.info("Established pika async listener")
        return connection

    async def process_incoming_message(self, message) -> None:
        """Process incoming message from RabbitMQ."""
        message.ack()
        body = message.body
        logger.info("Received message")
        if body:
            self.process_callable(json.loads(body))

    # TODO: make async
    # TODO: generalize send_message to only allow queue names from enum?
    def send_message(self, message: dict) -> None:
        """Publish message to queue."""
        self.publish(message, self.publish_queue_name)

    # def send_add_row_message(self, message: BaseAddRow) -> None:
    def send_add_row_message(self, message) -> None:
        """Publish add_row message to queue."""
        self.publish(message.dict(), self.publish_add_row_queue_name)

    # ugly, but types not available to scrape modules
    def send_add_row_message_json(self, message: dict) -> None:
        """Publish add_row message to queue."""
        self.publish(message, self.publish_add_row_queue_name)

    # def send_verify_scraping_message(
    #     self, message: VerifyScrapingMessageSchema
    # ) -> None:
    def send_verify_scraping_message(self, message) -> None:
        """Publish verify_scraping_message to queue."""
        self.publish(message.dict(), self.verify_scraped_queue_name)
