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
                final_response = {
                    "success": True,
                    "msg": "Wallet created"
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error creating the wallet in table",
                }
        else:
            final_response = response_success
        return final_response

    def handle_getWallet_response(self, getWallet_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(getWallet_response)
        final_response = {}
        if response_success:
            if getWallet_response["data"].get("data", None) is not None:
                walletInfo = getWallet_response["data"]["data"]["getWallet"]

                if walletInfo is None:
                    final_response = {
                        "success": True,
                        "msg": "Wallet does not exist in DynamoDB",
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Wallet info",
                        "data": walletInfo,
                    }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                }
        else:
            final_response = response_success

        return final_response

    def handle_listWallets_response(self, listWallets_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(listWallets_response)
        final_response = {}
        if response_success:
            if listWallets_response["data"].get("data", None) is not None:
                walletInfo = listWallets_response["data"]["data"]["listWallets"]

                if walletInfo["items"] == []:
                    final_response = {
                        "success": True,
                        "msg": "Wallet does not exist in DynamoDB",
                        "data": listWallets_response["data"],
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Wallet info",
                        "data": walletInfo,
                    }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": listWallets_response["data"]["errors"],
                }
        else:
            final_response = response_success
        return final_response

    def handle_listMarketplaces_response(self, listMarketplaces_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(listMarketplaces_response)
        final_response = {}
        if response_success:
            if listMarketplaces_response["data"].get("data", None) is not None:
                MarketplaceInfo = listMarketplaces_response["data"]["data"]["listMarketplaces"]

                if MarketplaceInfo["items"] == []:
                    final_response = {
                        "success": True,
                        "msg": "Wallet does not exist in DynamoDB",
                        "data": listMarketplaces_response["data"],
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Wallet info",
                        "data": MarketplaceInfo,
                    }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": listMarketplaces_response["data"]["errors"],
                }
        else:
            final_response = response_success
        return final_response

    def handle_getScript_response(self, getScript_response: dict) -> dict[str, Any]:
        response_success = self._fetch_success(getScript_response)
        final_response = {}
        if response_success:
            if getScript_response["data"].get("data", None) is not None:
                scriptInfo = getScript_response["data"]["data"]["getScript"]

                if scriptInfo is None:
                    final_response = {
                        "success": True,
                        "msg": "Script does not exist in DynamoDB",
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Script info",
                        "data": scriptInfo,
                    }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                }
        else:
            final_response = response_success

        return final_response
