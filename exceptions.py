class TelegramSendingProblemError(Exception):
    pass

class APIAccessError(Exception):
    pass

class APIWrongStatusError(Exception):
    pass

class ResponseError(Exception):
    pass

class ResponseTypeError(TypeError):
    pass

class ParseStatusError(KeyError):
    pass

class HomeworkEmptyError(Exception):
    pass
