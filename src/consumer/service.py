import os
import time
import traceback
import logging
logger = logging.getLogger(__name__)

from pydantic import BaseModel
from typing import List, Any
from datetime import datetime
import json

import boto3
from botocore.utils import ArnParser
from botocore.exceptions import ClientError
from publisher.sns_wrapper import SnsWrapper

class SqsMessageBody(BaseModel):
    Type: str
    MessageId: str
    TopicArn: str
    Message: str
    Timestamp: datetime
    UnsubscribeURL: str
    SequenceNumber: int | None = None
    SignatureVersion: str | None = None
    Signature: str | None = None
    SigningCertURL: str | None = None

    @property
    def topic_name(self):
        return ArnParser().parse_arn(self.TopicArn)['resource']
    
    @property
    def body(self):
        try:
            return json.loads(self.Message)
        except json.decoder.JSONDecodeError:
            return self.Message

class ConsumerService:
    def __init__(self,
                 queue_name: str,
                 listening_time_seconds: int=600,
                 message_ownership_time_seconds: int=600,
                 batch_size: int = 10,
                 sns_wrapper: SnsWrapper | None = None,
                 environment: str = "test"
                 ) -> None:
        
        self.sqs = boto3.resource("sqs")
        self.listening_time_seconds = listening_time_seconds
        self.message_ownership_time_seconds = message_ownership_time_seconds
        self.batch_size = batch_size
        self.callbacks = []
        self.environment = environment
        self.queue = self.__init_queue__(queue_name+"_"+self.environment)
        self.sns_wrapper = sns_wrapper
        

    def add_messages_callback(self, callback):
        self.callbacks.append(callback)

    def bind_topics(self,topics_to_bind: List[str]):
        if self.sns_wrapper is None:
            raise ValueError("SNS Wrapper was not supplied. Can't bind topic without it")

        for topic in topics_to_bind:
            topic_object = self.sns_wrapper.create_topic(topic+"_"+self.environment)
            self.sns_wrapper.subscribe(topic_object,"sqs",self.queue.attributes["QueueArn"])
            self.__add_access_policy__(self.queue,topic_object.attributes["TopicArn"])
        
    def unbind_topics(self, topics_to_unbind: List[str]):
        if self.sns_wrapper is None:
            raise ValueError("SNS Wrapper was not supplied. Can't unbind topics without it")
        for topic in self.sns_wrapper.list_topics():
            parsed_arn = ArnParser().parse_arn(topic.arn)
            if parsed_arn["resource"]+"_"+self.environment in topics_to_unbind:
                self.__delete_access_policy__(self.queue, topic.arn)
                
                logger.info(f"Unbinded topic {parsed_arn['resource']}")

    def __add_access_policy__(self,queue, topic_arn):
        """
        Add the necessary access policy to a queue, so
        it can receive messages from a topic.

        :param queue: The queue resource.
        :param topic_arn: The ARN of the topic.
        :return: None.
        """
        try:
            statement_id = f"{queue.attributes['QueueArn']}-{topic_arn}"
            statement_content = {
                                    "Sid": statement_id,
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": "SQS:SendMessage",
                                    "Resource": queue.attributes["QueueArn"],
                                    "Condition": {
                                        "ArnLike": {"aws:SourceArn": topic_arn}
                                    },
                }
            if "Policy" in queue.attributes:
                current_policy_dict = json.loads(queue.attributes["Policy"])
            else:
                current_policy_dict = {
                                "Version": "2012-10-17",
                                "Statement": [],
                            }
            statement_to_update = [statement for statement in current_policy_dict["Statement"] if statement["Sid"]==statement_id]
            if statement_to_update:
                statement_to_update[0] = statement_content
            else:
                current_policy_dict["Statement"].append(statement_content)
            queue.set_attributes(
                Attributes={
                    "Policy": json.dumps(current_policy_dict)
                }
            )
            logger.info("Added trust policy to the queue.")
        except ClientError as error:
            logger.exception("Couldn't add trust policy to the queue!")
            raise error

    def __delete_access_policy__(self,queue, topic_arn):
        """
        Add the necessary access policy to a queue, so
        it can receive messages from a topic.

        :param queue: The queue resource.
        :param topic_arn: The ARN of the topic.
        :return: None.
        """
        try:
            statement_id = f"{queue.attributes['QueueArn']}-{topic_arn}"
            current_policy_dict = json.loads(queue.attributes["Policy"])
            updated_statement = [statement for statement in current_policy_dict["Statement"] if statement["Sid"]!=statement_id]
            current_policy_dict["Statement"] = updated_statement
            if len(updated_statement) == 0:
                new_queue_attributes = { "Policy": "" }
            else:
                new_queue_attributes = {
                    "Policy": json.dumps(current_policy_dict)
                }
            queue.set_attributes(
                Attributes=new_queue_attributes
            )
            logger.info("Deleted the topic's access")
        except ClientError as error:
            logger.exception("Couldn't delete policy to the queue!")
            raise error

    def __init_queue__(self,queue_name):
        try:
            queue = self.__create_queue__(queue_name)
            return queue
        except ClientError as err:
            if not err.response["Error"]["Code"] == "QueueAlreadyExists":
                raise err
        return self.__get_queue__(queue_name)

    def __get_queue__(self,name):
        """
        Gets an SQS queue by name.

        :param name: The name that was used to create the queue.
        :return: A Queue object.
        """
        try:
            queue = self.sqs.get_queue_by_name(QueueName=name)
            logger.info("Got queue '%s' with URL=%s", name, queue.url)
            return queue
        except ClientError as error:
            logger.exception("Couldn't get queue named %s.", name)
            raise error           

    def __create_queue__(self, queue_name, attributes=None, fifo:bool = False, deduplicate=False):
        """
        Creates an Amazon SQS queue.

        :param name: The name of the queue. This is part of the URL assigned to the queue.
        :param attributes: The attributes of the queue, such as maximum message size or
                        whether it's a FIFO queue.
        :return: A Queue object that contains metadata about the queue and that can be used
                to perform queue operations like sending and receiving messages.
        """
        deduplicate = fifo if not fifo else deduplicate
        if not attributes:
            attributes ={
            "MaximumMessageSize": str(65536),
            "ReceiveMessageWaitTimeSeconds": str(self.listening_time_seconds),
            "VisibilityTimeout": str(self.message_ownership_time_seconds)}
            if fifo:
                attributes["FifoQueue"]=str(fifo)
                queue_name+=".fifo"
            if deduplicate:
                attributes["ContentBasedDeduplication"]=str(deduplicate)

        queue = self.sqs.create_queue(QueueName=queue_name, Attributes=attributes)
        logger.info("Created queue '%s' with URL=%s", queue_name, queue.url)
        return queue
    
    def listen(self, sleep_time: int):
        logger.info("Start Listening")
        while True:
            messages = None
            try:
                messages = self.__receive_messages__()
                if len(messages)==0:
                    time.sleep(sleep_time)
                    logger.info("Waiting for messages")
                    continue
                messages_bodies = [SqsMessageBody(**json.loads(message.body)) for message in messages]
                for callback in self.callbacks:
                    callback(messages_bodies)
                self.__ack_messages__(messages)
                if len(messages)<self.batch_size:
                    time.sleep(sleep_time)
            except Exception as err:
                if messages is list and len(messages)>0:
                    self.__nack_messages__(messages)
                traceback.print_exc()
                logger.error(err)
                break
            except KeyboardInterrupt:
                break
        logger.info("Stopped Listening")

    def __ack_messages__(self, messages):
        """
        Delete a batch of messages from a queue in a single request.

        :param queue: The queue from which to delete the messages.
        :param messages: The list of messages to delete.
        :return: The response from SQS that contains the list of successful and failed
                message deletions.
        """
        try:
            if len(messages) > 10:
                raise ValueError("Can acked only 10 messages at a time") # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs/queue/change_message_visibility_batch.html
            entries = [
                {"Id": str(ind), "ReceiptHandle": msg.receipt_handle}
                for ind, msg in enumerate(messages)
            ]
            response = self.queue.delete_messages(Entries=entries)
            failed_messages = []
            if "Successful" in response:
                for msg_meta in response["Successful"]:
                    logger.debug("Acked %s", messages[int(msg_meta["Id"])].receipt_handle)
            if "Failed" in response:
                for msg_meta in response["Failed"]:
                    logger.warning(
                        "Could not delete %s", messages[int(msg_meta["Id"])].receipt_handle
                    )
                    failed_messages.append(messages[int(msg_meta["Id"])])
            return failed_messages
        except ClientError:
            logger.exception("Couldn't delete messages from queue %s", self.queue)
           

    def __nack_messages__(self,messages):
        try:
            if len(messages) > 10:
                raise ValueError("Can nacked only 10 messages at a time") # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs/queue/change_message_visibility_batch.html
            entries=[
                {'Id': str(ind), 'ReceiptHandle': msg.receipt_handle, 'VisibilityTimeout': 0 }
                    for ind, msg in enumerate(messages)
            ]
            response = self.queue.change_message_visibility_batch(Entries=entries)
            failed_messages = []
            if "Successful" in response:
                for msg_meta in response["Successful"]:
                    logger.debug("Nacked %s", messages[int(msg_meta["Id"])].receipt_handle)
            if "Failed" in response:
                for msg_meta in response["Failed"]:
                    logger.warning(
                        "Could not delete %s", messages[int(msg_meta["Id"])].receipt_handle
                    )
                    failed_messages.append(messages[int(msg_meta["Id"])])
            return failed_messages
        except ClientError:
            logger.exception("Couldn't delete messages from queue %s", self.queue)

    def __receive_messages__(self) -> List[SqsMessageBody]:
        """
        Receive a batch of messages in a single request from an SQS queue.

        :param queue: The queue from which to receive messages.
        :param max_number: The maximum number of messages to receive. The actual number
                        of messages received might be less.
        :param wait_time: The maximum time to wait (in seconds) before returning. When
                        this number is greater than zero, long polling is used. This
                        can result in reduced costs and fewer false empty responses.
        :return: The list of Message objects received. These each contain the body
                of the message and metadata and custom attributes.
        """
        try:
            if self.queue is None:
                raise ConnectionError("Can't get connection to the queue")
            messages = self.queue.receive_messages(
                MessageAttributeNames=["All"],
                MaxNumberOfMessages=self.batch_size,
                WaitTimeSeconds=self.listening_time_seconds,
            )
            return messages
        except ClientError as error:
            logger.exception("Couldn't receive messages from queue: %s", self.queue)
            raise error          