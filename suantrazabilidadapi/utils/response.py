from dataclasses import dataclass
from typing import Any


@dataclass()
class Response():
    """Class defined to process all type of responses, from database and from APIs"""

    def _response_success(self, response):
        if response["success"]:
            final_response = {
                "connection": True,
            }
        else:
            final_response = {
                "connection": False,
                "data": response["error"],
            }
        return final_response

    def handle_createWallet_response(self, createWallet_response: list[dict]) -> dict[str, Any]:
        response_success = self._response_success(createWallet_response)
        if response_success["connection"]:
            if not createWallet_response["data"].get("errors", None):
                response_success["success"] = True
            else:
                response_success["success"] = False
                response_success["data"] = createWallet_response["data"]["errors"]

        return response_success

    def handle_getWallet_response(self, getWallet_response: dict) -> dict[str, Any]:
        response_success = self._response_success(getWallet_response)
        if response_success["connection"]:
            if getWallet_response["data"].get("data", None) is not None:
                walletInfo = getWallet_response["data"]["data"]["getWallet"]

                if walletInfo is None:
                    response_success["success"] = False
                else:
                    response_success["success"] = True
                    response_success["data"] = walletInfo
            else:
                response_success["success"] = False
                response_success["data"] = getWallet_response["data"]["errors"]

        return response_success

    def handle_listWallets_response(self, listWallets_response: dict) -> dict[str, Any]:
        response_success = self._response_success(listWallets_response)
        if response_success["connection"]:
            if listWallets_response["data"].get("data", None) is not None:
                walletInfo = listWallets_response["data"]["data"]["listWallets"]

                if walletInfo["items"] == []:
                    response_success["success"] = False
                    response_success["data"] = []
                else:
                    response_success["success"] = True
                    response_success["data"] = walletInfo
            else:
                response_success["success"] = False
                response_success["data"] = listWallets_response["data"]["errors"]

        return response_success

    def handle_listMarketplaces_response(self, listMarketplaces_response: dict) -> dict[str, Any]:
        response_success = self._response_success(listMarketplaces_response)
        if response_success["connection"]:
            if listMarketplaces_response["data"].get("data", None) is not None:
                MarketplaceInfo = listMarketplaces_response["data"]["data"]["listMarketplaces"]

                if MarketplaceInfo["items"] == []:
                    response_success["success"] = False
                    response_success["data"] = listMarketplaces_response["data"]
                else:
                    response_success["success"] = True
                    response_success["data"] = MarketplaceInfo
            else:
                response_success["success"] = False
                response_success["data"] = listMarketplaces_response["data"]["errors"]

        return response_success

    def handle_getScript_response(self, getScript_response: dict) -> dict[str, Any]:
        response_success = self._response_success(getScript_response)
        if response_success["connection"]:
            if getScript_response["data"].get("data", None) is not None:
                scriptInfo = getScript_response["data"]["data"]["getScript"]

                if scriptInfo is None:
                    response_success["success"] = False
                else:
                    response_success["success"] = True
                    response_success["data"] = scriptInfo
            else:
                response_success["success"] = False
                response_success["data"] = getScript_response["data"]["errors"]

        return response_success

    def handle_createContract_response(self, createContractResponse: list[dict]) -> dict[str, Any]:
        response_success = self._response_success(createContractResponse)
        if response_success["connection"]:
            if not createContractResponse["data"].get("errors", None):
                response_success["success"] = True
            else:
                response_success["success"] = False
                response_success["data"] = createContractResponse["data"]["errors"]

        return response_success
