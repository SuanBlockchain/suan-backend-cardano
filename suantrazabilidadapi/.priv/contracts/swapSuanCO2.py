# El contrato revisa el tiempo de redención, si es menor no deja crear SUANCO2, si es mayor revisa el volumen certificado y lleva registro del volumen que se swapea con el SUANCO2. Todos los stakeholders
# deben redimir tokens de propiedad por SUANCO2 en su totalidad en una transacción a excepción de los inversionistas y esto se sabe porque las billeteras que controlan los tokens de propiedad de todos los stakeholders
# (propietario, comunidad, administrador, etc) están marcadas en el datum con sus pkh respectivos. Cualquier dirección "anónima" que esté en posesión de tokens de propiedad de un proyecto se asumirá que es de tipo
# inversionista y podrá redimir en función de las condiciones que apliquen para inversionistas. Se llevará registro de los volúmenes de redención en el datum del oráculo respectivo para evitar que se hagan redenciones
# de volúmenes mayores a los certificados

# Validación

# 1. Tiempo del periodo finalizado
# 2. Tokens disponibles en redención cruzado con el pkh que redime
# 3.

# TODO:
# los tokens que se inyectan se deben quemar y no deben salir en la transaccción
# que el datum se disminuya en la proporción adecuada para mantener el balance


#!/usr/bin/env -S opshin eval spending
from opshin.prelude import *
from opshin.ledger.interval import *

suanco2policyid = b"somehting"
suancoTokenName = b"SUANCO2"


@dataclass
class Redemption(PlutusData):
    CONSTR_ID = 0
    sig: PubKeyHash
    tokenPolicyId: PolicyId


@dataclass
class TokenFeed(PlutusData):
    CONSTR_ID = 0
    tokenName: bytes
    redemption: Dict[PubKeyHash, int]
    deadline: POSIXTime


@dataclass
class DatumSwap(PlutusData):
    CONSTR_ID = 0
    value_dict: Dict[bytes, TokenFeed]


def get_token_info(
    tokenPolicyId: PolicyId, datum: DatumSwap, txinfo: TxInfo
) -> Union[TokenFeed, None]:
    token_feed = None
    tokens = [
        datum.value_dict[i.resolved.value.PolicyId]
        for i in txinfo.inputs
        if i.resolved.value.PolicyId == tokenPolicyId
    ]
    if tokens:
        token_feed = tokens[0]

    return token_feed


def is_after(deadline: POSIXTime, valid_range: POSIXTimeRange) -> bool:
    # the range [deadline, infinity) must contain the valid_range which guarantees that the transaction happens after the deadline
    from_interval: POSIXTimeRange = make_from(deadline)
    return contains(from_interval, valid_range)


def check_redemption_deadline(
    token_info: TokenFeed, valid_range: POSIXTimeRange
) -> None:

    deadline = token_info.deadline
    # check for redemption period, the valid_range of the transaction must start after the deadline
    assert is_after(deadline, valid_range), "deadline not reached"


def get_token_quantity_redeem(
    tokenPolicyId: PolicyId,
    token_name: bytes,
    txinfo: TxInfo,
) -> int:
    tq = sum(
        [
            i.resolved.value.get(tokenPolicyId, {b"", 0}.get(token_name, 0))
            for i in txinfo.inputs
            if i.resolved.value.PolicyId == tokenPolicyId
        ]
    )
    return tq


def check_volume(sig: PubKeyHash, token_info: TokenFeed, tq: int) -> None:
    redemption_volume = token_info.redemption.get(sig, 0)
    assert redemption_volume >= tq, "Redemption volume exceeded"


def check_stakeholder_signed(signatories: List[PubKeyHash], sig: PubKeyHash) -> None:

    assert (
        sig in signatories
    ), f"Owner did not sign transaction, requires {sig.hex()} but got {[s.hex() for s in signatories]}"


def validator(
    datum: DatumSwap,
    redeemer: Redemption,
    context: ScriptContext,
) -> None:
    purpose = context.purpose
    tx_info = context.tx_info

    assert isinstance(purpose, Spending), f"Wrong script purpose: {purpose}"

    # It is recommended to explicitly check all options with isinstance for user input
    if isinstance(redeemer, Redemption):
        # Check that the utxo in inputs contain a valid token as compared with the list available in the datum
        tokenPolicyId = redeemer.tokenPolicyId
        token_info = get_token_info(tokenPolicyId, datum, tx_info)
        assert isinstance(token_info, TokenFeed), "Token not found"

        check_redemption_deadline(token_info, tx_info.valid_range)

        tq = get_token_quantity_redeem(tokenPolicyId, token_info.tokenName, tx_info)
        assert tq > 0, "No token to redeem provided in inputs"

        sig = redeemer.sig
        if sig in token_info.redemption.keys():
            # Check that the volume to redeem is higher than the one provided
            check_volume(sig, token_info)
            # check that the stakeholder is signing to redeem its tokens
            check_stakeholder_signed(tx_info.signatories, sig)

        # check_suanco2_output()
        # que no se puedan sacar más tokens SUANCO2 de los que se inyectan de propiedad (proporción 1:1)
        # Check that Suanco2 redeemed are equal to the token provided and allowed to redeem
        for txo in tx_info.outputs:
            tq_suanco2 = sum(
                txo.value.get(suanco2policyid, {b"": 0}).get(suancoTokenName, 0)
            )
        assert tq == tq_suanco2, "Wrong SUANCO2 quantity"

        # Check that there are no tokens in the outputs except the Suanco2 validated

        # Check that the datum updates are correct to keep the correct balance to redeem later

    else:
        assert False, "Wrong redeemer"
