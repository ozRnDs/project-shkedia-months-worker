import traceback
import time
import logging
logger = logging.getLogger(__name__)

from project_shkedia_models.insights import InsightEngine

from config import app_config, secret_config
from db.service import MediaDBService
from logic.service import MonthsEngineLogics
from db.user_service import UserDBService, UserRequest

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

if __name__ == "__main__":
    try:
        month_engine_logics.listen()
    except Exception as err:
        logger.error(traceback.format_exc())

