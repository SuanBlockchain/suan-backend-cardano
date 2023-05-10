import json, time
from requests.structures import CaseInsensitiveDict
import requests
from datetime import date

# from sqlalchemy.orm import Session
# from fastapi import Depends
# from db.dblib import get_db
# from db.models import dbmodels
from core.config import config


def kobo_api(URL, params={}):
    kobo_tokens_dict = config(section="kobo")
    headers = CaseInsensitiveDict()
    kobo_token = kobo_tokens_dict["kobo_token"]
    headers["Authorization"] = "Token " + str(kobo_token)

    return requests.get(URL, headers=headers, params=params)


def generic_kobo_request(kobo_id: str = "") -> dict:
    TODAY = date.fromtimestamp(time.time())
    BASE_URL = "https://kf.kobotoolbox.org/api/v2/assets/"
    params = {"format": "json"}
    if kobo_id != "":
        BASE_URL = f"{BASE_URL}{kobo_id}/data"
    rawResult = kobo_api(BASE_URL, params)
    rawResult = json.loads(rawResult.content.decode("utf-8"))
    with open("./rawresult.json", "w") as file:
        json.dump(rawResult, file, indent=4, ensure_ascii=False)

    return rawResult

# def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     db_projects = db.query(dbmodels.Projects).offset(skip).limit(limit).all()
#     if db_projects is None:
#         raise Exception("No records found")
#     return db_projects

# TODAY = date.fromtimestamp(time.time())
# BASE_URL = "https://kf.kobotoolbox.org/api/v2/assets/"
# params = {"format": "json"}
# rawResult = kobo_api(BASE_URL, params)
# rawResult = json.loads(rawResult.content.decode("utf-8"))
# with open("./rawresult.json", "w") as file:
#     json.dump(rawResult, file, indent=4, ensure_ascii=False)
# projects = rawResult.get("results", None)
# print(projects)

# try:
#     tableName = "projects"
#     query = f"SELECT uid FROM {tableName};"
#     uids = read_query(query)
#     uid_array = []
#     if uids != [] or uids is not None:
#         for uid in uids:
#             uid_array.append(uid[0])

#     project_id = create_projects(projects, uid_array)

#     tableName = "projects"
#     query = f"SELECT id, uid FROM {tableName};"
#     project_query_result = read_query(query)
#     for project_ids in project_query_result:
#         project_id = project_ids[0]
#         ASSET_UID = project_ids[1]
#         if ASSET_UID == "aetorrJTocs2DgVfc5th8D":
#             print(ASSET_UID)
#         URL = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/data/"
#         # QUERY = f'{{"_submission_time":{{"$gt":"{TODAY}"}}}}'
#         params = {
#             # "query": QUERY,
#             "format": "json"
#         }
#         rawResult = kobo_api(URL, params)
#         data = json.loads(rawResult.content.decode("utf-8"))
#         with open("./data.json", "w") as file:
#             json.dump(data, file, indent=4, ensure_ascii=False)
#         if "results" in data:
#             data = data["results"]
#         else:
#             continue
#         tableName = "data"
#         query = f"SELECT _id, validation FROM {tableName};"
#         _id_array = read_query(query)

#         tableName = "measurement"
#         query = f"SELECT _id, measurement, value, file_name FROM {tableName};"
#         meas_result = read_query(query)

#         if ASSET_UID == "a3pDRvFG2FNQwP8BeDAexS":
#             create_dataV2(project_ids, data, _id_array)
#             create_measurementsV2(project_ids, URL, data, meas_result)
#         else:
#             create_data(project_ids, data, _id_array)
#             create_measurements(project_ids, URL, data, meas_result)
#         # Check if there is data with the approved status
#         tableName = "data"
#         query = f"SELECT project_id, _id, id FROM {tableName} WHERE validation = 'Approved' and project_id='{project_id}';"
#         data_results = read_query(query)
#         if data_results != [] or data_results is not None:
#             for data_result in data_results:
#                 create_picture(data_result)
# except TypeError:
#     print("No projects found in table projects")
