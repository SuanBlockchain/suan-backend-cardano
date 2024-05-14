# TODO: Use the oracle inline datum to validate the list of available tokens to commercialize. It means that there's no need to use NFT to confirm validity of the utxo
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


def validator(
    nft_policy_id: bytes,
    nft_token_name: bytes,
    datum: DatumSwap,
    redeemer: ListingAction,
    context: ScriptContext,
) -> None:
    purpose = context.purpose
    tx_info = context.tx_info

    # assert isinstance(purpose, Spending), f"Wrong script purpose: {purpose}"
    if isinstance(purpose, Spending):
        own_utxo = resolve_spent_utxo(tx_info.inputs, purpose)
        own_addr = own_utxo.address
        side = datum.order_side

        # It is recommended to explicitly check all options with isinstance for user input
        if isinstance(redeemer, Buy):
            # # Valida que el side corresponde con la acción del redeemer
            assert isinstance(side, Buy), "Side of the tx is not correct"

            # Check that the utxo consumed contains the NFT token (valida que el utxo es válido)
            assert (
                own_utxo.value.get(nft_policy_id, {b"": 0}).get(nft_token_name, 0) == 1
            ), "nft token not found in utxo"

            outputs = tx_info.outputs
            tokenB_policy_id = datum.tokenB.policy_id
            tokenB_name = datum.tokenB.token_name

            tokenA_quantity_input = all_tokens_unlocked_from_address(
                tx_info.inputs, own_addr, datum.tokenA
            )

            # Valida que la cantidad de tokenB requerida es enviada al owner
            res = False
            address_found = False
            for txo in outputs:
                if txo.address.payment_credential.credential_hash == datum.owner:
                    address_found = True
                    tokenB_quantity = tokenA_quantity_input * datum.price
                    if (
                        txo.value.get(tokenB_policy_id, {b"": 0}).get(tokenB_name, 0)
                        >= tokenB_quantity
                    ):
                        res = True
            assert address_found, "destination address to owner not found in tx outputs"
            assert res, "destination token quantity not found in tx output"

            # Quema el NFT token asociado al utxo consumido
            nft_burn = tx_info.mint.get(nft_policy_id, {b"": 0}).get(nft_token_name, 0)
            assert nft_burn == -1
            nft_output = sum(
                [
                    txo.value.get(nft_policy_id, {b"": 0}).get(nft_token_name, 0)
                    for txo in outputs
                ]
            )
            assert nft_output == 0, "swap token must be burned"

        elif isinstance(redeemer, Unlist):
            True
            # check_owner_signed(tx_info.signatories, datum.beneficiary)
    else:
        assert False, "Wrong redeemer"
