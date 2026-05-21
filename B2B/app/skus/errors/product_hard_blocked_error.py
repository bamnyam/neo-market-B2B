from app.skus.errors.sku_create_error import SkuCreateError


class ProductHardBlockedError(SkuCreateError):
    code = "FORBIDDEN"
    message = "Cannot add SKU to hard-blocked product"
    status_code = 403
