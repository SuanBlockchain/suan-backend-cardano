from dataclasses import dataclass
from typing import Any
from suantrazabilidadapi.utils.exception import ResponseDynamoDBException


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
    
    def _raise_check(self, response):
        if not response["connection"] or not response.get("success", None):
            raise ResponseDynamoDBException(response["data"])
    
    def handle_getGeneric_response(self, operation_name, getGeneric_response: dict) -> dict[str, Any]:
        response_success = self._response_success(getGeneric_response)
        if response_success["connection"]:
            if getGeneric_response["data"].get("data", None) is not None:
                walletInfo = getGeneric_response["data"]["data"][operation_name]

                if walletInfo is None:
                    response_success["success"] = False
                else:
                    response_success["success"] = True
                    response_success["data"] = walletInfo
            else:
                response_success["success"] = False
                response_success["data"] = getGeneric_response["data"]["errors"]

        self._raise_check(response_success)
        return response_success

    def handle_createWallet_response(self, createWallet_response: list[dict]) -> dict[str, Any]:
        response_success = self._response_success(createWallet_response)
        if response_success["connection"]:
            if not createWallet_response["data"].get("errors", None):
                response_success["success"] = True
            else:
                response_success["success"] = False
                response_success["data"] = createWallet_response["data"]["errors"]

        return response_success
    
    #TODO: Function to be decomissioned in the future. Move to genericGet
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

    #TODO: Function to be decomissioned in the future. Move to genericGet
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

    #TODO: Function to be decomissioned in the future. Move to genericGet
    def handle_getMerkleTree_response(self, getMerkleTree_response: dict) -> dict[str, Any]:
        response_success = self._response_success(getMerkleTree_response)
        if response_success["connection"]:
            if getMerkleTree_response["data"].get("data", None) is not None:
                merkleTreeInfo = getMerkleTree_response["data"]["data"]["getMerkleTree"]

                if merkleTreeInfo is None:
                    response_success["success"] = False
                else:
                    response_success["success"] = True
                    response_success["data"] = merkleTreeInfo
            else:
                response_success["success"] = False
                response_success["data"] = getMerkleTree_response["data"]["errors"]

        return response_success
    
    def handle_createMerkleTree_response(self, createMerkleTreeResponse: list[dict]) -> dict[str, Any]:
        response_success = self._response_success(createMerkleTreeResponse)
        if response_success["connection"]:
            if not createMerkleTreeResponse["data"].get("errors", None):
                response_success["success"] = True
                response_success["data"] = createMerkleTreeResponse["data"]["data"]["createMerkleTree"]
            else:
                response_success["success"] = False
                response_success["data"] = createMerkleTreeResponse["data"]["errors"]

        return response_success