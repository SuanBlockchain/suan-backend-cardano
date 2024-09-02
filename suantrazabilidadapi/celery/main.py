from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.commands.search.field import TextField  # , NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

from redis import asyncio as aioredis
import logging
import os


async def redis_config(index_name: str):

    # redis_url = "redis://localhost:6379/0"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    logging.info(f"Connecting to redis using: {redis_url}")

    rdb = aioredis.from_url(redis_url, decode_responses=True)
    schema = (
        TextField("$.action", as_name="action"),
        TextField("$.status", as_name="status"),
        TextField("$.destinAddress", as_name="destinAddress"),
        TextField("$.wallet_id", as_name="wallet_id"),
        TextField("$.token_string", as_name="token_string"),
    )

    try:
        # Check if the index already exists by trying to list its info
        index_name_redis = await rdb.ft(index_name).info()
        if index_name_redis == index_name:
            logging.info(f"Index {index_name} already exists.")

    except ResponseError as e:
        if "Unknown index name" in e.args[0]:
            await rdb.ft(index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=["AccessToken:"], index_type=IndexType.JSON
                ),
            )
            logging.info(f"Index {index_name} created successfully.")

    # Close the connection if needed
    await rdb.close()


#########################
# lifespan function that starts and ends when the fastapi application is started or ended
#########################
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Define the schema to store blockchain requests in redis
    index_name = "idx:AccessToken"
    await redis_config(index_name)

    try:
        yield
    finally:
        pass
