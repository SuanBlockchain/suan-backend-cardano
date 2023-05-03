#!/usr/bin/python
# from asyncio.windows_events import NULL
from utils import kobo_api

# from dblib import insert_project, read_query, write_query, insert_picture
import json
from psycopg2.extras import Json
from datetime import date, datetime
import time

# from unidecode import unidecode
# import unicodedata


# def create_projects(projects, uid_array):
#     date_created_criteria = "2022-10-01"
#     date_created_criteria = datetime.strptime(date_created_criteria, "%Y-%m-%d").date()
#     uid = None
#     project_id_array = []
#     try:
#         if projects != None:
#             for project in projects:
#                 date_created = project.get("date_created")
#                 deployment__active = project.get("deployment__active")
#                 owner__username = project.get("owner__username")
#                 uid = project.get("uid")
#                 dt_object = datetime.strptime(
#                     date_created, "%Y-%m-%dT%H:%M:%S.%fZ"
#                 ).date()
#                 if (
#                     deployment__active
#                     and uid not in uid_array
#                     and owner__username == "getfair"
#                     and dt_object >= date_created_criteria
#                 ):
#                     project_dict = {}
#                     project_dict["name"] = project["name"]
#                     project_dict["country"] = project["settings"]["country"][0]["label"]
#                     project_dict["sector"] = project["settings"]["sector"]["label"]
#                     project_dict["url"] = project["url"]
#                     project_dict["owner"] = project["owner"]
#                     project_dict["uid"] = project["uid"]
#                     project_dict["kind"] = project["kind"]
#                     project_dict["asset_type"] = project["asset_type"]
#                     project_dict["version_id"] = project["version_id"]
#                     project_dict["date_created"] = project["date_created"]
#                     table = "projects"
#                     columns = []
#                     for k in project_dict.keys():
#                         columns = list(project_dict.keys())

#                     values = []
#                     for value in project_dict.values():
#                         if type(value) == str:
#                             value = value.replace("'", "''")
#                             value = "'" + value + "'"
#                         values += [str(value)]
#                     project_id = insert_project(table, columns, values)
#                     print(f"Project id {uid} was created")
#                     project_id_array.append(project_id)
#             return project_id_array
#         else:
#             print(f"No projects to upload")
#     except Exception:
#         print(f"Problems creating project with id:  {uid}")


# def create_dataV2(project_ids, data, _id_array):
#     _id = None
#     try:
#         for value in data:
#             data_dict = {}
#             _id = value["_id"]
#             validation_status = value.get("_validation_status", None)
#             if validation_status != {}:
#                 for a, b in _id_array:
#                     if _id == a:
#                         if validation_status["label"] != b:
#                             tableName = "data"
#                             query = f"UPDATE {tableName} SET validation = '{validation_status['label']}' WHERE _id = {_id} RETURNING id;"
#                             write_query(query)
#             results = list(zip(*_id_array))
#             if _id_array == [] or (_id_array != [] and _id not in results[0]):
#                 # Setting up generic variables for the registry
#                 data_dict["project_id"] = project_ids[0]
#                 data_dict["_id"] = value.get("_id", None)
#                 data_dict["_uuid"] = value.get("_uuid", None)
#                 if validation_status != {} or not None:
#                     data_dict["validation"] = validation_status.get("label")
#                 data_dict["submission"] = value.get("_submission_time", None)

#                 all_in_dict = {}
#                 # Setting up variables for json
#                 all_in_dict["nombre_instalacion"] = value.get(
#                     "group_trazabilidad/nombre_instalacion", None
#                 )
#                 all_in_dict["pais_instalacion"] = value.get(
#                     "group_trazabilidad/pais_instalacion", None
#                 )
#                 all_in_dict["depto_instalacion"] = value.get(
#                     "group_trazabilidad/depto_instalacion", None
#                 )
#                 all_in_dict["municipio_instalacion"] = value.get(
#                     "group_trazabilidad/municipio_instalacion", None
#                 )
#                 all_in_dict["nombre_etapa"] = value.get(
#                     "group_trazabilidad/nombre_etapa", None
#                 )
#                 all_in_dict["numero_etapa"] = value.get(
#                     "group_trazabilidad/numero_etapa", None
#                 )
#                 all_in_dict["ubicacion_instalacion"] = value.get(
#                     "group_trazabilidad/ubicacion_instalacion", None
#                 )
#                 all_in_dict["latitud_instalacion"] = value.get(
#                     "group_trazabilidad/latitud_instalacion", None
#                 )
#                 all_in_dict["longitud_instalacion"] = value.get(
#                     "group_trazabilidad/longitud_instalacion", None
#                 )
#                 all_in_dict["descripcion_instalacion"] = value.get(
#                     "group_trazabilidad/descripcion_instalacion", None
#                 )

#                 # for k, v in value.items():
#                 #     if k.startswith('group_trazabilidad'):
#                 #         all_in_dict[k] = v
#                 data_dict["json"] = all_in_dict
#                 tableName = "data"
#                 columns = list(data_dict.keys())
#                 values = []
#                 for value in data_dict.values():
#                     if type(value) == str:
#                         value = value.replace("'", "''")
#                         value = "'" + value + "'"
#                     if type(value) == dict:
#                         value = Json(value)
#                     if value == None:
#                         value = "NULL"
#                     values += [str(value)]

#                 query = f"INSERT INTO {tableName}"
#                 query += "(" + ", ".join(columns) + ")\nVALUES"
#                 query += "(" + ", ".join(values) + "), \n"
#                 query = query[:-3] + " RETURNING id;"
#                 write_query(query)

#     except Exception:
#         print(f"Problems creating the data:  {_id} of project {project_ids[0]}")


# def create_measurementsV2(project_ids, URL, data, meas_result):
#     try:
#         for value in data:
#             _id = value["_id"]
#             kobo_url = None
#             instance = None
#             picture_id = None
#             measurement_dict = {}
#             file_dict = {}
#             for keys, v in value.items():
#                 # if keys not in exclusions:
#                 family_group = "group_trazabilidad"
#                 if "foto" in keys:
#                     v = v.replace("(", "")
#                     v = v.replace(")", "")
#                     value_archive = unidecode(v.replace(" ", "_"))
#                     attachements = value.get("_attachments")  # type: ignore
#                     for attachment in attachements:
#                         if value_archive == attachment["filename"].split("/")[-1]:
#                             instance = attachment["instance"]
#                             picture_id = attachment["id"]
#                             kobo_url = f"{URL}{instance}/attachments/{picture_id}/"
#                     measurement_dict["project_id"] = project_ids[0]
#                     measurement_dict["_id"] = _id
#                     measurement_dict["measurement"] = None
#                     measurement_dict["value"] = None
#                     measurement_dict["file_name"] = value_archive
#                     measurement_dict["instance"] = instance
#                     measurement_dict["picture_id"] = picture_id
#                     measurement_dict["kobo_url"] = kobo_url

#                     #     file_dict[keys_archive] = [value_archive, instance, picture_id, download_url]
#                     # if family_group == keys.split('/')[0] and '_Arc' not in keys.split('/')[-1]:
#                     #     if v != [] or v != {}:
#                     #         measurement_name = keys.split('/')[-1].split('_')
#                     #         measurement_dict[measurement_name[0] + '_' + measurement_name[1]] = v
#                     #         keys_archive = measurement_name[0] + '_' + 'Arc'
#                     #         if family_group + '/' + keys_archive in value.keys():
#                     #             value_archive = value.get(family_group + '/' + keys_archive)
#                     #             value_archive = unidecode(value_archive.replace(" ", "_"))
#                     #         # if 'Arc' in keys:
#                     #             for attachment in value.get('_attachments'):
#                     #                 if value_archive == attachment['filename'].split('/')[-1]:
#                     #                     instance = attachment['instance']
#                     #                     picture_id = attachment['id']
#                     #                     download_url = f"{URL}{instance}/attachments/{picture_id}/"
#                     #             file_dict[keys_archive] = [value_archive, instance, picture_id, download_url]
#                     #         else:
#                     #             file_dict[keys_archive] = None
#                     # Create the first records in data table
#                     meas_ids = []
#                     meas_meas = []
#                     meas_values = []
#                     meas_files = []
#                     for meas in meas_result:
#                         meas_ids.append(meas[0])
#                         meas_meas.append(meas[1])
#                         meas_values.append(meas[2])
#                         meas_files.append(meas[3])

#                     tableName = "measurement"
#                     # for i, (measurement_name, file) in enumerate(zip(measurement_dict, file_dict)):
#                     #     v = "'" + measurement_dict.get(measurement_name, '').replace("'", "''") + "'"
#                     #     # v = measurement_dict.get(measurement_name)
#                     #     file_details = file_dict.get(file)
#                     #     file_name = 'NULL'
#                     #     instance = 'NULL'
#                     #     picture_id = 'NULL'
#                     #     kobo_url = 'NULL'
#                     #     if file_details is not None:
#                     #         file_name = "'" + file_details[0].replace("'", "''") + "'"
#                     #         instance = file_details[1]
#                     #         picture_id = file_details[2]
#                     #         kobo_url = "'" + file_details[3].replace("'", "''") + "'"

#                     if _id not in meas_ids:
#                         columns = list(measurement_dict.keys())
#                         values = []
#                         for field in measurement_dict.values():
#                             if type(field) == str:
#                                 field = field.replace("'", "''")
#                                 field = "'" + field + "'"
#                             if type(field) == dict:
#                                 field = Json(field)
#                             if field == None:
#                                 field = "NULL"
#                             values += [str(field)]

#                         query = f"INSERT INTO {tableName}"
#                         query += "(" + ", ".join(columns) + ")\nVALUES"
#                         query += "(" + ", ".join(values) + "), \n"
#                         query = query[:-3] + " RETURNING id;"
#                         write_query(query)

#     except Exception:
#         print("Problems creating the data")


# def create_data(project_ids, data, _id_array):
#     _id = None
#     try:
#         for value in data:
#             data_dict = {}
#             _id = value["_id"]
#             validation_status = value["_validation_status"]
#             if validation_status != {}:
#                 for a, b in _id_array:
#                     if _id == a:
#                         if validation_status["label"] != b:
#                             tableName = "data"
#                             query = f"UPDATE {tableName} SET validation = '{validation_status['label']}' WHERE _id = {_id} RETURNING id;"
#                             write_query(query)
#             results = list(zip(*_id_array))
#             if _id_array == [] or (_id_array != [] and _id not in results[0]):
#                 # Setting up generic variables for the registry
#                 data_dict["project_id"] = project_ids[0]
#                 data_dict["_id"] = value.get("_id", None)
#                 data_dict["_uuid"] = value.get("_uuid", None)
#                 data_dict["usuario"] = value.get(
#                     "group_presentacion/nombre_usuario", None
#                 )
#                 data_dict["role"] = value.get("group_presentacion/cargo_usuario", None)
#                 data_dict["dlocation"] = value.get(
#                     "group_presentacion/departamento_ubicacion", None
#                 )
#                 data_dict["mlocation"] = value.get(
#                     "group_presentacion/municipio_ubicacion", None
#                 )
#                 data_dict["gpslocation"] = value.get(
#                     "group_presentacion/ubicacion_usuario", None
#                 )
#                 data_dict["submission"] = value.get("_submission_time", None)
#                 validation_status = value.get("_validation_status", None)
#                 if validation_status != {} or not None:
#                     data_dict["validation"] = validation_status.get("label")
#                 all_in_dict = {}
#                 for k, v in value.items():
#                     if k.startswith("group_presentacion"):
#                         all_in_dict[k] = v
#                 data_dict["json"] = all_in_dict
#                 tableName = "data"
#                 columns = list(data_dict.keys())
#                 values = []
#                 for value in data_dict.values():
#                     if type(value) == str:
#                         value = value.replace("'", "''")
#                         value = "'" + value + "'"
#                     if type(value) == dict:
#                         value = Json(value)
#                     if value == None:
#                         value = "NULL"
#                     values += [str(value)]

#                 query = f"INSERT INTO {tableName}"
#                 query += "(" + ", ".join(columns) + ")\nVALUES"
#                 query += "(" + ", ".join(values) + "), \n"
#                 query = query[:-3] + " RETURNING id;"
#                 write_query(query)

#             # results = list(zip(*_id_array))
#             #     # if _id in results[0]:
#             #     #     for i, _id_in_array in enumerate(results[0]):
#             #     #         if _id == _id_in_array:
#             #     #             results[1][i]
#             #     # # print(list(enumerate(results[0])))
#             #     #     if _id_array[1] != 'Approved' and validation_status != {}:
#             #     #         tableName = 'data'
#             #     #         query = f"UPDATE {tableName} SET validation = '{validation_status['label']}' WHERE _id = {_id} RETURNING id;"
#             #     #         write_query(query)
#             # if results
#             # if _id not in results:

#     except Exception:
#         print(f"Problems creating the data:  {_id} of project {project_ids[0]}")


# def create_picture(data_result):
#     project_id = data_result[0]
#     _id = data_result[1]
#     data_id = data_result[2]
#     try:
#         # Check if existing pictures are present
#         tableName = "pictures"
#         query = f"SELECT picture_id FROM {tableName} WHERE project_id = '{project_id}' and data_id = '{data_id}'"
#         existing_pictures = read_query(query)
#         existing_pictures = list(zip(*existing_pictures))
#         if existing_pictures == []:
#             existing_pictures = [()]
#         tableName = "measurement"
#         query = f"SELECT id, file_name, instance, picture_id, kobo_url FROM {tableName} WHERE project_id = '{project_id}' and _id = '{_id}'"
#         picture_results = read_query(query)
#         for picture_result in picture_results:
#             measurement_id = picture_result[0]
#             file_name = picture_result[1]
#             instance = picture_result[2]
#             picture_id = picture_result[3]
#             kobo_url = picture_result[4]
#             if picture_id not in existing_pictures[0] and picture_id != None:
#                 rawResultImage = kobo_api(kobo_url)
#                 # Store pictures in folder
#                 rawResultImage.raw.decode_content = True
#                 file_path = "/home/ubuntu/getfair/pictures/" + file_name
#                 with open(file_path, "wb") as file:
#                     for chunk in rawResultImage.iter_content(chunk_size=16 * 1024):
#                         file.write(chunk)
#                     print("Image sucessfully Downloaded: ", file_name)
#                 # Upload picture in IPFS
#                 ipfs_result = ipfs(file_path)
#                 IPFS_HASH = ipfs_result["IpfsHash"]
#                 IPFS_HASH = "ipfs://" + IPFS_HASH
#                 # Update table with IPFS Hash
#                 # Insert picture data in table
#                 tableName = "pictures"
#                 columns = [
#                     "project_id",
#                     "data_id",
#                     "picture_id",
#                     "instance",
#                     "name",
#                     "url",
#                     "ipfshash",
#                 ]
#                 values = (
#                     str(project_id),
#                     str(data_id),
#                     str(picture_id),
#                     str(instance),
#                     str(file_name),
#                     str(kobo_url),
#                     str(IPFS_HASH),
#                 )
#                 insert_picture(tableName, columns, values)
#     except Exception:
#         print(f"Problems creating picture with data id:  {data_id}")


# def create_measurements(project_ids, URL, data, meas_result):
#     try:
#         for value in data:
#             _id = value["_id"]
#             # exclusions = [
#             #     "_id",
#             #     'formhub/uuid',
#             #     "group_presentacion/nombre_usuario",
#             #     "group_presentacion/nombre_usuario_other",
#             #     "group_presentacion/nombre_usuario_ts",
#             #     "group_presentacion/nombre_instalacion",
#             #     "group_presentacion/nombre_instalacion_other",
#             #     "group_presentacion/municipio_instalacion",
#             #     "group_presentacion/depto_instalacion",
#             #     "group_presentacion/year_dato",
#             #     "group_presentacion/mes_dato",
#             #     '__version__',
#             #     'meta/instanceID',
#             #     "meta/deprecatedID",
#             #     '_xform_id_string',
#             #     "_uuid",
#             #     '_attachments',
#             #     '_status',
#             #     '_geolocation',
#             #     "_submission_time",
#             #     '_tags',
#             #     '_notes',
#             #     "_validation_status",
#             #     "_submitted_by"
#             # ]
#             download_url = None
#             instance = None
#             picture_id = None
#             measurement_dict = {}
#             file_dict = {}
#             for keys, v in value.items():
#                 # if keys not in exclusions:
#                 family_group = "group_medidas"
#                 if (
#                     family_group == keys.split("/")[0]
#                     and "_Arc" not in keys.split("/")[-1]
#                 ):
#                     if v != [] or v != {}:
#                         measurement_name = keys.split("/")[-1].split("_")
#                         measurement_dict[
#                             measurement_name[0] + "_" + measurement_name[1]
#                         ] = v
#                         keys_archive = measurement_name[0] + "_" + "Arc"
#                         if family_group + "/" + keys_archive in value.keys():
#                             value_archive = value.get(family_group + "/" + keys_archive)
#                             value_archive = unidecode(value_archive.replace(" ", "_"))
#                             # if 'Arc' in keys:
#                             for attachment in value.get("_attachments"):
#                                 if (
#                                     value_archive
#                                     == attachment["filename"].split("/")[-1]
#                                 ):
#                                     instance = attachment["instance"]
#                                     picture_id = attachment["id"]
#                                     download_url = (
#                                         f"{URL}{instance}/attachments/{picture_id}/"
#                                     )
#                             file_dict[keys_archive] = [
#                                 value_archive,
#                                 instance,
#                                 picture_id,
#                                 download_url,
#                             ]
#                         else:
#                             file_dict[keys] = None
#             # Create the first records in data table
#             meas_ids = []
#             meas_meas = []
#             meas_values = []
#             meas_files = []
#             for meas in meas_result:
#                 meas_ids.append(meas[0])
#                 meas_meas.append(meas[1])
#                 meas_values.append(meas[2])
#                 meas_files.append(meas[3])

#             tableName = "measurement"
#             for i, (measurement_name, file) in enumerate(
#                 zip(measurement_dict, file_dict)
#             ):
#                 v = (
#                     "'"
#                     + measurement_dict.get(measurement_name, "").replace("'", "''")
#                     + "'"
#                 )
#                 # v = measurement_dict.get(measurement_name)
#                 file_details = file_dict.get(file)
#                 file_name = "NULL"
#                 instance = "NULL"
#                 picture_id = "NULL"
#                 kobo_url = "NULL"
#                 if file_details is not None:
#                     file_name = "'" + file_details[0].replace("'", "''") + "'"
#                     instance = file_details[1]
#                     picture_id = file_details[2]
#                     kobo_url = "'" + file_details[3].replace("'", "''") + "'"

#                 if _id not in meas_ids and measurement_name not in meas_meas:
#                     query = f"""INSERT INTO {tableName} (project_id, _id, measurement, value, file_name, instance, picture_id, kobo_url)
#                     VALUES ({project_ids[0]}, {_id}, '{measurement_name}', {v}, {file_name}, {instance}, {picture_id}, {kobo_url}) RETURNING id;
#                     """
#                     write_query(query)

#     except Exception:
#         print("Problems creating the data")


from sqlalchemy.orm import Session


def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_projects = db.query(dbmodels.User).offset(skip).limit(limit).all()
    if db_projects is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects


if __name__ == "__main__":
    TODAY = date.fromtimestamp(time.time())
    BASE_URL = "https://kf.kobotoolbox.org/api/v2/assets/"
    params = {"format": "json"}
    rawResult = kobo_api(BASE_URL, params)
    rawResult = json.loads(rawResult.content.decode("utf-8"))
    with open("./rawresult.json", "w") as file:
        json.dump(rawResult, file, indent=4, ensure_ascii=False)
    projects = rawResult.get("results", None)
    print(projects)

    try:
        tableName = "projects"
        query = f"SELECT uid FROM {tableName};"
        uids = read_query(query)
        uid_array = []
        if uids != [] or uids is not None:
            for uid in uids:
                uid_array.append(uid[0])

        project_id = create_projects(projects, uid_array)

        tableName = "projects"
        query = f"SELECT id, uid FROM {tableName};"
        project_query_result = read_query(query)
        for project_ids in project_query_result:
            project_id = project_ids[0]
            ASSET_UID = project_ids[1]
            if ASSET_UID == "aetorrJTocs2DgVfc5th8D":
                print(ASSET_UID)
            URL = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/data/"
            # QUERY = f'{{"_submission_time":{{"$gt":"{TODAY}"}}}}'
            params = {
                # "query": QUERY,
                "format": "json"
            }
            rawResult = kobo_api(URL, params)
            data = json.loads(rawResult.content.decode("utf-8"))
            with open("./data.json", "w") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            if "results" in data:
                data = data["results"]
            else:
                continue
            tableName = "data"
            query = f"SELECT _id, validation FROM {tableName};"
            _id_array = read_query(query)

            tableName = "measurement"
            query = f"SELECT _id, measurement, value, file_name FROM {tableName};"
            meas_result = read_query(query)

            if ASSET_UID == "a3pDRvFG2FNQwP8BeDAexS":
                create_dataV2(project_ids, data, _id_array)
                create_measurementsV2(project_ids, URL, data, meas_result)
            else:
                create_data(project_ids, data, _id_array)
                create_measurements(project_ids, URL, data, meas_result)
            # Check if there is data with the approved status
            tableName = "data"
            query = f"SELECT project_id, _id, id FROM {tableName} WHERE validation = 'Approved' and project_id='{project_id}';"
            data_results = read_query(query)
            if data_results != [] or data_results is not None:
                for data_result in data_results:
                    create_picture(data_result)
    except TypeError:
        print("No projects found in table projects")
