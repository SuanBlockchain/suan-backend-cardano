import json
import os
import pathlib

import httpx
from rocketry import Grouper
from rocketry.conds import daily, minutely

ROOT = pathlib.Path(__file__).resolve().parent.parent


group = Grouper()


def get_department(url: str, params: dict = None):
    response = httpx.get(url, params=params)
    response.raise_for_status()
    return response.json()


# @group.task(daily(at="00:00"))
@group.task(minutely)
async def compare_files():
    json1 = {}
    department_file = f"./datosapi/app/basic_info/department.json"
    if os.path.exists(department_file):
        with open(department_file, "r") as file:
            json1 = json.load(file)

    URL = "https://geoportal.dane.gov.co/laboratorio/serviciosjson/gdivipola/servicios/departamentos.php"
    json2 = get_department(URL)

    if json1 == json2:
        print("Department info has not changed since last request")
    else:
        print(f"Department info has changed, update local file¡¡")
        with open(department_file, "w") as file:
            json.dump(json2, file)
