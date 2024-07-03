from opshin.prelude import *


@dataclass
class Mint(PlutusData):
    CONSTR_ID = 0


@dataclass
class Burn(PlutusData):
    CONSTR_ID = 1


def has_utxo(context: ScriptContext, oref: TxOutRef) -> bool:
    return any([oref == i.out_ref for i in context.tx_info.inputs])


def signedFromMaster(context: ScriptContext, pkh: PubKeyHash) -> bool:
    return pkh in context.tx_info.signatories


def check_token_name(context: ScriptContext, tn: TokenName) -> bool:
    mint_value = context.tx_info.mint
    valid = False
    for policy_id in mint_value.keys():
        v = mint_value.get(policy_id, {b"": 0})
        if len(v.keys()) == 1:
            for token_name in v.keys():
                valid = token_name == tn
    return valid


def validator(
    oref: TxOutRef,
    pkh: PubKeyHash,
    redeemer: Union[Mint, Burn],
    context: ScriptContext,
) -> None:
    tokenName = b"SUANCO2"
    purpose = context.purpose
    assert isinstance(purpose, Minting), "not minting purpose"

    tx_info = context.tx_info

    # Always check that the Master address has signed
    assert signedFromMaster(context, pkh), "Master's signature missing"
    # Always check token name
    assert check_token_name(context, tokenName), "Wrong token Name"

    if isinstance(redeemer, Mint):
        assert has_utxo(context, oref), "UTxO not consumed"

    if isinstance(redeemer, Burn):
        assert (
            sum(
                [
                    sum(o.value.get(purpose.policy_id, {b"": 0}).values())
                    for o in tx_info.outputs
                ]
            )
            == 0
        ), "Can not send tokens anywhere as output"

    else:
        assert False, "Wrong redeemer"
