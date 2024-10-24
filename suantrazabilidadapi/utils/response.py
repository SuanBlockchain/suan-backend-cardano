from dataclasses import dataclass
from typing import Any


@dataclass()
class Response():
    """Class defined to process all type of responses, from database and from APIs"""

    def _fetch_success(self, response):
        if response["success"]:
            return True
        final_response = {
            "success": False,
            "msg": "Problems connecting to DynamoDB",
            "data": response["error"],
        }
        return final_response

    def handle_createWallet_response(self, createWallet_response: list[dict]) -> dict[str, Any]:
        response_success = self._fetch_success(createWallet_response)
        if response_success:
            if not createWallet_response["data"].get("errors", None):
                response_success["msg"] = "Wallet created"
            else:
                response_success["msg"] = "Error creating the wallet in table"
                response_success["data"] = createWallet_response["data"]["errors"]

        return response_success

    def handle_getWallet_response(self, getWallet_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(getWallet_response)
        if response_success:
            if getWallet_response["data"].get("data", None) is not None:
                walletInfo = getWallet_response["data"]["data"]["getWallet"]

                if walletInfo is None:
                    response_success["msg"] = "Wallet does not exist in DynamoDB"
                else:
                    response_success["msg"] = "Wallet info"
                    response_success["data"] = walletInfo
            else:
                response_success["msg"] = "Error fetching data"
                response_success["data"] = getWallet_response["data"]["errors"]

        return response_success

    def handle_listWallets_response(self, listWallets_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(listWallets_response)
        if response_success:
            if listWallets_response["data"].get("data", None) is not None:
                walletInfo = listWallets_response["data"]["data"]["listWallets"]

                if walletInfo["items"] == []:
                    response_success["msg"] = "Wallet does not exist in DynamoDB"
                    response_success["data"] = listWallets_response["data"]
                else:
                    response_success["msg"] = "Wallet info"
                    response_success["data"] = walletInfo
            else:
                response_success["msg"] = "Error fetching data"
                response_success["data"] = listWallets_response["data"]["errors"]

        return response_success

    def handle_listMarketplaces_response(self, listMarketplaces_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(listMarketplaces_response)
        if response_success:
            if listMarketplaces_response["data"].get("data", None) is not None:
                MarketplaceInfo = listMarketplaces_response["data"]["data"]["listMarketplaces"]

                if MarketplaceInfo["items"] == []:
                    response_success["msg"] = "Wallet does not exist in DynamoDB"
                    response_success["data"] = listMarketplaces_response["data"]
                else:
                    response_success["msg"] = "Wallet info"
                    response_success["data"] = MarketplaceInfo
            else:
                response_success["msg"] = "Error fetching data"
                response_success["data"] = listMarketplaces_response["data"]["errors"]

        return response_success

    def handle_getScript_response(self, getScript_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(getScript_response)
        if response_success:
            if getScript_response["data"].get("data", None) is not None:
                scriptInfo = getScript_response["data"]["data"]["getScript"]

                if scriptInfo is None:
                    response_success["msg"] = "Script does not exist in DynamoDB"
                else:
                    response_success["msg"] = "Script info"
                    response_success["data"] = scriptInfo
            else:
                response_success["msg"] = "Error fetching data"
                response_success["data"] = getScript_response["data"]["errors"]

        return response_success

    def handle_createContract_response(self, createContractResponse: list[dict]) -> dict[str, Any]:
        response_success = self._fetch_success(createContractResponse)
        if response_success:
            if not createContractResponse["data"].get("errors", None):
                response_success["msg"] = "Script Created"
            else:
                response_success["msg"] = "Error creating the script in table"
                response_success["data"] = createContractResponse["data"]["errors"]

        return response_success
