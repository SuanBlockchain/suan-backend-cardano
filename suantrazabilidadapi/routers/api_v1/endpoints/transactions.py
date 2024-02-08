from fastapi import APIRouter, HTTPException, Body
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma, CardanoApi, Helpers

import os
import pathlib
from typing import Union, Optional

from pycardano import *
from blockfrost import ApiUrls

from cbor2 import loads

class Constants:
    NETWORK = Network.TESTNET
    BLOCK_FROST_PROJECT_ID = os.getenv('block_frost_project_id')
    PROJECT_ROOT = "suantrazabilidadapi"
    ROOT = pathlib.Path(PROJECT_ROOT)
    KEY_DIR = ROOT / f'.priv/wallets'
    ENCODING_LENGHT_MAPPING = {12: 128, 15: 160, 18: 192, 21: 224, 24:256}
    minting_wallet = os.getenv('minting_wallet')


chain_context = BlockFrostChainContext(
    project_id=Constants.BLOCK_FROST_PROJECT_ID,
    base_url=ApiUrls.preview.value,
)

"""Preparation"""
# Define the root directory where images and keys will be stored.
PROJECT_ROOT = "suantrazabilidadapi"
root = Constants.ROOT

# Create the directory if it doesn't exist
root.mkdir(parents=True, exist_ok=True)

# mainWalletName = "SuanMasterSigningKeys#"

def load_or_create_key_pair(base_dir, base_name):
    skey_path = base_dir / f"{base_name}.skey"
    vkey_path = base_dir / f"{base_name}.vkey"

    if skey_path.exists():
        skey = PaymentSigningKey.load(str(skey_path))
        vkey = PaymentVerificationKey.from_signing_key(skey)
    else:
        key_pair = PaymentKeyPair.generate()
        key_pair.signing_key.save(str(skey_path))
        key_pair.verification_key.save(str(vkey_path))
        skey = key_pair.signing_key
        vkey = key_pair.verification_key
    return skey, vkey

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
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {send.wallet_id} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                ########################
                """2. Build transaction"""
                ########################
                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                builder.add_input_address(walletInfo["address"])

                must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                if send.metadata is not None:
                    # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020

                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [send.metadata]}})))
                    # Set transaction metadata
                    builder.auxiliary_data = auxiliary_data
                addresses = send.addresses
                # multi_asset = []
                for address in addresses:
                    multi_asset = MultiAsset()
                    if address.multiAsset:
                        for item in address.multiAsset:
                            for policy_id, tokens in item.items():
                                my_asset = Asset()
                                for name, quantity in tokens.items():
                                    my_asset.data.update({AssetName(name.encode()): quantity})

                                multi_asset[ScriptHash(bytes.fromhex(policy_id))] = my_asset
                                
                    multi_asset_value = Value(0, multi_asset)

                    # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
                    min_val = min_lovelace(
                        chain_context, output=TransactionOutput(address.address, multi_asset_value)
                    )
                    if address.lovelace <= min_val:
                        builder.add_output(TransactionOutput(address.address, Value(min_val, multi_asset)))
                    else:
                        # builder.add_output(TransactionOutput.from_primitive([address.address, address.lovelace]))
                        builder.add_output(TransactionOutput(address.address, Value(address.lovelace, multi_asset)))

                build_body = builder.build(change_address=walletInfo["address"])

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
                    transaction_id_list.append(transaction_id)

<<<<<<< HEAD
                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

=======
                utxo_list_info = Plataforma().getUtxoInfo(transaction_id_list, True)
                
>>>>>>> transaction with metadata
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
<<<<<<< HEAD
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
=======
    except Exception as e:
        # Handling other types of exceptions
>>>>>>> transaction with metadata
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
<<<<<<< HEAD
                vk_witnesses = [VerificationKeyWitness(payment_vk, signature)]
=======
                vk_witnesses = [VerificationKeyWitness(spend_vk, signature)]
>>>>>>> transaction with metadata
                auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata({674: {"msg": [signSubmit.metadata]}})))
                signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses), auxiliary_data=auxiliary_data)

                chain_context.submit_tx(signed_tx.to_cbor())
                tx_id = tx_body.hash().hex()
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
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))
<<<<<<< HEAD
=======

# @router.get(
#     "/mylib-create-wallet/",
#     status_code=200,
#     summary="Create wallet, fund wallet with NFT token to access Sandbox marketplace",
#     response_description="Response with mnemonics and cardano cli keys",
#     # response_model=List[str],
# )
>>>>>>> transaction with metadata

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

async def sendAccessToken(destinAddress: str):
    try:

        ########################
        """1. Obtain the MasterKey to pay and mint"""
        ########################
        payment_skey, payment_vkey = load_or_create_key_pair(Constants.KEY_DIR, "payment")
        address = Address(payment_vkey.hash(), network=Constants.NETWORK)
        print(address)
        ########################
        """3. Create the script and policy"""
        ########################
        # A policy that requires a signature from the policy key we generated above
        pub_key_policy = ScriptPubkey(payment_vkey.hash())
        # A time policy that disallows token minting after 10000 seconds from last block
        # must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy])
        # Calculate policy ID, which is the hash of the policy
        policy_id = policy.hash()
        print(f"Policy ID: {policy_id}")
        with open(root / "policy.id", "a+") as f:
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
        # Create a transaction builder
        builder = TransactionBuilder(chain_context)
        # Add our own address as the input address
        builder.add_input_address(address)
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
        signed_tx = builder.build_and_sign([payment_skey], change_address=address)
        # Submit signed transaction to the network
        tx_id = signed_tx.transaction_body.hash().hex()
        chain_context.submit_tx(signed_tx)
        ####################################################
        final_response = {
                "success": True,
                "msg": "Tx submitted to the blockchain",
                "tx_id": tx_id
            }
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))

# @router.post(
#     "/genesis-token/",
#     status_code=201,
#     summary="Mint the Max Supply of the tokens for a specific project",
#     response_description="Confirmation of succesful minting",
#     # response_model=List[str],
# )

# async def projectGenesisToken(token_genesis: pydantic_schemas.TokenGenesis) -> dict:

#     try:
#         ########################
#         """1. Obtain the MasterKey to pay and mint"""
#         ########################
#         hdwallet = HDWallet.from_mnemonic(Constants.minting_wallet)

#         child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#         payment_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)
#         payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)
#         address = Address(payment_verification_key.hash(), network=Constants.NETWORK)

#         # Minting script derivation
#         pub_key_policy = ScriptPubkey(payment_verification_key.hash())
#         policy = ScriptAll([pub_key_policy])
#         policy_id = policy.hash()
#         print(f"Policy ID: {policy_id}")

#         ########################
#         """Define the token"""
#         ########################
#         tokenName = token_genesis.tokenName.encode('utf-8')
#         mintAsset = MultiAsset.from_primitive(
#             {
#                 policy_id.payload: {
#                     tokenName: token_genesis.tokenAmount,  
#                 }
#             }
#         )

#         ########################
#         """2. Build transaction"""
#         ########################
#         # Create a transaction builder
#         builder = TransactionBuilder(chain_context)

#         must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
#         # Since an InvalidHereAfter
#         builder.ttl = must_before_slot.after

#         ########################
#         """Create metadata"""
#         ########################
#         metadata = {
#             721: {  
#                 policy_id.payload.hex(): {
#                     tokenName: token_genesis.metadata,
#                 }
#             }
#         }

#         auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
#         # Set transaction metadata
#         builder.auxiliary_data = auxiliary_data

#         builder.mint = mintAsset
#         builder.native_scripts = [policy]
        
#         # Add user own address as the input address
#         builder.add_input_address(address)

#         min_val = min_lovelace(
#             chain_context, output=TransactionOutput(address, Value(0, mintAsset))
#         )
#         builder.add_output(TransactionOutput(address, Value(min_val, mintAsset)))

#         signed_tx = builder.build_and_sign([payment_skey], change_address=address)
#         tx_id = signed_tx.transaction_body.hash().hex()
#         chain_context.submit_tx(signed_tx)

#         final_response = {
#             "success": True,
#             "msg": f'Big Bang creation of tokens: {token_genesis.token_name}',
#             "tx_id": tx_id
#         }

#         return final_response
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
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



@router.post("/min-lovelace/", status_code=201,
summary="Given utxo output details, obtain calculated min ADA required",
    response_description="Min Ada required for the utxo in lovelace",)


async def minLovelace(addressDestin: pydantic_schemas.AddressDestin, datum_hash: Optional[str] = None, datum: Optional[dict[str, str]] = {}, script: Optional[dict[str, str]] = {}) -> int:
    
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

        min_val = min_lovelace(chain_context, output)

        return min_val
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tx-from-cbor/", status_code=201,
summary="Deserialized a transaction provided in cbor format to get the fee",
    response_description="Fee in lovelace",)



async def getFeeFromCbor(txcbor: str) -> int:

    """Transaaction body desisialized \n
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