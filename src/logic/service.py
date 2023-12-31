import time
import logging
logger = logging.getLogger(__name__)

from typing import List

from project_shkedia_models import search, media, insights, jobs
from db.service import MediaDBService

class MonthsEngineLogics:

    def __init__(self,
                 media_db_service: MediaDBService,
                 engine_details: insights.InsightEngine,
                 batch_process_size: int = 200,
                 batch_processing_period_minutes: int = 120,) -> None:
        self.engine = engine_details
        self.media_db_service = media_db_service
        self.batch_process_size = batch_process_size
        self.batch_processing_period_minutes = batch_processing_period_minutes
    

    def __init_engine__(self):
        #TODO: Get the engine's details if the exists in the db
        #TODO: Create the engine in the db if not exists
        #TODO: Updates the engine details if needed
        pass


    def listen(self):
        while True:
            media_to_process: search.SearchResult = self.media_db_service.get_images_to_analyze(engine_name="months", batch_size=self.batch_process_size)
            insights_list = []
            job_list: List[jobs.InsightJob] = []
            for result in media_to_process.results:
                media_item = media.MediaStorage(**result)
                temp_job = jobs.InsightJob(insight_engine_id=self.engine.id,
                                           media_id=media_item.media_id)
                job_list.append(temp_job)
                temp_image_insight = insights.Insight(insight_engine_id=self.engine.id,
                                                      media_id=media_item.media_id,
                                                      name=media_item.created_on.strftime("%m-%Y"),
                                                      job_id=temp_job.id,
                                                      status=insights.InsightStatusEnum.APPROVED)
                insights_list.append(temp_image_insight)
            if len(job_list)>0:
                self.media_db_service.put_jobs(job_list)
                self.media_db_service.put_insights(insights_list)
                for job in job_list:
                    job.status = jobs.InsightJobStatus.DONE
                self.media_db_service.update_jobs(job_list)
            time.sleep(self.batch_processing_period_minutes*60)


