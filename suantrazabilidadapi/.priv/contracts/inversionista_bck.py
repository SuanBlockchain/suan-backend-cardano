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
class DatumProjectParams(PlutusData):
    CONSTR_ID = 0
    beneficiary: bytes
    price: int

def check_single_utxo_spent(txins: List[TxInInfo], scriptAddr: Address) -> None:
    """To prevent double spending, count how many UTxOs are unlocked from the contract address"""
    count = 0

    for txi in txins:
        if txi.resolved.address == scriptAddr:
            count += 1
            # NFT token name should be the project name with the expected policyID
    assert count == 1, f"Only 1 contract utxo allowed but found {count}"

def check_owner_signed(signatories: List[PubKeyHash], owner: PubKeyHash) -> None:
    assert (
        owner in signatories
    ), f"Owner did not sign transaction, requires {owner.hex()} but got {[s.hex() for s in signatories]}"


def validator(token_policy_id: bytes, token_name: bytes, datum: DatumProjectParams, redeemer: Union[Buy, Unlist], context: ScriptContext) -> None:
    purpose = context.purpose
    tx_info = context.tx_info

    token = Token(token_policy_id, token_name)

    assert isinstance(purpose, Spending), f"Wrong script purpose: {purpose}"


    own_utxo = resolve_spent_utxo(tx_info.inputs, purpose)
    own_addr = own_utxo.address
    

    check_single_utxo_spent(tx_info.inputs, own_addr)

    # # It is recommended to explicitly check all options with isinstance for user input
    if isinstance(redeemer, Buy):

        ti = own_utxo.value.get(token.policy_id, {b"": 0}).get(token.token_name, 0)
        tf = sum(
            [
                x.value.get(token.policy_id, {b"": 0}).get(token.token_name, 0)
                for x in tx_info.outputs
                if x.address == own_addr
            ]
        )
        tb = ti - tf
        assert tb >= 0, "Not enough tokens to claim"
        payment = tb * datum.price

        """Check that the correct amount has been paid to the beneficiary (or more)"""
        res = False
        address_found = False
        for txo in tx_info.outputs:
            if txo.address.payment_credential.credential_hash == datum.beneficiary:
                address_found = True
                if txo.value.get(b"", {b"": 0}).get(b"", 0) >= payment:
                    res = True
        assert address_found, "beneficiary fee address not found in outputs"
        assert res, "Did not send required amount of lovelace to beneficiary"

        own_datum = own_utxo.datum
        if isinstance(own_datum, SomeOutputDatum):
            project_params: DatumProjectParams = own_datum.datum
            assert isinstance(project_params, DatumProjectParams)
            assert datum.beneficiary == project_params.beneficiary
            assert datum.price == project_params.price

    elif isinstance(redeemer, Unlist):
        True
    #     check_owner_signed(tx_info.signatories, datum.owner)
    else:
        assert False, "Wrong redeemer"