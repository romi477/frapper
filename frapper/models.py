# python3

from typing import List
from pydantic import BaseModel

from .tools import TO_DO


# class ItemMixin(BaseModel):

#     _table = tuple()
#     _table_name = None

#     @staticmethod
#     def response_keys():
#         return PhraseMeta._table

#     @staticmethod
#     def post_keys():
#         return PhraseMeta._table[1:-1]

#     def post_values(self):
#         return [getattr(self, x) for x in self.post_keys()]


class PhraseMeta(BaseModel):

    _table = (
        'id',
        'state',
        'channel_id',
        'message_id',
        'message_date',
        'created_at',
    )

    state: str = TO_DO
    channel_id: str
    message_id: int
    message_date: str

    @staticmethod
    def response_keys():
        return PhraseMeta._table

    @staticmethod
    def post_keys():
        return PhraseMeta._table[1:-1]

    def post_values(self):
        return [getattr(self, x) for x in self.post_keys()]


class PhraseMetaList(BaseModel):

    phrase_meta: List[PhraseMeta]

    @staticmethod
    def response_keys():
        return PhraseMeta.response_keys()

    @staticmethod
    def post_keys():
        return PhraseMeta.post_keys()


class PhrasePl(BaseModel):

    _table = (
        'id',
        'meta_id',
        'state',
        'active',
        'target',
        'target_tag',
        'translate',
        'translate_tag',
        'target_mask',
        'translate_mask',
        'message_id',
        'message_date',
        'metadata',
        'created_at',
    )

    meta_id: int
    state: str = TO_DO
    active: bool
    target: str
    target_tag: str
    translate: str
    translate_tag: str
    target_mask: str
    translate_mask: str
    message_id: int
    message_date: str
    metadata: str

    @staticmethod
    def response_keys():
        return PhrasePl._table

    @staticmethod
    def post_keys():
        return PhrasePl._table[1:-1]

    def post_values(self):
        return [getattr(self, x) for x in self.post_keys()]


class PhrasePlList(BaseModel):

    phrase_pl: List[PhrasePl]

    @staticmethod
    def response_keys():
        return PhrasePl.response_keys()

    @staticmethod
    def post_keys():
        return PhrasePl.post_keys()
