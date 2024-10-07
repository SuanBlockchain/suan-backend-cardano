class PlataformaException(Exception):
    """Generic exception"""

class ResponseTypeError(PlataformaException):
    """Response Type exception"""
class ResponseProcessingError(PlataformaException):
    """Response processing exception"""
class ResponseDynamoDBException(PlataformaException):
    """Response DynamoDB exception"""
class ResponseFindingUtxo(PlataformaException):
    """Response finding utxo exception"""
