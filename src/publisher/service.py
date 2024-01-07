import traceback
import logging
logger = logging.getLogger(__name__)

import boto3
from .sns_wrapper import SnsWrapper
from typing import List

class PublisherService:
    def __init__(self,
                 topic_names: List[str],
                 
                 ) -> None:
        self.sns_service = SnsWrapper(boto3.resource("sns"))
        self.topic_names = topic_names
        self.topics = {}
        for topic_id in self.topic_names:
            self.topics[topic_id] = self.sns_service.create_topic(topic_id)


    def publish(self, topic_id, message, message_id):
        #TODO: Check how to parse message
        try:
            self.sns_service.publish_message(self.topics[topic_id],message.model_dump_json(),message_id)
        except Exception as err:
            traceback.print_exc()
            logger.error(err)
            raise err