from fastapi import APIRouter, HTTPException
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma, CardanoApi, Helpers
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.generic import Constants

from typing import Union, Optional
import logging

from pycardano import (
    TransactionBuilder, 
    Address,
    HDWallet,
    ExtendedSigningKey,
    VerificationKeyHash,
    PlutusV2Script,
    plutus_script_hash,
    Redeemer,
    MultiAsset,
    InvalidHereAfter,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    AssetName,
    Asset,
    ScriptHash,
    Value,
    min_lovelace,
    TransactionOutput,
    PaymentVerificationKey,
    TransactionBody,
    VerificationKeyWitness,
    Transaction,
    TransactionWitnessSet,
    ScriptPubkey,
    ScriptAll,
    UTxO
)

from cbor2 import loads

router = APIRouter()

@router.post(
    "/build-tx/",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)

async def buildTx(send: pydantic_schemas.BuildTx) -> dict:

    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", send.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                raise ValueError(f'Wallet with id: {send.wallet_id} does not exist in DynamoDB')
            else:
                ########################
                """2. Build transaction"""
                ########################
                chain_context = CardanoNetwork().get_chain_context()

                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                master_address = Address.from_primitive(walletInfo["address"])
                builder.add_input_address(master_address)

                must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                if send.metadata is not None:
                    # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [send.metadata]}})))
                    # Set transaction metadata
                    builder.auxiliary_data = auxiliary_data
                addresses = send.addresses
                for address in addresses:
                    multi_asset = MultiAsset()
                    if address.multiAsset:
                        for item in address.multiAsset:
                            my_asset = Asset()
                            for name, quantity in item.tokens.items():
                                my_asset.data.update({AssetName(bytes(name, encoding="utf-8")): quantity})
                            
                            multi_asset[ScriptHash(bytes.fromhex(item.policyid))] = my_asset
                                
                    multi_asset_value = Value(0, multi_asset)

                    # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
                    min_val = min_lovelace(
                        chain_context, output=TransactionOutput(Address.decode(address.address), multi_asset_value)
                    )
                    if address.lovelace <= min_val:
                        builder.add_output(TransactionOutput(Address.decode(address.address), Value(min_val, multi_asset)))
                    else:
                        builder.add_output(TransactionOutput(Address.decode(address.address), Value(address.lovelace, multi_asset)))

                
                build_body = builder.build(change_address=master_address, merge_change=True)

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f'Tx Build',
                    "build_tx": format_body,
                    "cbor": str(build_body.to_cbor_hex()),
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor())
                }
        else:

            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sign-submit/", status_code=201, summary="Sign and submit transaction in cborhex format", response_description="Response with transaction submission confirmation")

async def signSubmit(signSubmit: pydantic_schemas.SignSubmit) -> dict:
    try:

        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", signSubmit.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {signSubmit.wallet_id} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                seed = walletInfo["seed"] 
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                payment_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

                ########################
                """2. Build transaction"""
                ########################
                cbor_hex = signSubmit.cbor
                tx_body = TransactionBody.from_cbor(cbor_hex)

                signature = payment_skey.sign(tx_body.hash())
                vk_witnesses = [VerificationKeyWitness(payment_vk, signature)]
                if signSubmit.metadata is not None:
                    # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [signSubmit.metadata]}})))

                    signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses), auxiliary_data=auxiliary_data)
                else:
                    signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

                chain_context = CardanoNetwork().get_chain_context()
                chain_context.submit_tx(signed_tx.to_cbor())
                tx_id = tx_body.hash().hex()

                logging.info(f"transaction id: {tx_id}")
                logging.info(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{tx_id}")
                
                final_response = {
                    "success": True,
                    "msg": "Tx submitted to the blockchain",
                    "tx_id": tx_id,
                    "cardanoScan": f"Cardanoscan: https://preview.cardanoscan.io/transaction/{tx_id}"
                }

        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        return final_response
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/tx-status/",
    status_code=201,
    summary="Get the number of block confirmations for a given transaction hash list",
    response_description="Array of transaction confirmation counts",
    # response_model=List[str],
)

async def txStatus(tx_hashes: Union[str, list[str]]) -> list:
    try:
         return CardanoApi().txStatus(tx_hashes)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get(
    "/send-access-token/",
    status_code=201,
    summary="Get the token to access Suan Marketplace",
    response_description="Confirmation of token sent to provided address",
    # response_model=List[str],
)

async def sendAccessToken(wallet_id: str, destinAddress: str):
    try:

        ########################
        """1. Obtain the MasterKey to pay and mint"""
        ########################
        r = Plataforma().getWallet("id", wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                raise ValueError(f'Wallet with id: {wallet_id} does not exist in DynamoDB')
            else:

                seed = walletInfo["seed"] 
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                payment_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)


                master_address = Address.from_primitive(walletInfo["address"])
                ########################
                """3. Create the script and policy"""
                ########################
                # A policy that requires a signature from the policy key we generated above
                pub_key_policy = ScriptPubkey(payment_vk.hash())
                # A time policy that disallows token minting after 10000 seconds from last block
                # must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Combine two policies using ScriptAll policy
                policy = ScriptAll([pub_key_policy])
                # Calculate policy ID, which is the hash of the policy
                policy_id = policy.hash()
                print(f"Policy ID: {policy_id}")
                with open(Constants().PROJECT_ROOT / "policy.id", "a+") as f:
                    f.truncate(0)
                    f.write(str(policy_id))
                # Create the final native script that will be attached to the transaction
                native_scripts = [policy]
                ########################
                """Define NFT"""
                ########################
                tokenName = b"SandboxSuanAccess1"
                my_nft_alternative = MultiAsset.from_primitive(
                    {
                        policy_id.payload: {
                            tokenName: 1,  
                        }
                    }
                )
                ########################
                """Create metadata"""
                ########################
                metadata = {
                    721: {  
                        policy_id.payload.hex(): {
                            tokenName: {
                                "description": "NFT con acceso a marketplace en Sandbox",
                                "name": "Token NFT SandBox",
                            },
                        }
                    }
                }
                # Place metadata in AuxiliaryData, the format acceptable by a transaction.
                auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
                """Build transaction"""
                chain_context = CardanoNetwork().get_chain_context()
                # Create a transaction builder
                builder = TransactionBuilder(chain_context)
                # Add our own address as the input address
                builder.add_input_address(master_address)
                # Since an InvalidHereAfter rule is included in the policy, we must specify time to live (ttl) for this transaction
                # builder.ttl = must_before_slot.after
                # Set nft we want to mint
                builder.mint = my_nft_alternative
                # Set native script
                builder.native_scripts = native_scripts
                # Set transaction metadata
                builder.auxiliary_data = auxiliary_data
                # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
                min_val = min_lovelace(
                    chain_context, output=TransactionOutput(destinAddress, Value(0, my_nft_alternative))
                )
                # Send the NFT to our own address + 500 ADA
                builder.add_output(TransactionOutput(destinAddress, Value(min_val, my_nft_alternative)))
                builder.add_output(TransactionOutput(destinAddress, Value(50000000)))
                # Create final signed transaction
                signed_tx = builder.build_and_sign([payment_skey], change_address=master_address)
                # Submit signed transaction to the network
                tx_id = signed_tx.transaction_body.hash().hex()
                chain_context.submit_tx(signed_tx)
                ####################################################
                final_response = {
                        "success": True,
                        "msg": "Tx submitted to the blockchain",
                        "tx_id": tx_id
                    }
        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
        return final_response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/min-lovelace/", status_code=201,
summary="Given utxo output details, obtain calculated min ADA required",
    response_description="Min Ada required for the utxo in lovelace",)


async def minLovelace(addressDestin: pydantic_schemas.AddressDestin, datum_hash: Optional[str] = None, datum: Optional[dict[str, str]] = None, script: Optional[dict[str, str]] = None) -> int:
    
    """Min Ada required for the utxo in lovelace \n
    """
    try:
        address = addressDestin.address
        # Get Multiassets
        multiAsset = Helpers().makeMultiAsset([addressDestin])
        # Create Value type
        amount = Value(addressDestin.lovelace, multiAsset)
        if not datum_hash:
            datum_hash = None
        if not datum:
            datum = None
        if not script:
            script = None

        output = TransactionOutput(address, amount, datum_hash, datum, script)

        chain_context = CardanoNetwork().get_chain_context()
        min_val = min_lovelace(chain_context, output)

        return min_val
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tx-fee/", status_code=200,
summary="Deserialized a transaction provided in cbor format to get the fee",
    response_description="Fee in lovelace",)

async def getFeeFromCbor(txcbor: str) -> int:

    """Deserialized a transaction provided in cbor format to get the fee \n
    """
    try:
        payload = bytes.fromhex(txcbor)
        value = loads(payload)
        if isinstance(value, list):
            fee = value[0][2]
        else:
            fee = value[2]

        return fee
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/mint-tokens/",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)

async def mintTokens(send: pydantic_schemas.TokenGenesis) -> dict:

    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", send.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                raise ValueError(f'Wallet with id: {send.wallet_id} does not exist in DynamoDB')
            else:
                ########################
                """2. Build transaction"""
                ########################
                chain_context = CardanoNetwork().get_chain_context()

                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                master_address = Address.from_primitive(walletInfo["address"])
                # builder.add_input_address(master_address)

                pkh = bytes(master_address.payment_part)


                # Other method to find the utxo needed to cover transaction with Plutus script, 
                # but I prefered to find a utxo for the collateral and input the address instead
                # Get input utxo
                utxo_to_spend = None
                for utxo in chain_context.utxos(master_address):
                    if utxo.output.amount.coin > 3000000:
                        utxo_to_spend = utxo
                        break
                assert utxo_to_spend is not None, "UTxO not found to spend!"

                builder.add_input(utxo_to_spend)

                # Find a collateral UTxO
                # non_nft_utxo = None
                # for utxo in chain_context.utxos(master_address):
                #     # multi_asset should be empty for collateral utxo
                #     if not utxo.output.amount.multi_asset and utxo.output.amount.coin >= 5000000:
                #         non_nft_utxo = utxo
                #         break
                # assert isinstance(non_nft_utxo, UTxO), "No collateral UTxOs found!"
                # builder.collaterals.append(non_nft_utxo)

                signatures = []
                if send.mint is not None:

                    tokens_bytes = { bytes(tokenName, encoding="utf-8"): q for tokenName, q in send.mint.asset.tokens.items() }
                    signatures.append(VerificationKeyHash(pkh))
                    
                    #Consultar en base de datos
                    script_id = send.mint.asset.policyid

                    r = Plataforma().getScript("id", script_id)
                    if r["data"].get("data", None) is not None:
                        contractInfo = r["data"]["data"]["getScript"]
                        if contractInfo is None:
                            raise ValueError(f"Script with policyId does not exist in database")
                        else:
                            cbor_hex = contractInfo.get("cbor", None)
                            cbor = bytes.fromhex(cbor_hex)
                            plutus_script = PlutusV2Script(cbor)
                    else:
                        raise ValueError(f"Error fetching Script from database")

                    script_hash = plutus_script_hash(plutus_script)
                    logging.info(f"script_hash: {script_hash}")
                    
                    if send.mint.redeemer == 0:
                        redeemer = pydantic_schemas.RedeemerMint()
                    elif send.mint.redeemer == 1:
                        redeemer = pydantic_schemas.RedeemerBurn()
                    else:
                        raise ValueError(f"Wrong redeemer")

                    builder.add_minting_script(script=plutus_script, redeemer=Redeemer(redeemer))
                    
                    mint_multiassets = MultiAsset.from_primitive({ bytes(script_hash): tokens_bytes })
                    
                    builder.mint = mint_multiassets

                    #If burn, insert the utxo that contains the asset
                    for tn_bytes, amount in tokens_bytes.items():
                        if amount < 0:
                            burn_utxo = None
                            candidate_burn_utxo = []
                            for utxo in chain_context.utxos(master_address):
                                def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                                    return pi == script_hash and an.payload == tn_bytes and a >= -amount
                                if utxo.output.amount.multi_asset.count(f):
                                    burn_utxo = utxo
                                    
                                    builder.add_input(burn_utxo)

                            if not burn_utxo:
                                q = 0
                                for utxo in chain_context.utxos(master_address):
                                    def f1(pi: ScriptHash, an: AssetName, a: int) -> bool:
                                        return pi == script_hash and an.payload == tn_bytes
                                    if utxo.output.amount.multi_asset.count(f1):
                                        candidate_burn_utxo.append(utxo)
                                        union_multiasset = utxo.output.amount.multi_asset.data
                                        for asset in union_multiasset.values():
                                            q += int(list(asset.data.values())[0])
                                
                                if q >= -amount:
                                    for x in candidate_burn_utxo:
                                        builder.add_input(x)
                                else:
                                    raise ValueError("UTxO containing token to burn not found!")

                builder.required_signers = signatures

                must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                if send.metadata is not None:
                    # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [send.metadata]}})))
                    # Set transaction metadata
                    builder.auxiliary_data = auxiliary_data

                if send.addresses:
                    for address in send.addresses:
                        multi_asset = MultiAsset()
                        if address.multiAsset:
                            for item in address.multiAsset:
                                my_asset = Asset()
                                for name, quantity in item.tokens.items():
                                    my_asset.data.update({AssetName(bytes(name, encoding="utf-8")): quantity})
                                
                                multi_asset[ScriptHash(bytes.fromhex(item.policyid))] = my_asset
                        
                        multi_asset_value = Value(0, multi_asset)

                        # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
                        min_val = min_lovelace(
                            chain_context, output=TransactionOutput(Address.decode(address.address), multi_asset_value)
                        )
                        if address.lovelace <= min_val:
                            builder.add_output(TransactionOutput(Address.decode(address.address), Value(min_val, multi_asset)))
                        else:
                            builder.add_output(TransactionOutput(Address.decode(address.address), Value(address.lovelace, multi_asset)))
                else:
                    if amount > 0:
                        # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
                        min_val = min_lovelace(
                            chain_context, output=TransactionOutput(master_address, Value(0, mint_multiassets))
                        )
                        builder.add_output(TransactionOutput(master_address, Value(min_val, mint_multiassets)))

                seed = walletInfo.get("seed", None)
                if not seed:
                    raise ValueError(f"No seed found for wallet with id: {send.wallet_id}")
                
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                signed_tx = builder.build_and_sign(signing_keys=[payment_skey], change_address=master_address)

                chain_context.submit_tx(signed_tx)

                logging.info(f"transaction id: {signed_tx.id}")
                logging.info(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")

                # build_body = builder.build(change_address=address.address, merge_change=True)
                build_body = signed_tx.transaction_body

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f'Tx Build',
                    "build_tx": format_body,
                    "cbor": str(signed_tx.to_cbor_hex()),
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                    "tx_id": str(signed_tx.id),
                    "cardanoScan": f"https://preview.cardanoscan.io/transaction/{signed_tx.id}"
                }
        else:

            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.post(
#     "/distribute-tx/{source_funds}",
#     status_code=201,
#     summary="Build the transaction off-chain for validation before signing",
#     response_description="Response with transaction details and in cborhex format",
#     # response_model=List[str],
# )

# async def distributeTx(source_funds: pydantic_schemas.distributeCommandName, send: pydantic_schemas.DistributeTx) -> dict:

#     try:
#         if source_funds == "bioc":
#             master_address = "addr_test1vqx420pm9cx326rh0q8yx6u4h72ae56l9ekzk05m8w9qe3cz5swj5"
#         if source_funds == "propietario":
#             master_address = "addr_test1vpgydu6xuc3nvyzpdnkq4jpaprs0rp5x5xzk088grlp92cq057hxl"
#         elif source_funds == "administrador":
#             master_address = "addr_test1qzttu3gj6vtz6e6j4p4pnmyw52x5j7kw47kce4hux9fv445khez395ck94n492r2r8kgag5df9avatad3nt0cv2jettqxfwfwv"
#         elif source_funds == "buffer":
#             master_address = "addr_test1vqs34z4ljy3c6u3s97m64zqz7f0ks6vtre2dcpl5um8wz2qgaxq8z"
#         elif source_funds == "comunidad":
#             master_address = "addr_test1vqvx6mm487nkkpavyf7sqflgavutajq8veer5wmy0nwlgyg27rsqk"
#         elif source_funds == "inversionista":
#             master_address = "addr_test1qq0uh3hap3sqcj3cwlx2w3yq9vm4wclgp4x0y3wuyvapzdcle0r06rrqp39rsa7v5azgq2eh2a37sr2v7fzacge6zymsn0w2mg"
        

#         r = Plataforma().getWallet("id", send.wallet_id)
#         if r["data"].get("data", None) is not None:
#             walletInfo = r["data"]["data"]["getWallet"]
#             if walletInfo is None:
#                 raise ValueError(f'Wallet with id: {send.wallet_id} does not exist in DynamoDB')
#             else:
#         # mnemonics, skey, vkey, address, pkh = Keys().load_or_create_key_pair(wallet_name=source)
                
        
#         # if not (skey and vkey):
#         #     raise ValueError(f'Wallet with id: {send.wallet_id} does not exist in DynamoDB')

#                 ########################
#                 """2. Build transaction"""
#                 ########################
#                 chain_context = CardanoNetwork().get_chain_context()

#                 # Create a transaction builder
#                 builder = TransactionBuilder(chain_context)

#                 # Add user own address as the input address

#                 builder.add_input_address(master_address)

#                 buyer_address = Address.from_primitive(walletInfo["address"])
#                 builder.add_input_address(buyer_address)

#                 must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
#                 # Since an InvalidHereAfter
#                 builder.ttl = must_before_slot.after

#                 if send.metadata is not None:
#                     # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

#                     auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [send.metadata]}})))
#                     # Set transaction metadata
#                     builder.auxiliary_data = auxiliary_data
#                 addresses = send.addresses
#                 for address in addresses:
#                     multi_asset = MultiAsset()
#                     if address.multiAsset:
#                         for item in address.multiAsset:
#                             my_asset = Asset()
#                             for name, quantity in item.tokens.items():
#                                 my_asset.data.update({AssetName(bytes(name, encoding="utf-8")): quantity})
                            
#                             multi_asset[ScriptHash(bytes.fromhex(item.policyid))] = my_asset
                                
#                     multi_asset_value = Value(0, multi_asset)

#                     # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
#                     min_val = min_lovelace(
#                         chain_context, output=TransactionOutput(Address.decode(address.address), multi_asset_value)
#                     )
#                     if address.lovelace <= min_val:
#                         builder.add_output(TransactionOutput(Address.decode(address.address), Value(min_val, multi_asset)))
#                     else:
#                         builder.add_output(TransactionOutput(Address.decode(address.address), Value(address.lovelace, multi_asset)))

                
#                 build_body = builder.build(change_address=master_address, merge_change=True)

#                 # Processing the tx body
#                 format_body = Plataforma().formatTxBody(build_body)

#                 transaction_id_list = []
#                 for utxo in build_body.inputs:
#                     transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
#                     transaction_id_list.append(transaction_id)

#                 utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

#                 final_response = {
#                     "success": True,
#                     "msg": f'Tx Build',
#                     "build_tx": format_body,
#                     "cbor": str(build_body.to_cbor_hex()),
#                     "utxos_info": utxo_list_info,
#                     "tx_size": len(build_body.to_cbor())
#                 }
                
#                 return final_response
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/sign-submit-distribute/", status_code=201, summary="Sign and submit transaction in cborhex format", response_description="Response with transaction submission confirmation")

# async def signSubmitDistribute(source_funds: pydantic_schemas.distributeCommandName, signSubmit: pydantic_schemas.SignSubmit) -> dict:
#     try:
#         if source_funds == "bioc":
#             wallet_id = "0d553c3b2e0d156877780e436b95bf95dcd35f2e6c2b3e9b3b8a0cc7"
#         if source_funds == "propietario":
#             wallet_id = "5046f346e6233610416cec0ac83d08e0f18686a185679ce81fc25560"
#         elif source_funds == "administrador":
#             wallet_id = "96be4512d3162d6752a86a19ec8ea28d497aceafad8cd6fc3152cad6"
#         elif source_funds == "buffer":
#             wallet_id = "211a8abf91238d72302fb7aa8802f25f68698b1e54dc07f4e6cee128"
#         elif source_funds == "comunidad":
#             wallet_id = "186d6f753fa76b07ac227d0027e8eb38bec80766723a3b647cddf411"
#         elif source_funds == "inversionista":
#             wallet_id = "1fcbc6fd0c600c4a3877cca744802b375763e80d4cf245dc233a1137"

#         r = Plataforma().getWallet("id", wallet_id)
#         if r["data"].get("data", None) is not None:
#             walletInfo = r["data"]["data"]["getWallet"]
#             if walletInfo is None:
#                 final_response = {
#                     "success": True,
#                     "msg": f'Wallet with id: {wallet_id} does not exist in DynamoDB',
#                     "data": r["data"]
#                 }
#             else:
#                 seed = walletInfo["seed"] 
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#                 payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

#                 payment_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#                 ########################
#                 """2. Build transaction"""
#                 ########################    
#                 cbor_hex = signSubmit.cbor
#                 tx_body = TransactionBody.from_cbor(cbor_hex)

#                 signature = payment_skey.sign(tx_body.hash())
#                 vk_witnesses = [VerificationKeyWitness(payment_vk, signature)]
#                 if signSubmit.metadata is not None:
#                     # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

#                     auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [signSubmit.metadata]}})))

#                     signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses), auxiliary_data=auxiliary_data)
#                 else:
#                     signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

#                 chain_context = CardanoNetwork().get_chain_context()
#                 chain_context.submit_tx(signed_tx.to_cbor())
#                 tx_id = tx_body.hash().hex()

#                 logging.info(f"transaction id: {tx_id}")
#                 logging.info(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{tx_id}")
                
#                 final_response = {
#                     "success": True,
#                     "msg": "Tx submitted to the blockchain",
#                     "tx_id": tx_id,
#                     "cardanoScan": f"Cardanoscan: https://preview.cardanoscan.io/transaction/{tx_id}"
#                 }

#         else:
#             if r["success"] == True:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["data"]["errors"]
#                 }
#             else:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["error"]
#                 }
#         return final_response
#     except Exception as e:
#         # Handling other types of exceptions
#         raise HTTPException(status_code=500, detail=str(e))
    
# @router.post(
#     "/purchase-token/",
#     status_code=201,
#     summary="Get the token to access Suan Marketplace",
#     response_description="Confirmation of token sent to provided address",
#     # response_model=List[str],
# )

# async def purchaseToken(buy: pydantic_schemas.Buy) -> dict:

#     try:
#         ########################
#         """1. Get wallet info"""
#         ########################
#         r = Plataforma().getWallet("id", buy.wallet_id)
#         if r["data"].get("data", None) is not None:
#             walletInfo = r["data"]["data"]["getWallet"]
#             if walletInfo is None:
#                 final_response = {
#                     "success": True,
#                     "msg": f'Wallet with id: {buy.wallet_id} does not exist in DynamoDB',
#                     "data": r["data"]
#                 }
#             else:
#                 ########################
#                 """Obtain user verification key"""
#                 ########################
#                 seed = walletInfo["seed"] 
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
#                 spend_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#                 ########################
#                 """Obtain minting verification key and get the script and policyid"""
#                 ########################
#                 r = Plataforma().getWallet("id", Constants.minting_wallet)
#                 seed = r["data"]["data"]["getWallet"]["seed"]
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#                 minting_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#                 # Minting script derivation
#                 pub_key_policy = ScriptPubkey(minting_verification_key.hash())
#                 policy = ScriptAll([pub_key_policy])
#                 policy_id = policy.hash()
#                 print(f"Policy ID: {policy_id}")

#                 ########################
#                 """Define the token"""
#                 ########################
#                 tokenName = buy.tokenName.encode('utf-8')
#                 mintAsset = MultiAsset.from_primitive(
#                     {
#                         policy_id.payload: {
#                             tokenName: buy.tokenAmount,  
#                         }
#                     }
#                 )

#                 ########################
#                 """2. Build transaction"""
#                 ########################
#                 address = walletInfo["address"]
#                 # Create a transaction builder
#                 builder = TransactionBuilder(chain_context)

#                 must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
#                 # Since an InvalidHereAfter
#                 builder.ttl = must_before_slot.after

#                 ########################
#                 """Create metadata"""
#                 ########################
#                 metadata = { policy_id.payload.hex(): {tokenName: buy.metadata}
#                     }
#                 enclosedMetadata = {
#                     721: metadata
#                 }

#                 auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(enclosedMetadata)))
#                 # Set transaction metadata
#                 # builder.auxiliary_data = auxiliary_data

#                 builder.mint = mintAsset
#                 builder.native_scripts = [policy]
                
#                 # Add user own address as the input address
#                 builder.add_input_address(address)

#                 min_val = min_lovelace(
#                     chain_context, output=TransactionOutput(address, Value(0, mintAsset))
#                 )
#                 builder.add_output(TransactionOutput(address, Value(min_val, mintAsset)))
#                 builder.required_signers = [minting_verification_key.hash(), spend_vk.hash()]
#                 # builder.required_signers([minting_verification_key.hash(), spend_vk.hash()])

#                 build_body = builder.build(change_address=address)

#                 # witnessSet = builder.build_witness_set()

#                 # signature = payment_skey.sign(build_body.hash())
#                 # witnessSet.vkey_witnesses = []
#                 # witnessSet.vkey_witnesses.append(
#                 #     VerificationKeyWitness(payment_verification_key, signature)
#                 # )

#                 # # signed_tx = builder.build_and_sign([payment_skey], change_address=address)
#                 # tx_signed = Transaction(build_body, witnessSet, auxiliary_data=auxiliary_data)
#                 # witnessSet.vkey_witnesses.append(
#                 #     VerificationKeyWitness(payment_verification_key, signature)
#                 # )

#                 # Processing the tx body
#                 format_body = Plataforma().formatTxBody(build_body)

#                 transaction_id_list = []
#                 for utxo in build_body.inputs:
#                     transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
#                     transaction_id_list.append(transaction_id)

#                 utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

#                 final_response = {
#                     "success": True,
#                     "msg": f'Tx Build',
#                     "build_tx": format_body,
#                     "cbor": str(build_body.to_cbor_hex()),
#                     "utxos_info": utxo_list_info,
#                     "tx_size": len(build_body.to_cbor())
#                 }
#         else:

#             if r["success"] == True:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["data"]["errors"]
#                 }
#             else:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["error"]
#                 }
        
#         return final_response

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     except Exception as e:
#         # Handling other types of exceptions
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/sign-submit-purchase/", status_code=201, summary="Sign and submit transaction in cborhex format", response_description="Response with transaction submission confirmation")

# async def signSubmitPurchase(signSubmit: pydantic_schemas.PurchaseSignSubmit) -> dict:
#     try:

#         ########################
#         """1. Get wallet info"""
#         ########################
#         r = Plataforma().getWallet("id", signSubmit.wallet_id)
#         if r["data"].get("data", None) is not None:
#             walletInfo = r["data"]["data"]["getWallet"]
#             if walletInfo is None:
#                 final_response = {
#                     "success": True,
#                     "msg": f'Wallet with id: {signSubmit.wallet_id} does not exist in DynamoDB',
#                     "data": r["data"]
#                 }
#             else:
#                 seed = walletInfo["seed"] 
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#                 payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

#                 payment_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#                 ########################
#                 """1. Get wallet for mint"""
#                 ########################
#                 r = Plataforma().getWallet("id", Constants.minting_wallet)
#                 seed = r["data"]["data"]["getWallet"]["seed"]
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#                 minting_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

#                 minting_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#                 ########################
#                 """2. Build transaction"""
#                 ########################
#                 cbor_hex = signSubmit.cbor
#                 tx_body = TransactionBody.from_cbor(cbor_hex)


#                 payment_signature = payment_skey.sign(tx_body.hash())
#                 minting_signature = minting_skey.sign(tx_body.hash())

#                 enclosedMetadata = {
#                     721: signSubmit.metadata
#                 }

#                 vk_witnesses = [VerificationKeyWitness(payment_vk, payment_signature), VerificationKeyWitness(minting_vk, minting_signature)]
#                 auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(enclosedMetadata)))
#                 # signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses), auxiliary_data=auxiliary_data)
#                 signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

#                 chain_context.submit_tx(signed_tx.to_cbor())
#                 tx_id = tx_body.hash().hex()
#                 final_response = {
#                     "success": True,
#                     "msg": "Tx submitted to the blockchain",
#                     "tx_id": tx_id
#                 }

#         else:
#             if r["success"] == True:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["data"]["errors"]
#                 }
#             else:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["error"]
#                 }
#         return final_response
#     except Exception as e:
#         # Handling other types of exceptions
#         raise HTTPException(status_code=500, detail=str(e))

