from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceCreateError(Exception):
    code: str
    message: str
    status_code: int
