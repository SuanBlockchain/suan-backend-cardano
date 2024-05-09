#!/usr/bin/env -S opshin eval spending
from opshin.prelude import *

@dataclass
class Buy(PlutusData):
    # Redeemer to buy the listed values
    CONSTR_ID = 0

@dataclass
class Unlist(PlutusData):
    # Redeemer to unlist the values
    CONSTR_ID = 1

@dataclass
class TokenFeed(PlutusData):
    CONSTR_ID=0
    tokenName: bytes
    price: int

@dataclass
class DatumOracle(PlutusData):
    CONSTR_ID = 0
    value_dict: Dict[bytes, TokenFeed]
    identifier: bytes
    validity: POSIXTime

@dataclass
class DatumProjectParams(PlutusData):
    CONSTR_ID = 0
    beneficiary: bytes

# oracle_policy_id = b'\xbe\xe9e\x17\xf9\xda\xb2u5\x8a\x14\x13Q\xf4\x01\x0b\x07}Y\x97\xd3\x82C\x06\x04\x93\x8b\x9a' #For internal test
# oracle_policy_id = b"\xb1\x1a6}a\xa2\xb8\xf6\xa7pI\xa8\t\xd7\xb9<mD\xc1@g\x8di'j\xb7|\x12"

def check_owner_signed(signatories: List[PubKeyHash], owner: PubKeyHash) -> None:
    assert (
        owner in signatories
    ), f"Owner did not sign transaction, requires {owner.hex()} but got {[s.hex() for s in signatories]}"

def check_correct_amount(outputs: List[TxOut], datum: DatumProjectParams, payment: int) -> None:
    """Check that the correct amount has been paid to the beneficiary (or more)"""
    res = False
    address_found = False
    for txo in outputs:
        if txo.address.payment_credential.credential_hash == datum.beneficiary:
            address_found = True
            if txo.value.get(b"", {b"": 0}).get(b"", 0) >= payment:
                res = True
    assert address_found, "beneficiary fee address not found in outputs"
    assert res, "Did not send required amount of lovelace to beneficiary"

def token_balance(outputs: List[TxOut], own_utxo: TxOut, own_addr: Address, token_policy_id: bytes, token_name: bytes) -> int:
    # Get the project token @input from the spend contract
    ti = own_utxo.value.get(token_policy_id, {b"": 0}).get(token_name, 0)
    # Get the project token sent back to the spend contract
    tf = sum(
        [
            x.value.get(token_policy_id, {b"": 0}).get(token_name, 0)
            for x in outputs
            if x.address == own_addr
        ]
    )
    tb = ti - tf
    return tb

def check_datum_price(oracle_datum: DatumOracle, token_policy_id: bytes, token_name: bytes, token_balance: int, outputs: List[TxOut], datum: DatumProjectParams) -> None:
    price = 0
    values = oracle_datum.value_dict
    token_info: TokenFeed = values[token_policy_id]

    if isinstance(token_info, TokenFeed):
        name: bytes = token_info.tokenName
        if name == token_name:
            price: int = token_info.price
    assert price > 0, "Price index for token not found"
    payment = token_balance * price
    check_correct_amount(outputs, datum, payment)

def check_oracle_datum(reference_inputs: List[TxInInfo], oracle_policy_id: bytes, token_policy_id: bytes, token_name: bytes, token_balance: int, outputs: List[TxOut], datum: DatumProjectParams) -> None:
    oracle_policy_found = False
    for reference_input in reference_inputs:
        reference_script = reference_input.resolved.reference_script 
        if isinstance(reference_script, NoScriptHash):
            values = reference_input.resolved.value
            if any([value > 0 for value in values.get(oracle_policy_id, {b"": 0}).values()]):
                oracle_policy_found = True
                reference_input_datum = reference_input.resolved.datum
                if isinstance(reference_input_datum, SomeOutputDatum):
                    oracle_datum: DatumOracle = reference_input_datum.datum
    assert oracle_policy_found, "No reference input with oracle token"
    assert isinstance(oracle_datum, DatumOracle), "No datum contained in reference input"
    check_datum_price(oracle_datum, token_policy_id, token_name, token_balance, outputs, datum)

def check_datum_constant(own_datum: OutputDatum, datum: DatumProjectParams) -> None:
    """Check that the datum is not modified"""
    res = False
    if isinstance(own_datum, SomeOutputDatum):
        project_params: DatumProjectParams = own_datum.datum
        if isinstance(project_params, DatumProjectParams):
            if datum.beneficiary == project_params.beneficiary:
                res = True
    assert res, "Datum must be kept constant"

def validator(oracle_policy_id: bytes, token_policy_id: bytes, token_name: bytes, datum: DatumProjectParams, redeemer: Union[Buy, Unlist], context: ScriptContext) -> None:
    purpose = context.purpose
    tx_info = context.tx_info

    assert isinstance(purpose, Spending), f"Wrong script purpose: {purpose}"

    own_utxo = resolve_spent_utxo(tx_info.inputs, purpose)
    own_addr = own_utxo.address

    # # It is recommended to explicitly check all options with isinstance for user input
    if isinstance(redeemer, Buy):
        tb = token_balance(tx_info.outputs, own_utxo, own_addr, token_policy_id, token_name)
        assert tb >= 0, "Not enough tokens to claim"

        check_oracle_datum(tx_info.reference_inputs, oracle_policy_id, token_policy_id, token_name, tb, tx_info.outputs, datum)

        check_datum_constant(own_utxo.datum, datum)

    elif isinstance(redeemer, Unlist):
        True
        # check_owner_signed(tx_info.signatories, datum.beneficiary)
    else:
        assert False, "Wrong redeemer"