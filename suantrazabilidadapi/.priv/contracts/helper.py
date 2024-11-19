from opshin.prelude import *

@dataclass
class Create(PlutusData):
    CONSTR_ID = 0


@dataclass
class Update(PlutusData):
    CONSTR_ID = 1

def assert_minting_purpose(context: ScriptContext) -> None:
    purpose = context.purpose
    if isinstance(purpose, Minting):
        is_minting = True
    else:
        is_minting = False
    assert is_minting, "not minting purpose"

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

def check_minted_amount(tn: TokenName, context: ScriptContext) -> bool:
    mint_value = context.tx_info.mint
    valid = False
    count = 0
    for policy_id in mint_value.keys():
        v = mint_value.get(policy_id, {b"": 0})
        if len(v.keys()) == 1:
            for token_name in v.keys():
                amount = v.get(token_name, 0)
                valid = token_name == tn and amount == 1
                if amount != 0:
                    count += 1
    return valid and count == 1

def validator(
    pkh: PubKeyHash, tn: TokenName, redeemer: Union[Create, Update], context: ScriptContext
) -> None:
    assert_minting_purpose(context)

    assert signedFromMaster(context, pkh), "Master's signature missing"

    if isinstance(redeemer, Create):
        assert check_minted_amount(tn, context), "wrong amount minted"

    assert check_token_name(context, tn), "Wrong token Name"

