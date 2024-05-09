from opshin.prelude import *
@dataclass
class Mint(PlutusData):
    CONSTR_ID = 0
    
@dataclass
class Burn(PlutusData):
    CONSTR_ID = 1

def assert_minting_purpose(context: ScriptContext) -> None:
    purpose = context.purpose
    if isinstance(purpose, Minting):
        is_minting = True
    else:
        is_minting = False
    assert is_minting, "not minting purpose"

def signedToBeneficiary(context: ScriptContext, pkh: PubKeyHash) -> bool:
    return pkh in context.tx_info.signatories

def check_minted_amount(context: ScriptContext, tn: TokenName, q: int) -> bool:
    mint_value = context.tx_info.mint
    valid = False
    count = 0
    for policy_id in mint_value.keys():
        v = mint_value.get(policy_id, {b"": 0})
        if len(v.keys()) == 1:
            for token_name in v.keys():
                amount = v.get(token_name, 0)
                valid = token_name == tn and amount == q
                if amount != 0:
                    count += 1
    return valid and count == 1


def check_token_name(context: ScriptContext, tn: TokenName) -> bool:
    mint_value = context.tx_info.mint
    valid = False
    for policy_id in mint_value.keys():
        v = mint_value.get(policy_id, {b"": 0})
        if len(v.keys()) == 1:
            for token_name in v.keys():
                valid = token_name == tn
    return valid

def validator(pkh: PubKeyHash, tokenName: TokenName, redeemer: Union[Mint, Burn], context: ScriptContext
) -> None:
    assert_minting_purpose(context)
    assert signedToBeneficiary(context, pkh), "beneficiary's signature missing"
    assert check_token_name(context, tokenName), "wrong amount minted"
    if isinstance(redeemer, Mint):
        quantity = 1
    elif isinstance(redeemer, Burn):
        quantity = -1
    assert check_minted_amount(context, tokenName, quantity)