from app.products.errors.product_delete_error import ProductDeleteError


class ProductNotFoundError(ProductDeleteError):
    code = "NOT_FOUND"
    message = "Product not found"
    status_code = 404
