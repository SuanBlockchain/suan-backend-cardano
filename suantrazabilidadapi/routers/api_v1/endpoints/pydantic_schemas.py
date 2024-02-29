from enum import Enum
from typing import List, Union, Optional, Annotated
<<<<<<< HEAD
from datetime import datetime
from pydantic import UUID4, constr
=======
from pydantic import constr
from typing import Dict
>>>>>>> develop

from fastapi import Query

from pydantic import BaseModel, validator

from .examples import *


############################
# Wallet section definition
############################

<<<<<<< HEAD
class SourceName(str, Enum):
    balance = "balance"
=======
class walletCommandName(str, Enum):
    id = "id"
    address = "address"

class walletQueryParam(BaseModel):
    query_param: str
>>>>>>> develop

class Words(str, Enum):
    twelve: str = "12"
    fifteen: str = "15"
    eigthteen: str = "18"
    twenty_one: str = "21"
    twenty_four: str = "24"

class WalletStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class Wallet(BaseModel):
    save_flag: bool = True
    userID: str
    words: str

class WalletResponse(BaseModel):
    walletId: str
    mnemonics: List[str]


class KeyCreate(BaseModel):
    name: Union[str, None]
    size: int = 24
    save_flag: bool = True


class KeyRecover(BaseModel):
    name: Union[str, None]
    words: List[str]
    save_flag: bool = True


############################
# Transaction section definition
############################

class Metadata(BaseModel):
    metadata: List[Annotated[str, constr(max_length=64)]]

class AddressDestin(BaseModel):
    address: str
    lovelace: Optional[int] = 0
    multiAsset: Optional[list[Dict[str, Dict[str, int]]]] = None

<<<<<<< HEAD
class Metadata(BaseModel):
    metadata: List[Annotated[str, constr(max_length=64)]]

class BuildTx(Metadata):
    wallet_id: str
    addresses: list[AddressDestin]
=======
    @validator("address", always=True)
    def check_address(cls, value):
        if not value.startswith("addr_"):
            raise ValueError("Address format is not correct")

        return value

    @validator("lovelace", always=True)
    def check_lovelace(cls, value):
        if value < 0:
            raise ValueError("Lovelace must be positive")
        return value

    @validator("multiAsset", always=True)
    def check_multiAsset(cls, value):
        if not isinstance(value, list):
            raise ValueError("MultiAsset must be a list")
        return value

class BuildTx(Metadata):
    wallet_id: str
    addresses: list[AddressDestin]

class Buy(BaseModel):
    wallet_id: str
    tokenName: str
    metadata: dict[str, str]
    tokenAmount: int

class TokenGenesis(BaseModel):
    tokenName: str
    metadata: dict
    tokenAmount: int
>>>>>>> develop


class SignSubmit(Metadata):
<<<<<<< HEAD
=======
    wallet_id: str
    cbor: str

class PurchaseSignSubmit(BaseModel):
>>>>>>> develop
    wallet_id: str
    cbor: str
    metadata: dict


############################
# User section definition
############################
    
# class Tokens(BaseModel):
#     name: str
#     amount: int

# class Script(BaseModel):
#     name: str
#     type: str = "all"
#     required: int = 0
#     hashes: List[str]
#     type_time: str = ""
#     slot: int = 0

#     @validator("type", always=True)
#     def check_type(cls, value):
#         if value not in ("sig", "all", "any", "atLeast"):
#             raise ValueError("type must be: sig, all, any or atLeast ")
#         return value
<<<<<<< HEAD
    
=======

############################
# User section definition
############################
>>>>>>> develop
# class UserBase(BaseModel):
#     username: str


# class User(UserBase):
#     id: UUID4
#     id_wallet: Optional[str] = None
#     is_verified: bool
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         orm_mode = True


# class UserCreate(UserBase):
#     password: str


# class Token(BaseModel):
#     access_token: str
#     token_type: str


# class TokenData(BaseModel):
#     username: Union[str, None] = None





# class BuildTx(BaseModel):
#     address_origin: str
#     address_destin: list[AddressDestin]
#     metadata: Union[dict, None] = None
#     script_id: str = ""
#     mint: Union[list[Tokens], None] = None
#     witness: int = 1

#     @validator("script_id", always=True)
#     def chekc_script_id(cls, value):
#         try:
#             if value != "":
#                 uuid.UUID(value)
#         except ValidationError as e:
#             print(e)
#         return value


# class SimpleSign(BaseModel):
#     wallets_ids: list[str]


# class SignCommandName(str, Enum):
#     cborhex = "cborhex"
#     txfile = "txfile"


# class Mint(BuildTx):
#     script_id: str
#     tokens: list[Tokens]

    # @validator("script_id", always=True)
    # def chekc_script_id(cls, value):
    #     assert isinstance(value, UUID4), "Script_id field must be a valid UUID4"
    #     return value

############################
# Source section definition
############################
<<<<<<< HEAD

=======
>>>>>>> develop

############################
# Script section definition
############################


# class Script(BaseModel):
#     name: str
#     type: str = "all"
#     required: int = 0
#     hashes: List[str]
#     type_time: str = ""
#     slot: int = 0

#     @validator("type", always=True)
#     def check_type(cls, value):
#         if value not in ("sig", "all", "any", "atLeast"):
#             raise ValueError("type must be: sig, all, any or atLeast ")
#         return value

#     @validator("required", always=True)
#     def check_required(cls, value, values):
#         if values["type"] == "atLeast":
#             assert isinstance(
#                 value, int
#             ), "Required field must be integer if type atLeast is used"
#             assert (
#                 value > 0
#             ), "Required field must be higher than 0 and be equal to the number of specified keyHashes"
#         return value

#     @validator("hashes", always=True)
#     def check_hashes(cls, value, values):
#         if values["type"] == "atLeast":
#             assert (
#                 len(value) >= values["required"]
#             ), "Number of keyshashes should be atLeast equal to the number of required keyHashes"
#         return value

#     @validator("slot", always=True)
#     def check_slot(cls, value, values):
#         if values["type_time"] in ("before", "after"):
#             assert isinstance(
#                 value, int
#             ), "Slot field must be integer if type before/after is used"
#             assert (
#                 value > 0
#             ), "At least it should be greater than 0 or the current slot number"
#             return value
#         else:
#             return None


# class ScriptPurpose(str, Enum):
#     mint = "mint"
#     multisig = "multisig"