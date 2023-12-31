import requests
from requests.adapters import HTTPAdapter, Retry
from typing import List

from project_shkedia_models import media, search, insights,jobs

class MediaDBService:

    def __init__(self,
                host: str,
                port: str | int,
                default_batch_size: int = 1000
                    ) -> None:
        self.default_batch_size = default_batch_size
        self.db_service_url = f"http://{host}:{str(port)}"


    def get_images_to_analyze(self, engine_name: str, batch_size: int | None = None) -> search.SearchResult:
        batch_size = batch_size if batch_size else self.default_batch_size
        
        get_images_api_url = self.db_service_url + f"/v2/no-jobs/media/{engine_name}"

        query_params = {
            "page_size": batch_size,
            "uploaded_status": "UPLOADED"
        }

        s = requests.Session()

        retries = Retry(total=5,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))

        results = s.get(get_images_api_url, params=query_params)

        s.close()

        if results.status_code == 200:
            return search.SearchResult(**results.json())
        return []

    def put_jobs(self, job_list: List[jobs.InsightJob]):
        json = [item.model_dump() for item in job_list]

        put_job_api_url = self.db_service_url + f"/v2/job"

        s = requests.Session()

        retries = Retry(total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))

        results = s.put(put_job_api_url, json=json)

        if results.status_code==200:
            return len(results.json())
        raise Exception(f"{results.status_code}: {results.detail}")
        
    def update_jobs(self, job_list: List[jobs.InsightJob]):
        json = [item.model_dump() for item in job_list]

        update_job_api_url = self.db_service_url + f"/v2/job"

        s = requests.Session()

        retries = Retry(total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))

        results = s.post(update_job_api_url, json=json)

        if results.status_code==200:
            return len(results.json())

    def put_insights(self,insights_list: List[insights.Insight]):
        
        json = [item.model_dump() for item in insights_list]

        put_insights_api_url = self.db_service_url + f"/v2/insights"

        s = requests.Session()

        retries = Retry(total=5,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))

        results = s.put(put_insights_api_url, json=json)

        if results.status_code==200:
            return len(results.json())






