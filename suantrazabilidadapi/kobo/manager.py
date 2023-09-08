from typing import Union
from dataclasses import dataclass, field
import os


import requests

from .form import KoboForm
from suantrazabilidadapi.core.config import config

@dataclass()
class Manager():
    kobo_tokens_dict = config(section="kobo")
    # headers = CaseInsensitiveDict()

    url: str = field(init=True, default="https://kf.kobotoolbox.org/")
    api_version: int = field(init=True, default=2)
    headers: dict = field(init=False)
    token: str = field(init=False)


    def __post_init__(self) -> None:
        self.SUANBLOCKCHAIN = "suanblockchain"
        self.desc_name_1 = "revision"
        self.desc_name_2 = "version"
        self.url = self.url.rstrip("/")
        self.api_version = self.api_version
        if self.api_version != 2:
            raise ValueError("The value of 'api_version' has to be: 2")
        # self.token = self.kobo_tokens_dict["kobo_token"]
        self.token = os.getenv('kobo_token')
        self.headers: dict = {"Authorization": f"Token {self.token}"}
        self._assets = None

    def _fetch_forms(self) -> None:
        """Fetch the list of forms the user has access to with its token."""
        url_assets = f"{self.url}/api/v{self.api_version}/assets.json"

        res = requests.get(url=url_assets, headers=self.headers)

        # If error while fetching the data, return an empty list
        if res.status_code != 200:
            return []

        results = res.json()["results"]
        # It seems that when uploading an XLSForm from the website to create
        # a new form and there is an issue during the upload, the form
        # will be visible in the API but not in the UI. In this case it will
        # have the property "asset_type" set to "empty" instead of "survey"
        # for a working form. We don't want to keep them so we filter them out.
        # This issue seems to be very rare.
        results = [r for r in results if r["asset_type"] != "empty"]

        return results

    def _create_koboform(self, form: dict) -> KoboForm:
        kform = KoboForm(uid=form["uid"])
        kform._extract_from_asset(form)
        kform.headers = self.headers

        return kform

    def get_forms(self) -> list:
        if not self._assets:
            self._assets = self._fetch_forms()

        kforms = []
        for form in self._assets:
            kform = self._create_koboform(form)
            kforms.append(kform)
        return kforms

    def get_form(self, uid: str) -> Union[KoboForm, None]:
        if not self._assets:
            self._assets = self._fetch_forms()

        # If no forms
        if self._assets == []:
            return None

        form_list = [f for f in self._assets if f["uid"] == uid]

        if len(form_list) == 0:
            raise ValueError(f"There is no form with the uid: {uid}.")

        form = form_list[0]
        kform = self._create_koboform(form)

        return kform
    
    def filter_form(self, forms) -> list:
     
        form_list = []

        for form in forms:

            deployment_active = form.metadata["deployment__active"]
            has_deployment = form.metadata["has_deployment"]
            owner = form.metadata["owner"]
            name = form.metadata["name"]
            # Filter forms active, deployed and owner username = 'suanblockchain'
            if deployment_active and has_deployment and owner == self.SUANBLOCKCHAIN and self.desc_name_1 in name and self.desc_name_2 in name:
                form_list.append(form)

        return form_list
    