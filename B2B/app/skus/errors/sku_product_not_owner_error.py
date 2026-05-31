from app.skus.errors.sku_update_error import SkuUpdateError


class SkuProductNotOwnerError(SkuUpdateError):
    code = "NOT_OWNER"
    message = "Product does not belong to the authenticated seller"
    status_code = 403
