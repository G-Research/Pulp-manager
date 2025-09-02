"""implementation of the basic repository repo
"""

from datetime import datetime
from .base import Pulp3BaseModel


class SigningService(Pulp3BaseModel):
    """SigningService is used to sign certain content of repos to give it trust
    """

    pulp_href: str
    pulp_created: datetime
    name: str
    public_key: str
    pubkey_fingerprint: str
    script: str
