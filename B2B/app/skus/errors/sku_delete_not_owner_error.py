from app.skus.errors.sku_delete_error import SkuDeleteError


class SkuDeleteNotOwnerError(SkuDeleteError):
    code = "NOT_OWNER"
    message = "SKU does not belong to the authenticated seller"
    status_code = 403
