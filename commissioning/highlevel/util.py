from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI

def new_quota_holder_client(QH_URL):
    """
    Create a new quota holder api client
    """
    class QuotaholderHTTP(HTTP_API_Client):
        api_spec = QuotaholderAPI()

    return QuotaholderHTTP(QH_URL)
