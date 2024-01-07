import traceback
import logging
logger = logging.getLogger(__name__)
from uuid import uuid4
import boto3
from .sns_wrapper import SnsWrapper
from typing import List, Dict
from project_shkedia_models.message import ProjectShkediaMsgMetadata, ProjectShkediaComponent, ProjectShkediaMessage, ActionsEnum,TimestampLogger

from enum import Enum

class MonthsTopicsEnum(str, Enum):
    MONTHS_INSIGHTS="MONTHS_INSIGHTS"


class PublisherService:
    def __init__(self,
                 topic_names: Dict[MonthsTopicsEnum,str],
                 name: str,
                 id: str,
                 environment: str = "test",
                 ) -> None:
        self.sns_service = SnsWrapper(boto3.resource("sns"))
        self.topic_names = topic_names
        self.environment = environment

        self.topics = {}
        for _,topic_name in self.topic_names.items():
            if len(topic_name)>0 and type(topic_name)==str:
                self.topics[topic_name] = self.sns_service.create_topic(topic_name+"_"+self.environment)
        self.details = ProjectShkediaComponent(name=name, id=id)


    def publish(self, topic_type: MonthsTopicsEnum, object_to_publish, action: ActionsEnum, timestamps: TimestampLogger):
        try:
            topic_name = self.topic_names[topic_type]
            object_class = type(object_to_publish)
            object_type_name = object_class.__module__ + "." + object_class.__name__
            # To get the class from it's name use the following: 
            #   module_name, class_name = object_type_name.rsplit('.', 1)
            #   class_obj = getattr(sys.modules[module_name], class_name)
            #
            message_meta = ProjectShkediaMsgMetadata(workers=[self.details],timestamps=timestamps.timestamps)
            message_to_publish = ProjectShkediaMessage(meta=message_meta, action=action, body_type=object_type_name,body=object_to_publish)
            self.__sns_publish__(topic_name,message_to_publish,message_id=str(uuid4()))
        except Exception as err:
            logger.warning(f"Failed to publish the action to topic: {str(err)}")

    def __sns_publish__(self, topic_name, message, message_id):
        try:
            self.sns_service.publish_message(self.topics[topic_name],message.model_dump_json())
        except Exception as err:
            traceback.print_exc()
            logger.error(err)
            raise err