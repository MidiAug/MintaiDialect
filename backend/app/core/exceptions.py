from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_502_BAD_GATEWAY


class ValidationError(HTTPException):
    def __init__(self, detail: str = "请求参数不合法", status_code: int = HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class LLMServiceError(HTTPException):
    def __init__(self, detail: str = "LLM 服务异常", status_code: int = HTTP_502_BAD_GATEWAY):
        super().__init__(status_code=status_code, detail=detail)


class TTSServiceError(HTTPException):
    def __init__(self, detail: str = "TTS 服务异常", status_code: int = HTTP_502_BAD_GATEWAY):
        super().__init__(status_code=status_code, detail=detail)


class ASRServiceError(HTTPException):
    def __init__(self, detail: str = "ASR 服务异常", status_code: int = HTTP_502_BAD_GATEWAY):
        super().__init__(status_code=status_code, detail=detail)


