from app.skus.errors.sku_delete_error import SkuDeleteError


class SkuDeleteNotFoundError(SkuDeleteError):
    code = "NOT_FOUND"
    message = "SKU not found"
    status_code = 404
