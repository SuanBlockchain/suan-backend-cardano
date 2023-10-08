from dataclasses import dataclass
from logging import basicConfig, getLogger, INFO
import boto3
from time import sleep
from pyqldb.driver.qldb_driver import QldbDriver


logger = getLogger(__name__)
basicConfig(level=INFO)

session = boto3.Session(profile_name='suan')

class Constants:
    """Constant values used in the Qrdb class
    """
    # LEDGER_NAME: str = "project-tracking"
    REGION_NAME: str = "us-east-1"
    ACTIVE_STATE: str = "ACTIVE"
    LEDGER_CREATION_POLL_PERIOD_SEC: int = 10

@dataclass()
class Qrdb(Constants):

    def __post_init__(self):
        self.qldb_client = session.client('qldb', region_name=self.REGION_NAME)

    def _create_qldb_driver(self, ledger_name: str, region_name=None) -> QldbDriver:
        return QldbDriver(ledger_name=ledger_name, boto3_session=session)

    
    def create_ledger(self, ledger_name: str):
        logger.info("Let's create the ledger named: {}...".format(ledger_name))
        result = self.qldb_client.create_ledger(Name=ledger_name, PermissionsMode='ALLOW_ALL')
        logger.info('Success. Ledger state: {}.'.format(result.get('State')))
        return result

    def wait_for_active(self, ledger_name: str):
        """
        Wait for the newly created ledger to become active.

        :type name: str
        :param name: The ledger to check on.

        """
        logger.info('Waiting for ledger to become active...')
        while True:
            result = self.qldb_client.describe_ledger(Name=ledger_name)
            if result.get('State') == self.ACTIVE_STATE:
                logger.info('Success. Ledger is active and ready to use.')
                return result
            logger.info('The ledger is still creating. Please wait...')
            sleep(self.LEDGER_CREATION_POLL_PERIOD_SEC)

    def create_table(self, ledger_name: str, table_name: str) -> list:
        """
        Create a table with the specified name.

        :type ledger_name: str
        :param ledger_name: Name of the ledger to add indexes for.

        :type table_name: str
        :param table_name: Name of the table to create.

        :rtype: list
        :return: list with the table ids
        """
        logger.info("Creating the '{}' table...".format(table_name))
        statement = 'CREATE TABLE {}'.format(table_name)
        with self._create_qldb_driver(ledger_name, region_name=self.REGION_NAME) as driver:
            cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        
        logger.info('{} table created successfully.'.format(table_name))
        ret_val = list(map(lambda x: x.get("tableId"), cursor))
        return ret_val
    
    def create_index(self, ledger_name: str, table_name: str, index_attribute: str) -> int:
        """
        Create an index for a particular table.

        :type ledger_name: str
        :param ledger_name: Name of the ledger to add indexes for.

        :type table_name: str
        :param table_name: Name of the table to add indexes for.

        :type index_attribute: str
        :param index_attribute: Index to create on a single attribute.

        :rtype: int
        :return: The number of changes to the database.
        """
        logger.info("Creating index on '{}'...".format(index_attribute))
        statement = 'CREATE INDEX on {} ({})'.format(table_name, index_attribute)
        with self._create_qldb_driver(ledger_name, region_name=self.REGION_NAME) as driver:
            cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        
        if isinstance(len(list(cursor)), int):
            return True
        else:
            return False