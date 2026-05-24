from app.skus.errors.sku_create_error import SkuCreateError


class ProductNotOwnerError(SkuCreateError):
    code = "NOT_OWNER"
    message = "Product does not belong to the authenticated seller"
    status_code = 403
