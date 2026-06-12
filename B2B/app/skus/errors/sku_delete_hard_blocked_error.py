from app.skus.errors.sku_delete_error import SkuDeleteError


class SkuDeleteHardBlockedError(SkuDeleteError):
    code = "FORBIDDEN"
    message = "Cannot delete SKU of hard-blocked product"
    status_code = 403
