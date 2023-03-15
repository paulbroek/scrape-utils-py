"""models.py.

FastAPI response and message moels
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from pydantic import BaseModel

###########################
##### BASE CLASSES
###########################


# T = TypeVar("T")


class Response(ABC):
    @abstractmethod
    def get_message(self) -> str:
        pass

    # def get_message(self) -> str:
    #     if isinstance(self.message, T):
    #         return self.message.value
    #     return self.message


###########################
##### MESSAGES
###########################


class PushUrlMessage(str, Enum):
    INCORRECT_URL = "url should start with:"
    EXISTS = "url exists in db, pass `force=True` to override"
    ERROR = "could not push url to redis"
    ERROR_OTHER = "other error"
    SUCCESS = "pushed url to redis"
    EXISTS_PUSHED_QUEUE = "url exists db, so sending add_to_row request to rabbitmq"


class ItemResponseMessage(str, Enum):
    ERROR = "internal error: "
    SUCCESS = "success"
    NOT_EXISTS = "item does not exist in db"


# class BookResponseMessage(ResponseMessageBase):
#     NOT_EXISTS = "book does not exist in db"

# class AuthorResponseMessage(ResponseMessageBase):
#     NOT_EXISTS = "author does not exist in db"

###########################
##### RESPONSE MODELS
###########################


class PushUrlResponse(Response, BaseModel):
    message: PushUrlMessage | str
    success: int

    def get_message(self) -> str:
        if isinstance(self.message, PushUrlMessage):
            return self.message.value
        return self.message


class ItemResponse(Response, BaseModel):
    message: ItemResponseMessage | str
    item: Optional[dict]
    success: int

    def get_message(self) -> str:
        if isinstance(self.message, PushUrlMessage):
            return self.message.value
        return self.message


class nitemResponse(BaseModel):
    total: int


class nitemDetailResponse(BaseModel):
    total: int
    book: Optional[int]
    author: Optional[int]


###########################
##### PAYLOAD MODELS
###########################


class PushRedisPayload(BaseModel):
    url: str
