from enum import Enum
from typing import List, Union, Optional, Annotated
from pydantic import constr
from typing import Dict

from pydantic import BaseModel, validator

from .examples import *
from opshin.prelude import *


############################
# Wallet section definition
############################

class walletCommandName(str, Enum):
    id = "id"
    address = "address"

class walletQueryParam(BaseModel):
    query_param: str

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
    userID: str = ""
    words: str
    save_local: bool = False
    localName: str = ...

    @validator("localName", always=True)
    def check_local(cls, value, values):
        save_local = values.get("save_local")
        if save_local and (value == "" or value == "string"):
            raise ValueError("if save_local is True, provide localName")
        return value

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

class Asset(BaseModel):
    policyid: str
    tokens: Dict[str, int]

class AddressDestin(BaseModel):
    address: str
    lovelace: Optional[int] = 0
    multiAsset: Optional[list[Asset]] = None

    @validator("address", always=True)
    def check_address(cls, value):
        if not value.startswith("addr"):
            raise ValueError("Address format is not correct")
        return value

    @validator("lovelace", always=True)
    def check_lovelace(cls, value):
        if value < 0:
            raise ValueError("Lovelace must be positive")
        return value

class Mint(BaseModel):
    asset: Asset
    redeemer: Optional[int] = 0


class BuildTx(BaseModel):
    wallet_id: str
    addresses: list[AddressDestin]
    metadata: Optional[List[Annotated[str, constr(max_length=64)]]] = None

class TokenGenesis(BaseModel):
    wallet_id: str
    addresses: list[AddressDestin]
    metadata: Optional[List[Annotated[str, constr(max_length=64)]]] = None
    mint: Optional[Mint] = None

class Buy(BaseModel):
    wallet_id: str
    tokenName: str
    metadata: dict[str, str]
    tokenAmount: int

class Tokens(BaseModel):
    name: str
    amount: int

class SignSubmit(BaseModel):
    wallet_id: str
    cbor: str
    metadata: Optional[List[Annotated[str, constr(max_length=64)]]] = None

class PurchaseSignSubmit(BaseModel):
    wallet_id: str
    cbor: str
    metadata: dict

############################
# Contracts section definition
############################

class ScriptType(str, Enum):
    native = "native"
    mintSuanCO2 = "mintSuanCO2"
    mintProjectToken = "mintProjectToken"
    spend = "spend"
    any = "any"


@dataclass()
class ReferenceParams(PlutusData):
    CONSTR_ID = 0
    tokenName: bytes
    suanpkh: PubKeyHash


class contractCommandName(str, Enum):
    id = "id"
    # address = "address"