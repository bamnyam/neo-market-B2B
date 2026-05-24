from app.products.errors.product_delete_error import ProductDeleteError


class ProductNotOwnerError(ProductDeleteError):
    code = "NOT_OWNER"
    message = "Product does not belong to the authenticated seller"
    status_code = 403
