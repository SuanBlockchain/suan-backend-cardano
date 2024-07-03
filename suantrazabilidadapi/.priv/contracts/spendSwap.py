# TODO: allow partial spends
# if the utxo is valid, it must contain a token to swap avaiable in the list from the inline datum in oracle. The price is free to set for the time being, so oracle is only used to check the list of valid
# Tokens to list as valid orders.
#!/usr/bin/env -S opshin eval spending
from opshin.prelude import *


@dataclass
class Buy(PlutusData):
    CONSTR_ID = 0
    # nft_token: Token


@dataclass
class Sell(PlutusData):
    CONSTR_ID = 1


@dataclass
class Unlist(PlutusData):
    # Redeemer to unlist the values
    CONSTR_ID = 2


ListingAction = Union[Buy, Sell, Unlist]


@dataclass
class DatumSwap(PlutusData):
    CONSTR_ID = 0
    owner: bytes
    order_side: Union[Buy, Sell]
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


def check_token_in_datum(
    oracle_datum: DatumOracle, token_policy_id: bytes, token_name: bytes
) -> None:
    values = oracle_datum.value_dict
    token_info: TokenFeed = values[token_policy_id]

    if isinstance(token_info, TokenFeed):
        name: bytes = token_info.tokenName
    assert name == token_name, "Token not found in oracle list"


def check_oracle_datum(
    reference_inputs: List[TxInInfo],
    oracle_policy_id: bytes,
    token_policy_id: bytes,
    token_name: bytes,
) -> None:
    oracle_policy_found = False
    for reference_input in reference_inputs:
        reference_script = reference_input.resolved.reference_script
        if isinstance(reference_script, NoScriptHash):
            values = reference_input.resolved.value
            if any(
                [value > 0 for value in values.get(oracle_policy_id, {b"": 0}).values()]
            ):
                oracle_policy_found = True
                reference_input_datum = reference_input.resolved.datum
                if isinstance(reference_input_datum, SomeOutputDatum):
                    oracle_datum: DatumOracle = reference_input_datum.datum
    assert oracle_policy_found, "No reference input with oracle token"
    assert isinstance(
        oracle_datum, DatumOracle
    ), "No datum contained in reference input"
    check_token_in_datum(oracle_datum, token_policy_id, token_name)


def check_owner_signed(signatories: List[PubKeyHash], owner: PubKeyHash) -> None:
    assert (
        owner in signatories
    ), f"Owner did not sign transaction, requires {owner.hex()} but got {[s.hex() for s in signatories]}"


def validator(
    oracle_policy_id: bytes,
    datum: DatumSwap,
    redeemer: ListingAction,
    context: ScriptContext,
) -> None:
    purpose = context.purpose
    tx_info = context.tx_info

    assert isinstance(purpose, Spending), f"Wrong script purpose: {purpose}"

    own_utxo = resolve_spent_utxo(tx_info.inputs, purpose)
    own_addr = own_utxo.address
    side = datum.order_side

    outputs = tx_info.outputs
    tokenA_policy_id = datum.tokenA.policy_id
    tokenA_name = datum.tokenA.token_name
    tokenB_policy_id = datum.tokenB.policy_id
    tokenB_name = datum.tokenB.token_name

    # It is recommended to explicitly check all options with isinstance for user input
    if isinstance(redeemer, Buy):
        # Check that the utxo contains a valid token as compared with the list available in the oracle
        check_oracle_datum(
            tx_info.reference_inputs, oracle_policy_id, tokenA_policy_id, tokenA_name
        )

        # Valida que el side corresponde con la acción del redeemer
        assert isinstance(side, Buy), "Side of the tx is not correct"

        # Check the existence of token in the utxo
        tokenA_quantity_spend = own_utxo.value.get(
            datum.tokenA.policy_id, {b"": 0}
        ).get(datum.tokenA.token_name, 0)
        assert tokenA_quantity_spend > 0, "Could not find tokenA in utxo"

        # Valida que la cantidad de tokenB requerida es enviada al owner
        res = False
        address_found = False
        for txo in outputs:
            if txo.address.payment_credential.credential_hash == datum.owner:
                address_found = True
                tokenB_quantity = tokenA_quantity_spend * datum.price
                if (
                    txo.value.get(tokenB_policy_id, {b"": 0}).get(tokenB_name, 0)
                    >= tokenB_quantity
                ):
                    res = True
        assert address_found, "destination address to owner not found in tx outputs"
        assert res, "destination token quantity not found in tx output"

    elif isinstance(redeemer, Unlist):
        check_owner_signed(tx_info.signatories, datum.owner)
