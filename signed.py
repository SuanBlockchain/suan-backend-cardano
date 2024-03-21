from opshin.builder import build, PlutusContract, PlutusData
from opshin.prelude import (
    Address as OpAddress, 
    dataclass, 
    PubKeyCredential, 
    SomeStakingCredential, 
    StakingHash,
    Token,
    NoStakingCredential
)
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Redeemer,
    plutus_script_hash,
    Value,
    VerificationKeyHash,
    ChainContext, BlockFrostChainContext,
    HDWallet, ExtendedSigningKey,
    min_lovelace,
    MultiAsset,
    Address,
    PaymentSigningKey,
    PaymentVerificationKey,
    Network,
    StakeVerificationKey,
    ScriptPubkey,
    ScriptAll,
    Metadata,
    AlonzoMetadata,
    AuxiliaryData,
    UTxO,
    ScriptHash,
    TransactionWitnessSet,
    Transaction,
    VerificationKeyWitness
    
)
import os
from blockfrost import ApiUrls
import logging
import binascii
from typing import Any

from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import Plataforma
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas

def get_nft_utxo(context: Any, address: Address, nft: MultiAsset) -> UTxO:
    """Retrieve the UTXO using the NFT identifier."""
    utxos = context.utxos(str(address))
    nft_utxo = next(
        utxo
        for utxo in utxos
        if utxo.output.amount.multi_asset == nft
    )
    return nft_utxo

def build_multiAsset(policy_id: ScriptHash, tokenName: bytes, quantity: int):
    multi_asset = MultiAsset.from_primitive(
        {
            policy_id.payload: {
                tokenName: quantity,  
            }
        }
    )
    return multi_asset


def get_chain_context() -> ChainContext:

    chain_backend = os.getenv("CHAIN_BACKEND", "blockfrost")
    if chain_backend == "blockfrost":
        BASE_URL = ApiUrls.preview.value
        BLOCK_FROST_PROJECT_ID = "previewp0ZkXTGqxYc7wcjUllmcPQPpZmUAGCCU"
        return BlockFrostChainContext(BLOCK_FROST_PROJECT_ID, base_url=BASE_URL)


def get_signing_info(name):
    skey_path = str(f"/home/cardanodatos/suan/suan-trazabilidad/suantrazabilidadapi/.priv/wallets/keys/{name}.skey")
    payment_skey = PaymentSigningKey.load(skey_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    payment_address = Address(payment_vkey.hash(), network=Network.TESTNET)
    return payment_vkey, payment_skey, payment_address


def main(
    script: str,
    option: str = "send"
):
    # Load chain context
    context = get_chain_context()

    wallet_id = "575a7f01272dd95a9ba2696e9e3d4895fe39b12350f7fa88a301b3ad"
    r = Plataforma().getWallet("id", wallet_id)


    if r["data"].get("data", None) is not None:
        walletInfo = r["data"]["data"]["getWallet"]
            
        if walletInfo is None:
            raise ValueError(f'Wallet with id: {wallet_id} does not exist in DynamoDB')
        else:
            # Get payment address
            payment_address = Address.from_primitive(walletInfo["address"])
            pkh = bytes(payment_address.payment_part)

            seed = walletInfo["seed"] 
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

            payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)
            payment_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)
            staking_verification_key = StakeVerificationKey.from_primitive(child_hdwallet.public_key)
            payment_pkh = binascii.hexlify(payment_verification_key.hash().payload).decode('utf-8')
            stake_pkh = binascii.hexlify(staking_verification_key.hash().payload).decode('utf-8')
            logging.info(f"payment pkh: {payment_pkh} and stake pkh: {stake_pkh}")

    else:
        raise ValueError(f'Error fetching data')

    cbor_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("build/script.cbor")
    mainnet_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("build/mainnet.addr")
    testnet_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("build/testnet.addr")
    policy_id_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("build/script.policy_id")

    signatures = []

    pub_key_policy = ScriptPubkey(payment_verification_key.hash())
    policy = ScriptAll([pub_key_policy])
    nft_policy_id = policy.hash()
    native_scripts = [policy]

    tokenName = b"NFTSUANTOKEN"
    nft_policy_id_bytes=bytes.fromhex(nft_policy_id.payload.hex())

    if script == "inversionista":
        # Build script
        script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("inversionista.py")

        # token = Token(
        #     policy_id=nft_policy_id_bytes,
        #     token_name=tokenName
        # )

        plutus_script = build(script_path, nft_policy_id_bytes, tokenName)

    # Save the contract
    plutus_contract = PlutusContract(plutus_script)
    cbor_hex = plutus_contract.cbor_hex
    mainnet_address = plutus_contract.mainnet_addr
    testnet_address = plutus_contract.testnet_addr
    policy_id = plutus_contract.policy_id

    # Load script info
    script_hash = plutus_script_hash(plutus_script)
    logging.info(f"script_hash: {script_hash}")
    logging.info(f"testnet_address: {testnet_address}")

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(payment_address)
    
    utxo_to_spend = None
    # Get input utxo
    for utxo in context.utxos(payment_address):
        if utxo.output.amount.coin > 3000000:
            utxo_to_spend = utxo
            break
    assert utxo_to_spend is not None, "UTxO not found to spend!"
    logging.info(f"Found utxo to spend: {utxo_to_spend.input.transaction_id} and index: {utxo_to_spend.input.index}")

    #Calculate min and send tokens to contract
    datum = pydantic_schemas.DatumProjectParams(
        beneficiary=OpAddress(
            payment_credential=PubKeyCredential(bytes.fromhex(wallet_id)),
            staking_credential=NoStakingCredential()
        ),
        price= 10_000_000,
    )

    if option == "send":

        builder.add_output(TransactionOutput(testnet_address, Value(20_000_00), datum=datum))
    elif option == "seed":
        # Mint an NFT that contains unique datum that NFT can be minted from the same wallet that provides the acces toke
        
        nft_multiasset = build_multiAsset(nft_policy_id, tokenName, 1_000_000)
        metadata = {
            721: {  
                nft_policy_id.payload.hex(): {
                    tokenName: {
                        "description": f"NFT to identify project with unique info",
                        "name": f"NFT for project",
                        }
                    },
                }
        }
        auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
        builder.mint = nft_multiasset
        builder.native_scripts = native_scripts
        builder.auxiliary_data = auxiliary_data
        
        min_val = min_lovelace(
            context, output=TransactionOutput(testnet_address, Value(0, nft_multiasset), datum=datum)
        )
        builder.add_output(TransactionOutput(testnet_address, Value(min_val, nft_multiasset), datum=datum))

    else:
        # nft_multiasset = build_multiAsset(nft_policy_id, tokenName, 1)
        # nft_utxo = get_nft_utxo(context, testnet_address, nft_multiasset)
        # builder.add_input(nft_utxo)

        # Get input utxo
        utxo_from_contract = None
        for utxo in context.utxos(testnet_address):
            if utxo.output.amount.coin >= 1_000_000:
                utxo_from_contract = utxo
                break
        assert utxo_from_contract is not None, "UTxO not found to spend!"
        logging.info(f"Found utxo to spend: {utxo_from_contract.input.transaction_id} and index: {utxo_from_contract.input.index}")

        builder.add_script_input(
        utxo_from_contract,
        plutus_script,
        redeemer=Redeemer(pydantic_schemas.Buy()),
        )
        

        builder.add_output(TransactionOutput(payment_address, Value(20_000_000)))

        nft_multiasset_back = build_multiAsset(nft_policy_id, tokenName, 999_998)
        nft_multiasset_buy = build_multiAsset(nft_policy_id, tokenName, 2)
        min_val = min_lovelace(
            context, output=TransactionOutput(testnet_address, Value(0, nft_multiasset_back), datum=datum)
        )
        builder.add_output(TransactionOutput(payment_address, Value(min_val, nft_multiasset_buy)))
        builder.add_output(TransactionOutput(testnet_address, Value(min_val, nft_multiasset_back), datum=datum))

    signatures.append(VerificationKeyHash(pkh))
    builder.required_signers = signatures

    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    context.submit_tx(signed_tx)

    logging.info(f"transaction id: {signed_tx.id}")
    logging.info(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")

    # Save the contract
    with open(cbor_path, 'w') as file:
        file.write(str(cbor_hex))
    with open(mainnet_path, 'w') as file:
        file.write(str(mainnet_address))
    with open(testnet_path, 'w') as file:
        file.write(str(testnet_address))
    with open(policy_id_path, 'w') as file:
        file.write(str(policy_id))


if __name__ == "__main__":
    main(script= "inversionista", option = "retreive")