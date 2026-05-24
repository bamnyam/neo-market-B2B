from app.skus.errors.sku_create_error import SkuCreateError


class ProductNotFoundError(SkuCreateError):
    code = "NOT_FOUND"
    message = "Product not found"
    status_code = 404
