from app.skus.errors.sku_delete_error import SkuDeleteError


class SkuDeleteActiveReservesError(SkuDeleteError):
    code = "CONFLICT"
    message = "Cannot delete SKU with active reserves"
    status_code = 409
