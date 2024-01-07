## 0.1.0 (2024-01-07)

### Feat

- **main**: Bind consumer and logic to create queue based worker
- **db/service,logic/service**: Get engine details from the db at startup
- **logic/service,-db/service**: Create jobs for media without the job. Implement the insight calculation and closing of the job

### Fix

- **consumer/service**: Add environment to topic and queue names. Handle exceptions in the listen function. Add support to many types of messages
- **db/service**: Return list of InsightJob after put_jobs
- **config**: Update the extract_env_variable function to better handle errors. Change BATCH_PROCESS_PERIOD_MIN to float type

### Refactor

- **config**: Add environment variables to the configure the consumer
- **logic/service**: Create the queue logic
- **publisher/service**: Upgrade publisher version to latest from template
- **consumer,publisher**: Import consumer and publisher templates from the template-worker
- **logic/service,db/services**: Add the lastest versions of the services from yolov7 worker. Include engine creation and basic authentications
- **src**: Create the basic worker structure with the db service, logic service, main and config
- **src,tests**: Create the basic structure for the project and tests
- **general**: Adjust files to the new project (from basic template version)
- **.gitigone,dockerignore**: Adding .local, dev folders to the gitignore. Delete .devcontainer from .dockerignore
