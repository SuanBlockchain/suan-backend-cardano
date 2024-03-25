
from utils.mock import MockChainContext, MockUser
from typing import List, Optional
from functools import cache

import pycardano as py

def setup_user(context: MockChainContext):
    user = MockUser(context)
    user.fund(100000000)  # 100 ADA
    return user

def setup_users(context: MockChainContext) -> List[MockUser]:
    users = []
    for _ in range(3):
        u = MockUser(context)
        u.fund(10_000_000)  # 10 ADA
        users.append(u)
    return users

@cache
def setup_context(script: Optional[str] = None):
    context = MockChainContext()
    # enable opshin validator debugging
    # context.opshin_scripts[plutus_script] = inversionista.validator
    return context, setup_user(context), setup_user(context)

def send_value(
    context: MockChainContext, u1: MockUser, value: py.Value, u2: MockUser
):
    builder = py.TransactionBuilder(context)
    builder.add_input_address(u1.address)
    builder.add_output(py.TransactionOutput(u2.address, value))
    tx = builder.build_and_sign([u1.signing_key], change_address=u1.address)
    context.submit_tx(tx)
    return context


def test_simple_spend():
    # Create the mock py chain context
    context = MockChainContext()
    # Create 3 users and assign each 10 ADA
    users = setup_users(context)
    # Send 1 ADA from user 0 to user 1
    send_value(context, users[0], py.Value(coin=1_000_000), users[1])
    # Send 1 ADA from user 1 to user 2
    send_value(context, users[1], py.Value(coin=1_000_000), users[2])


def test_not_enough_funds():
    context = MockChainContext()
    users = setup_users(context)
    # Send 100 ADA from user 0 to user 1
    try:
        send_value(context, users[0], py.Value(coin=100_000_000), users[1])
        validates = True
    except py.UTxOSelectionException:
        validates = False
    assert not validates, "transaction must fail"


if __name__ == "__main__":
    test_simple_spend()