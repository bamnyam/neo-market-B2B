from app.products.errors.product_delete_error import ProductDeleteError


class ProductAlreadyDeletedError(ProductDeleteError):
    code = "INVALID_REQUEST"
    message = "Product already deleted"
    status_code = 400
