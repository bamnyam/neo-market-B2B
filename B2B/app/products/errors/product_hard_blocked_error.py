from app.products.errors.product_delete_error import ProductDeleteError


class ProductHardBlockedError(ProductDeleteError):
    code = "FORBIDDEN"
    message = "Cannot edit hard-blocked product"
    status_code = 403
