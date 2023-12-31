import traceback
import time
import logging
logger = logging.getLogger(__name__)

from project_shkedia_models.insights import InsightEngine

from config import app_config
from db.service import MediaDBService
from logic.service import MonthsEngineLogics

media_service = MediaDBService(host=app_config.MEDIA_DB_HOST, 
                               port=app_config.MEDIA_DB_PORT,
                               default_batch_size=app_config.BATCH_SIZE)

engine_details = InsightEngine(name=app_config.ENGINE_NAME,description=app_config.DESCRIPTION,
                                         input_source=app_config.INPUT_SOURCE,
                                         input_queue_name=app_config.INPUT_QUEUE_NAME,
                                         output_exchange_name=app_config.OUTPUT_EXCHANGE_NAME,
                                         id="4dd224ba-3d49-4e3e-8f4a-14e1d50ea965")

month_engine_logics = MonthsEngineLogics(media_db_service=media_service,
                                         engine_details=engine_details,
                                         batch_process_size=app_config.BATCH_SIZE,
                                         batch_processing_period_minutes=app_config.BATCH_PROCESS_PERIOD_MIN)

if __name__ == "__main__":
    try:
        month_engine_logics.listen()
    except Exception as err:
        logger.error(traceback.format_exc())

