import time
from algosdk.future.transaction import PaymentTxn, AssetTransferTxn, assign_group_id, LogicSigTransaction
from algosdk.error import AlgodHTTPError
from base64 import b64decode

# constants
PARAMETER_SCALE_FACTOR = 1000000

def int_to_bytes(i):
    """Convert int to bytes
    """
    return i.to_bytes(8, "big")


def sign_and_submit_transactions(client, transactions, signed_transactions, sender, sender_sk):
    for i, txn in enumerate(transactions):
        if txn.sender == sender:
            signed_transactions[i] = txn.sign(sender_sk)
    
    txid = client.send_transactions(signed_transactions)
    return wait_for_confirmation(client, txid)


def wait_for_confirmation(client, txid):
    """Waits for a transaction with id txid to complete. Returns dict with transaction information 
    after completion.

    :param client: algod client
    :type client: :class:`AlgodClient`
    :param txid: id of the sent transaction
    :type txid: string
    :return: dict of transaction information
    :rtype: dict
    """
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for confirmation")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    txinfo['txid'] = txid
    print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo


def send_and_wait(algod_client, stxns):
    """Send list of signed transactions and wait for completion

    :param algod_client: algod client
    :type algod_client: :class:`AlgodClient`
    :param stxns: list of signed transactions
    :type stxns: list
    :return: dict of transaction information
    :rtype: dict
    """
    # Send transaction
    txid = algod_client.send_transactions(stxns)
    # Await confirmation
    wait_for_confirmation(algod_client, txid)
    # Gather results
    transaction_response = algod_client.pending_transaction_info(txid)
    # Return response
    return transaction_response


def get_application_global_state(algod_client, application_id):
    """Returns dictionary of global state for a given application

    :param algod_client: :class:`AlgodClient` object for interacting with network
    :type algod_client: :class:`AlgodClient`
    :param application_id: application id
    :type application_id: int
    :return: dictionary of global state for given application
    :rtype: dict
    """

    application_info = algod_client.application_info(application_id)
    application_global_state = application_info["params"]["global-state"]
    formatted_global_state = {}
    for keyvalue in application_global_state:
        key, value = keyvalue["key"], keyvalue["value"]
        key_formatted = b64decode(key).decode("utf-8")
        value = value["uint"] if value["type"] == 2 else value["bytes"]
        formatted_global_state[key_formatted] = value

    return formatted_global_state


def get_application_local_state(algod_client, address, application_id):
    """Returns dictionary of global state for a given application

    :param algod_client: :class:`AlgodClient` object for interacting with network
    :type algod_client: :class:`AlgodClient`
    :param address: an account address
    :type address: str
    :param application_id: application id
    :type application_id: int
    :return: dictionary of local state of account for given application
    :rtype: dict
    """

    account_info = algod_client.account_info(address)
    application_local_state = account_info["apps-local-state"]
    formatted_local_state = {}
    for state in application_local_state:
        if (state["id"] == application_id) and (state["key-value"]):
            for keyvalue in state["key-value"]:
                key, value = keyvalue["key"], keyvalue["value"]
                key_formatted = b64decode(key).decode("utf-8")
                value = value["uint"] if value["type"] == 2 else value["bytes"]
                formatted_local_state[key_formatted] = value

    return formatted_local_state


def get_account_balances(algod_client, address, filter_zero_balances=False):
    """Returns dictionary of global state for a given application

    :param algod_client: :class:`AlgodClient` object for interacting with network
    :type algod_client: :class:`AlgodClient`
    :param address: an account address
    :type address: str
    :param filter_zero_balances: include assets with zero balance
    :type filter_zero_balances: bool, optional
    :return: dictionary of balances for given account
    :rtype: dict
    """

    balances = {}
    account_info = algod_client.account_info(address)
    if filter_zero_balances:
        if account_info["amount"] > 0:
            balances[1] = account_info["amount"]
    else:
        balances[1] = account_info["amount"]

    assets = account_info.get("assets", [])
    for asset in assets:
        asset_id, amount = asset["asset-id"], asset["amount"]
        if filter_zero_balances:
            if amount > 0:
                balances[asset_id] = amount
        else:
            balances[asset_id] = amount

    return balances


def get_params(algod_client, fee=1000, flat_fee=True):
    """Returns dictionary of global state for a given application

    :param algod_client: :class:`AlgodClient` object for interacting with network
    :type algod_client: :class:`AlgodClient`
    :param fee: fee in microalgos
    :type fee: int, optional
    :param flat_fee: whether the specified fee is a flat fee
    :type flat_fee: bool, optional
    :return: :class:`SuggestedParams` object for sending transactions
    :rtype: :class:`SuggestedParams`
    """

    params = algod_client.suggested_params()
    params.fee = fee
    params.flat_fee = flat_fee

    return params


def get_payment_txn(params, sender, receiver, amount, asset_id=1):
    """Returns dictionary of global state for a given application

    :param params: :class:`SuggestedParams` object for interacting with network
    :type params: :class:`SuggestedParams`
    :param sender: sender account address
    :type sender: str
    :param receiver: receiver account address
    :type receiver: str
    :param amount: amount of asset to send
    :type amount: int
    :param asset_id: asset id if AssetTransferTxn
    :type asset_id: int
    :return: :class:`PaymentTxn` or :class:`AssetTransferTxn` object for sending an asset
    :rtype: :class:`PaymentTxn` or :class:`AssetTransferTxn`
    """

    if (asset_id == 1):
        return PaymentTxn(
            sender=sender,
            sp=params,
            receiver=receiver,
            amt=amount,
            note=int(time.time() * 1000 * 1000).to_bytes(8, 'big')
        )
    else:
        return AssetTransferTxn(
            sender=sender,
            sp=params,
            receiver=receiver,
            amt=amount,
            index=asset_id,
            note=int(time.time() * 1000 * 1000).to_bytes(8, 'big')
        )

class TransactionGroup:

    def __init__(self, transactions):
        """Constructor method for :class:`TransactionGroup` class

        :param transactions: list of unsigned transactions
        :type transactions: list
        """
        transactions = assign_group_id(transactions)
        self.transactions = transactions
        self.signed_transactions = [None for _ in self.transactions]

    def sign_with_private_key(self, address, private_key):
        """Signs the transactions with specified private key and saves to class state

        :param address: account address of the user
        :type address: string
        :param private_key: private key of user
        :type private_key: string
        """
        for i, txn in enumerate(self.transactions):
            self.signed_transactions[i] = txn.sign(private_key)
    
    def sign_with_private_keys(self, private_keys, is_logic_sig):
        """Signs the transactions with specified private key and saves to class state

        :param private_keys: private key of user
        :type private_keys: string
        :param is_logic_sig: if given "pkey" is a logicsig
        :type is_logic_sig: list
        """
        assert(len(private_keys) == len(self.transactions))
        assert(len(private_keys) == len(is_logic_sig))
        for i, txn in enumerate(self.transactions):
            if is_logic_sig[i]:
                self.signed_transactions[i] = LogicSigTransaction(txn, private_keys[i])
            else:
                self.signed_transactions[i] = txn.sign(private_keys[i])
        
    def submit(self, algod, wait=False):
        """Submits the signed transactions to network using the algod client

        :param algod: algod client
        :type algod: :class:`AlgodClient`
        :param wait: wait for txn to complete, defaults to False
        :type wait: boolean, optional
        :return: dict of transaction id
        :rtype: dict
        """
        try:
            txid = algod.send_transactions(self.signed_transactions)
        except AlgodHTTPError as e:
            raise Exception(str(e))
        if wait:
            return wait_for_confirmation(algod, txid)
        return {"txid": txid}

    def __add__(self, transaction_group):
        """Combines two transaction groups together in order

        :param transaction_group: transaction group
        :type transaction_group: :class:`TransactionGroup`
        :return: combined transaction group
        :rtype: :class:`TransactionGroup`
        """

        aggregate_transactions = self.transactions + transaction_group.transactions
        # set group to None
        for i in range(len(aggregate_transactions)):
            aggregate_transactions[i].group = None
        new_transaction_group = TransactionGroup(aggregate_transactions)
        return new_transaction_group