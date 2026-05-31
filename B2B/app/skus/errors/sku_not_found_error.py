from app.skus.errors.sku_update_error import SkuUpdateError


class SkuNotFoundError(SkuUpdateError):
    code = "NOT_FOUND"
    message = "SKU not found"
    status_code = 404
