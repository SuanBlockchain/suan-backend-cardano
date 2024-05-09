#TODO: the minted amount must be limited by the amount of certified tokens during the swap transaction
#TODO: the swap contract must be part of the inputs of the transaction. Or the swap process is done in 2 steps. First receiving the request to the swap contract and then calling the 
# minting contract with the correct redeemer.

from opshin.prelude import *

@dataclass
class Mint(PlutusData):
    CONSTR_ID = 0
    
@dataclass
class Burn(PlutusData):
    CONSTR_ID = 1

#TODO: has_utxo does not work because the script is not really locked to create more tokens with the same name. We need to actually put the utxo as parameter and validate it as a fix value or simply limit the amount
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

def validator(oref: TxOutRef, pkh: PubKeyHash, tokenName: TokenName, redeemer: Union[Mint, Burn], context: ScriptContext
) -> None:

    purpose = context.purpose
    assert isinstance(purpose, Minting), "not minting purpose"

    tx_info = context.tx_info

    # Always check that the Master address has signed
    assert signedFromMaster(context, pkh), "Master's signature missing"
    # Always check token names
    assert check_token_name(context, tokenName), "Wrong token Name"

    if isinstance(redeemer, Mint):

        assert has_utxo(context, oref), "UTxO not consumed"

    elif isinstance(redeemer, Burn):
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