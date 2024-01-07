import sys
import time
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

import json
from typing import List

from project_shkedia_models import search, media, insights, jobs, message
from db.service import MediaDBService
from db.user_service import UserDBService, UserRequest
from consumer.service import SqsMessageBody

class MonthsEngineLogics:

    def __init__(self,
                 media_db_service: MediaDBService,
                 engine_details: insights.InsightEngine,
                 auth_service: UserDBService,
                 batch_process_size: int = 200,
                 batch_processing_period_minutes: float = 120,) -> None:
        self.media_db_service = media_db_service
        self.batch_process_size = batch_process_size
        self.batch_processing_period_minutes = batch_processing_period_minutes
        self.engine = self.__init_engine__(engine_details)
        self.auth_service = auth_service
        logger.info("Initialized EngineLogics")


    def __init_engine__(self,local_engine_details):
        search_results = self.media_db_service.search_engine(engine_name=local_engine_details.name)
        if search_results.total_results_number > 0:
            logger.debug("Got engine details from DB")
            db_engine = insights.InsightEngine(**search_results.results[0])
            if db_engine == local_engine_details:
                return db_engine
            logger.warning("There is a difference between the db and local engines")
            #TODO: Updates the engine details if needed
            return db_engine
        if self.media_db_service.create_engine(local_engine_details):
            logger.info("Got engine details from DB")
            return local_engine_details

    def __get_MediaID_objects_from_messages__(self, messages_bodies: List[SqsMessageBody]):
        parsed_messages = [message.ProjectShkediaMessage(**json.loads(raw_message.Message)) for raw_message in messages_bodies]
        process_list = []
        for msg_id, new_message in enumerate(parsed_messages):
            module_name, class_name = new_message.body_type.rsplit('.', 1)
            class_obj = getattr(sys.modules[module_name], class_name)
            if not issubclass(class_obj, media.MediaIDs):
                logger.error(f"Can't process classes of type {new_message.body_type}. {messages_bodies[msg_id].MessageId}")
                continue
            process_list += [media.MediaIDs(**media_item) for media_item in new_message.body]
        return process_list

    def process_messages(self, messages_bodies: List[SqsMessageBody]):
        process_list = self.__get_MediaID_objects_from_messages__(messages_bodies)
        jobs_list = self.__create_jobs_for_media_ids__(process_list)
        
        insights_list = []
        processed_jobs = []
        for job in jobs_list:
            media_item = [media_item for media_item in process_list if media_item.media_id == job.media_id][0]
            try:
                insights_list += self.__extract_insights_logics__(job.id,media_item)
            except Exception as err:
                logger.error(f"Failed to process job {job.id}")
                continue
            processed_jobs.append(job)

        if len(insights_list)>0:
            pass
            self.media_db_service.put_insights(insights_list)
        if len(processed_jobs)>0:
            for job in processed_jobs:
                job.status = jobs.InsightJobStatus.DONE
                job.end_time = datetime.now()
            if not self.media_db_service.update_jobs(processed_jobs)>0:
                logger.error(f"Could not update job {processed_jobs}")


    def __extract_insights_logics__(self, job_id, media_item: media.MediaThumbnail) -> List[insights.Insight]:
        temp_image_insight = insights.Insight(insight_engine_id=self.engine.id,
                                                media_id=media_item.media_id,
                                                name=media_item.created_on.strftime("%Y-%m"),
                                                job_id=job_id,
                                                status=insights.InsightStatusEnum.APPROVED)
        logger.info(f"Processed job ({job_id}). Added insight calculated: {temp_image_insight.name}")

        return [temp_image_insight]

    def __create_jobs_for_media_ids__(self, media_list: List[media.MediaIDs]):
        job_list: List[jobs.InsightJob] = []
        for media_item in media_list:
            temp_job = jobs.InsightJob(insight_engine_id=self.engine.id,
                                        media_id=media_item.media_id)
            logger.info(f"Create new job ({temp_job.id}) for media ({media_item.media_id})")
            job_list.append(temp_job)
        if len(job_list)>0:
            return self.media_db_service.put_jobs(job_list)
            

    def __create_jobs__(self):
        media_to_process: search.SearchResult = self.media_db_service.get_media_to_analyze(engine_name=self.engine.name, batch_size=self.batch_process_size)
        job_list: List[jobs.InsightJob] = []
        for result in media_to_process.results:
            media_item = media.MediaStorage(**result)
            temp_job = jobs.InsightJob(insight_engine_id=self.engine.id,
                                        media_id=media_item.media_id)
            logger.info(f"Create new job ({temp_job.id}) for media ({media_item.media_id})")
            job_list.append(temp_job)
        if len(job_list)>0:
            self.media_db_service.put_jobs(job_list)
            pass

    def listen(self):
        while True:
            try:
                self.__create_jobs__()
            except Exception as err:
                logger.warning(f"Failed to create jobs: {str(err)}")
            logger.info("Search jobs")
            jobs_to_process: search.SearchResult = self.media_db_service.get_pending_jobs(engine_id=self.engine.id, batch_size=self.batch_process_size)
            jobs_to_process: List[jobs.InsightJob] = [jobs.InsightJob(**item) for item in jobs_to_process.results]
            media_to_process: search.SearchResult = self.media_db_service.get_media_by_ids(token=self.auth_service.get_token(),
                                                                                           media_ids_list=[item.media_id for item in jobs_to_process],
                                                                                           page_size=self.batch_process_size)
            media_to_process: List[media.MediaIDs] = [media.MediaIDs(**media_item) for media_item in media_to_process.results]
            analyzing_dictionary = {}
            for job in jobs_to_process:
                list_of_relevent_media = [media_item for media_item in media_to_process if media_item.media_id==job.media_id]
                if len(list_of_relevent_media)>0:
                    analyzing_dictionary[job.id] = (job,list_of_relevent_media[0])
            
            insights_list = []
            processed_jobs = []
            for job_id,value in analyzing_dictionary.items():
                temp_job,media_item = value
                insights_list += self.__extract_insights_logics__(temp_job.id,media_item)
                processed_jobs.append(temp_job)
            if len(insights_list)>0:
                pass
                # self.media_db_service.put_insights(insights_list)
            if len(processed_jobs)>0:
                for job in processed_jobs:
                    job.status = jobs.InsightJobStatus.DONE
                    job.end_time = datetime.now()
                if not self.media_db_service.update_jobs(processed_jobs)>0:
                    logger.error(f"Could not update job {processed_jobs}")
            if len(jobs_to_process)==0:
                time.sleep(self.batch_processing_period_minutes*60)


