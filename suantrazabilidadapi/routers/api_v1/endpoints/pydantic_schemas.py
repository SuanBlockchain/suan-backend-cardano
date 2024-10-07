from enum import Enum
from typing import Any, Dict, List, Optional, Union

from opshin.prelude import *
from pydantic import BaseModel, constr, validator

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


# class Wallet(BaseModel):
#     save_flag: bool = True
#     userID: str = ""
#     words: str

class walletType(str, Enum):
    """"""
    user: str = "user"
    oracle = "oracle"


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


class TempDatum(BaseModel):
    beneficiary: str


class AddressDestin(BaseModel):
    address: Optional[str] = None
    lovelace: Optional[int] = 0
    multiAsset: Optional[list[Asset]] = None
    datum: Optional[TempDatum] = None  # TODO: make datum more generic

    # @validator("address", always=True)
    # def check_address(cls, value):
    #     if not value.startswith("addr"):
    #         raise ValueError("Address format is not correct")
    #     return value

    # @validator("lovelace", always=True)
    # def check_lovelace(cls, value):
    #     if value < 0:
    #         raise ValueError("Lovelace must be positive")
    #     return value


class Mint(BaseModel):
    asset: Asset


class MintRedeem(str, Enum):
    mint = "Mint"
    burn = "Burn"


class BuildTx(BaseModel):
    wallet_id: str
    addresses: Optional[list[AddressDestin]]
    metadata: Optional[Dict[str, Dict[str, Any]]] = None


class Utxo(BaseModel):
    transaction_id: str
    index: int


class TokenGenesis(BaseModel):
    wallet_id: str
    utxo: Utxo
    addresses: Optional[list[AddressDestin]]
    metadata: Optional[Dict[str, Dict[str, Any]]] = None
    mint: Optional[Mint] = None


class ClaimRedeem(str, Enum):
    buy = "Buy"
    sell = "Sell"
    unlist = "Unlist"


class Claim(BaseModel):
    wallet_id: str
    spendPolicyId: str
    addresses: list[AddressDestin]
    metadata: Optional[Dict[str, Dict[str, Any]]] = None


class SignSubmit(BaseModel):
    wallet_id: str
    cbor: str
    scriptIds: Optional[list[str]] = None
    redeemers_cbor: Optional[list[str]] = None
    metadata_cbor: Optional[str] = None


class Index(BaseModel):
    policy_id: str
    token: str
    price: int


class Oracle(BaseModel):
    data: List[Index]
    validity: POSIXTime


class OracleAction(str, Enum):
    create = "Create"
    update = "Update"


class UnlockOrder(BaseModel):
    wallet_id: str
    orderPolicyId: str
    utxo: Utxo
    addresses: list[AddressDestin]
    metadata: Optional[Dict[str, Dict[str, Any]]] = None


class Order(BaseModel):
    wallet_id: str
    orderPolicyId: str
    tokenA: Token
    qtokenA: int
    price: int
    tokenB: Token
    metadata: Optional[Dict[str, Dict[str, Any]]] = None


############################
# Contracts section definition
############################


class ScriptType(str, Enum):
    native = "native"
    mintSuanCO2 = "mintSuanCO2"
    mintProjectToken = "mintProjectToken"
    spendSwap = "spendSwap"
    spendProject = "spendProject"


@dataclass
class RedeemerMint(PlutusData):
    CONSTR_ID = 0


@dataclass
class RedeemerBurn(PlutusData):
    CONSTR_ID = 1


@dataclass
class RedeemerBuy(PlutusData):
    # Redeemer to buy the listed values
    CONSTR_ID = 0


@dataclass
class RedeemerSell(PlutusData):
    # Redeemer to sell the listed values
    CONSTR_ID = 1


@dataclass
class RedeemerUnlist(PlutusData):
    # Redeemer to unlist the listed values
    CONSTR_ID = 2


@dataclass
class DatumProjectParams(PlutusData):
    CONSTR_ID = 0
    beneficiary: bytes


@dataclass
class DatumSwap(PlutusData):
    CONSTR_ID = 0
    owner: bytes
    order_side: Union[RedeemerBuy, RedeemerSell]
    tokenA: Token
    tokenB: Token
    price: int


@dataclass
class TokenFeed(PlutusData):
    CONSTR_ID = 0
    tokenName: bytes
    price: int


@dataclass
class DatumOracle(PlutusData):
    CONSTR_ID = 0
    value_dict: Dict[bytes, TokenFeed]
    identifier: bytes
    validity: POSIXTime
    # signature: bytes


class contractCommandName(str, Enum):
    id = "id"
    # address = "address"


############################
# Projects section definition
############################


class projectCommandName(str, Enum):
    id = "id"
