from app.skus.errors.sku_update_error import SkuUpdateError


class SkuProductHardBlockedError(SkuUpdateError):
    code = "FORBIDDEN"
    message = "Cannot edit hard-blocked product"
    status_code = 403
