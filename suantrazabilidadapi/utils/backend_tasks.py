# # import asyncio
# # from rocketry import Rocketry
# # from rocketry.conds import every

# # import koios_api
# from pycardano import (
#     Address,
#     AlonzoMetadata,
#     AuxiliaryData,
#     ExtendedSigningKey,
#     HDWallet,
#     Metadata,
#     MultiAsset,
#     PaymentVerificationKey,
#     ScriptAll,
#     ScriptPubkey,
#     TransactionBuilder,
#     TransactionOutput,
#     Value,
#     min_lovelace,
# )

# from plataforma import Plataforma
# from generic import Constants
# from blockchain import CardanoNetwork

# # app = Rocketry(config={"task_execution": "async"})


# # @app.task(every("30 seconds", based="finish"))
# def do_permanently():
#     # "This runs for really long time"
#     r = Plataforma().getWalletbyToken()
#     if r["data"].get("data", None) is not None:
#         wallet_list = r["data"]["data"]["listWallets"]["items"]
#         if wallet_list != []:
#             r = Plataforma().getWallet(
#                 "id", "575a7f01272dd95a9ba2696e9e3d4895fe39b12350f7fa88a301b3ad"
#             )
#             walletInfo = r["data"]["data"]["getWallet"]
#             if walletInfo is None:
#                 raise ValueError(
#                     f"Wallet with id: 575a7f01272dd95a9ba2696e9e3d4895fe39b12350f7fa88a301b3ad does not exist in DynamoDB"
#                 )
#             else:
#                 seed = walletInfo["seed"]
#                 hdwallet = HDWallet.from_seed(seed)
#                 child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#                 payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

#                 payment_vk = PaymentVerificationKey.from_primitive(
#                     child_hdwallet.public_key
#                 )

#                 master_address = Address.from_primitive(walletInfo["address"])
#                 ########################
#                 """3. Create the script and policy"""
#                 ########################
#                 # A policy that requires a signature from the policy key we generated above
#                 pub_key_policy = ScriptPubkey(payment_vk.hash())  # type: ignore
#                 # A time policy that disallows token minting after 10000 seconds from last block
#                 # must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
#                 # Combine two policies using ScriptAll policy
#                 policy = ScriptAll([pub_key_policy])
#                 # Calculate policy ID, which is the hash of the policy
#                 policy_id = policy.hash()
#                 print(f"Policy ID: {policy_id}")
#                 with open(Constants().PROJECT_ROOT / "policy.id", "a+") as f:
#                     f.truncate(0)
#                     f.write(str(policy_id))
#                 # Create the final native script that will be attached to the transaction
#                 native_scripts = [policy]
#                 ########################
#                 """Define NFT"""
#                 ########################
#                 tokenName = b"SandboxSuanAccess1"
#                 my_nft_alternative = MultiAsset.from_primitive(
#                     {
#                         policy_id.payload: {
#                             tokenName: 1,
#                         }
#                     }
#                 )
#                 multi_asset_mint = MultiAsset.from_primitive(
#                     {
#                         policy_id.payload: {
#                             tokenName: len(wallet_list),
#                         }
#                     }
#                 )
#                 ########################
#                 """Create metadata"""
#                 ########################
#                 metadata = {
#                     721: {
#                         policy_id.payload.hex(): {
#                             tokenName: {
#                                 "description": "NFT con acceso a marketplace en Sandbox",
#                                 "name": "Token NFT SandBox",
#                             },
#                         }
#                     }
#                 }
#                 # Place metadata in AuxiliaryData, the format acceptable by a transaction.
#                 auxiliary_data = AuxiliaryData(
#                     AlonzoMetadata(metadata=Metadata(metadata))
#                 )
#                 """Build transaction"""
#                 chain_context = CardanoNetwork().get_chain_context()
#                 # Create a transaction builder
#                 builder = TransactionBuilder(chain_context)
#                 # Add our own address as the input address
#                 builder.add_input_address(master_address)
#                 # Since an InvalidHereAfter rule is included in the policy, we must specify time to live (ttl) for this transaction
#                 # builder.ttl = must_before_slot.after
#                 # Set nft we want to mint
#                 builder.mint = multi_asset_mint
#                 # Set native script
#                 builder.native_scripts = native_scripts
#                 # Set transaction metadata
#                 builder.auxiliary_data = auxiliary_data

#                 for wallet in wallet_list:
#                     # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
#                     min_val = min_lovelace(
#                         chain_context,
#                         output=TransactionOutput(
#                             wallet["address"], Value(0, my_nft_alternative)
#                         ),
#                     )
#                     # Send the NFT to our own address + 500 ADA
#                     builder.add_output(
#                         TransactionOutput(
#                             wallet["address"], Value(min_val, my_nft_alternative)
#                         )
#                     )
#                     builder.add_output(
#                         TransactionOutput(wallet["address"], Value(50000000))
#                     )

#                 # Create final signed transaction
#                 signed_tx = builder.build_and_sign(
#                     [payment_skey], change_address=master_address
#                 )
#                 # Submit signed transaction to the network
#                 tx_id = signed_tx.transaction_body.hash().hex()
#                 chain_context.submit_tx(signed_tx)

#                 response_wallet = []
#                 for wallet in wallet_list:
#                     variables = {
#                         "id": wallet["id"],
#                     }
#                     responseWallet = Plataforma().updateWalletWithToken(variables)
#                     if responseWallet["success"] == True:
#                         response_wallet.append(
#                             {
#                                 "success": True,
#                                 "msg": f"Wallet updated and token sent",
#                                 "wallet_id": wallet["id"],
#                                 "address": wallet["address"],
#                             }
#                         )
#                     else:
#                         response_wallet.append(
#                             {
#                                 "success": False,
#                                 "msg": f"Problems updating or token not sent",
#                                 "wallet_id": wallet["id"],
#                                 "address": wallet["address"],
#                                 "data": responseWallet["error"],
#                             }
#                         )
#                 final_response = {
#                     "success": True,
#                     "msg": "Wallet updated and token sent",
#                     "data": response_wallet,
#                 }

#         else:
#             final_response = {
#                 "success": False,
#                 "msg": "No data found",
#                 "data": None,
#             }

#     else:
#         if r["success"] == True:
#             final_response = {
#                 "success": False,
#                 "msg": "Error fetching data",
#                 "data": r["data"]["errors"],
#             }
#         else:
#             final_response = {
#                 "success": False,
#                 "msg": "Error fetching data",
#                 "data": r["error"],
#             }
#     print(final_response)
#     return final_response

#     # address = "addr_test1vqkge7txl2vdw26efyv7cytjl8l6n8678kz09agc0r34pdss0xtmp"
#     # address_info = koios_api.get_address_info(address)
#     # print(address_info)
#     # return address_info


# # @app.task(every('2 seconds', based="finish"))
# # async def do_short():
# #     "This runs for short time"
# #     await asyncio.sleep(1)

# # @app.task(every('20 seconds', based="finish"))
# # async def do_long():
# #     "This runs for long time"
# #     await asyncio.sleep(60)

# # @app.task(every('10 seconds', based="finish"))
# # async def do_fail():
# #     "This fails constantly"
# #     await asyncio.sleep(10)
# #     raise RuntimeError("Whoops!")

# if __name__ == "__main__":
#     # Run only Rocketry
#     # app.run()

#     do_permanently()
