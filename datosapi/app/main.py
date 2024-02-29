from rocketry import Rocketry
from rocketry.args import TaskLogger, Config, EnvArg
from rocketry.log import MinimalRecord
# from redbird.repos import SQLRepo
# from sqlalchemy import create_engine
from redbird.repos import CSVFileRepo

from .tasks import scheduler

app = Rocketry(config={
        "task_execution": "async",
#     # "task_pre_exist": "raise", #Default
#     # "force_status_from_logs": False, #Default
#     # "silence_task_prerun": False, #Default
#     # "silence_task_logging": False, #Default
#     # "silence_cond_check": False, #Default
#     # "multilaunch": False, #Default
#     # "restarting": "replace", #Default
#     # "instant_shutdown": False, #Default
})

# Set Task Groups
# ---------------

app.include_grouper(scheduler.group)

# Application Setup
# -----------------

@app.setup()
def set_repo(logger=TaskLogger()):

    filename = 'logs.csv'
    repo = CSVFileRepo(filename=f'./datosapi/app/basic_info/{filename}', model=MinimalRecord, id_field="created")
    logger.set_repo(repo)

@app.setup()
def set_config(config=Config(), env=EnvArg("ENV", default="dev")):
    if env == "prod":
        config.silence_task_prerun = True
        config.silence_task_logging = True
        config.silence_cond_check = True
    else:
        config.silence_task_prerun = False
        config.silence_task_logging = False
        config.silence_cond_check = False

if __name__ == "__main__":
    app.run()