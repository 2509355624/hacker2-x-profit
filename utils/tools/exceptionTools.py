class CustomException(Exception):
    def __init__(self, code=500, msg="Unknown error"):
        self.code = code
        self.msg = msg
        super().__init__(self.msg)

class CustomErrors:
    ERROR_912 = 912
    ERROR_500 = 500
