
from pydantic import BaseModel


class StaticIPv6Address(BaseModel):
    address: str
    prefix: int

class WlanProfile(BaseModel):
    name: str
    uuid: str
    static_ipv6_addresses: list[StaticIPv6Address] = []
