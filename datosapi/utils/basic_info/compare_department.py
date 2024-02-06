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
        print(f"Department info has changed, update local file¡¡")


if __name__ == "__main__":
    compare_files.serve(name="get-department")