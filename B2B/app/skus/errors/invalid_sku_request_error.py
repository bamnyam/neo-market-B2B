from app.skus.errors.sku_create_error import SkuCreateError


class InvalidSkuRequestError(SkuCreateError):
    code = "INVALID_REQUEST"
    status_code = 400

    def __init__(self, message):
        self.message = message
