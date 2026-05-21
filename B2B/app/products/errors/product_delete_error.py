class ProductDeleteError(Exception):
    code = "PRODUCT_DELETE_ERROR"
    message = "Product delete error"
    status_code = 400
