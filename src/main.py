import traceback
import time
import logging
import boto3
logger = logging.getLogger(__name__)

from project_shkedia_models.insights import InsightEngine

from config import app_config, secret_config
from db.service import MediaDBService
from logic.service import MonthsEngineLogics
from db.user_service import UserDBService, UserRequest
from publisher.service import PublisherService
from consumer.service import ConsumerService
from publisher.service import MonthsTopicsEnum
from publisher.sns_wrapper import SnsWrapper

auth_service = UserDBService(host=app_config.USER_DB_HOST,
                             port=app_config.USER_DB_PORT,
                             credentials=UserRequest(user_name=secret_config.user_name, password=secret_config.password))

media_service = MediaDBService(host=app_config.MEDIA_DB_HOST, 
                               port=app_config.MEDIA_DB_PORT,
                               default_batch_size=app_config.BATCH_SIZE)

month_engine_logics = MonthsEngineLogics(media_db_service=media_service,
                                         auth_service=auth_service,
                                         engine_details=app_config.ENGINE_DETAILS,
                                         batch_process_size=app_config.BATCH_SIZE,
                                         batch_processing_period_minutes=app_config.BATCH_PROCESS_PERIOD_MIN)

consumer_service = ConsumerService(queue_name=app_config.ENGINE_DETAILS.input_queue_name,
                                   listening_time_seconds=app_config.LISTENING_TIME_SECONDS,
                                   message_ownership_time_seconds=app_config.MESSAGE_OWNERSHIP_TIME_SECONDS,
                                   batch_size=app_config.BATCH_SIZE,
                                   sns_wrapper=SnsWrapper(boto3.resource("sns")),
                                   environment=app_config.ENVIRONMENT)

consumer_service.bind_topics([app_config.ENGINE_DETAILS.input_source])

consumer_service.add_messages_callback(month_engine_logics.process_messages)


if __name__ == "__main__":
    try:
        consumer_service.listen(5)
        # month_engine_logics.listen()
    except Exception as err:
        logger.error(traceback.format_exc())

