#TODO: the minted amount must be limited by the amount of certified tokens during the swap transaction
#TODO: the swap contract must be part of the inputs of the transaction. Or the swap process is done in 2 steps. First receiving the request to the swap contract and then calling the 
# minting contract with the correct redeemer.

from opshin.prelude import *

def assert_minting_purpose(context: ScriptContext) -> None:
    purpose = context.purpose
    if isinstance(purpose, Minting):
        is_minting = True
    else:
        is_minting = False
    assert is_minting, "not minting purpose"

def signedToBeneficiary(context: ScriptContext, pkh: PubKeyHash) -> bool:
    return pkh in context.tx_info.signatories

# def has_utxo(context: ScriptContext, params: ReferenceParams) -> bool:
#     return any([oref == i.out_ref for i in context.tx_info.inputs])


def check_token_name(context: ScriptContext, tn: TokenName) -> bool:
    mint_value = context.tx_info.mint
    valid = False
    for policy_id in mint_value.keys():
        v = mint_value.get(policy_id, {b"": 0})
        if len(v.keys()) == 1:
            for token_name in v.keys():
                valid = token_name == tn
    return valid

#test
def validator(pkh: PubKeyHash, tokenName: TokenName, redeemer: None, context: ScriptContext
) -> None:
    assert_minting_purpose(context)
    assert signedToBeneficiary(context, pkh), "beneficiary's signature missing"
    assert check_token_name(context, tokenName), "wrong amount minted"