from collections.abc import Mapping, Sequence

class InvalidTokenError(Exception): ...
class ExpiredSignatureError(InvalidTokenError): ...

def encode(
    payload: Mapping[str, object],
    key: str,
    algorithm: str = ...,
) -> str: ...
def decode(
    jwt: str,
    key: str,
    algorithms: Sequence[str],
) -> dict[str, object]: ...
