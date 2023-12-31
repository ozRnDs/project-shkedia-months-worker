import os
import logging
logging.basicConfig(format='%(asctime)s.%(msecs)05d | %(levelname)s | %(filename)s:%(lineno)d | %(message)s' , datefmt='%FY%T')

class ApplicationConfiguration:

    RECONNECT_WAIT_TIME: int = 1
    RETRY_NUMBER: int = 10
    ENVIRONMENT: str = "DEV"
    DEBUG: bool = False

    # Authentication Configuration values
    AUTH_SERVICE_URL: str = "CHANGE ME"

    # DB Configuration values
    AUTH_DB_CREDENTIALS_LOCATION: str = "/temp/postgres_credentials/postgres_credentials.json"

    # DB Configuration values
    MEDIA_DB_HOST: str = "10.0.0.5"
    MEDIA_DB_PORT: str = "4431"
    MEDIA_REPO_HOST: str = "10.0.0.5"
    MEDIA_REPO_PORT: str = "4432"
    USER_DB_HOST: str = "10.0.0.5"
    USER_DB_PORT: str = "4430"
        
    # Encryption Configuration Values
    PUBLIC_KEY_LOCATION: str = ".local/data.pub"
    PRIVATE_KEY_LOCATION: str = ".local/data"

    # Worker Configuration Values
    ENGINE_NAME: str = "months"
    DESCRIPTION: str = "Extract the month and year the media was created in the format: MM-YYYY"
    INPUT_SOURCE: str = "raw.image"
    INPUT_QUEUE_NAME: str = "InputMonthEngine"
    OUTPUT_EXCHANGE_NAME: str = "output.month.engine"
    
    BATCH_SIZE: int = 100
    BATCH_PROCESS_PERIOD_MIN: int = 30

    def __init__(self) -> None:
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.logger.info("Start App")

        self.extract_env_variables()
        

    def extract_env_variables(self):
        for attr, attr_type in self.__annotations__.items():
            try:
                self.__setattr__(attr, (attr_type)(os.environ[attr]))
            except Exception as err:
                self.logger.warning(f"Couldn't find {attr} in environment. Run with default value")
        
app_config = ApplicationConfiguration()