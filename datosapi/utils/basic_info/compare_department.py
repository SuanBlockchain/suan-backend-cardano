import json
from prefect import flow, task
import httpx
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

@task
def get_department(url: str, params: dict = None):
    response = httpx.get(url, params=params)
    response.raise_for_status()
    return response.json()

@flow(log_prints=True)
def compare_files(department_file: str = f"{ROOT}/basic_info/department.json"):
    with open(department_file, "r") as file:
        json1 = json.load(file)

    URL = "https://geoportal.dane.gov.co/laboratorio/serviciosjson/gdivipola/servicios/departamentos.php"
    json2 = get_department(URL)

    if json1 == json2:
        print("Department info has not changed since last request")
    else:
        #TODO: write the result in an S3 file for consumption
        print(f"Department info has changed, update local file¡¡")


if __name__ == "__main__":
    compare_files.from_source(
        source= "https://github.com/larestrepo/suan-trazabilidad.git", entrypoint= "./datosapi/utils/basic_info/compare_department.py:compare_files"
    ).deploy(
        name="get-department", cron="0 0 * * *", tags=["department", "data"], version="department/data", description="Call endpoint to update the department mapping data",
        work_pool_name="my-managed-pool"
    )