# python3

from typing import List
from pydantic import BaseModel


class TableMixin:

    __fields__ = dict()
    _table_name = None

    @classmethod
    def table_columns_cls(cls):
        return tuple(cls.__fields__.keys())

    @classmethod
    def post_keys_cls(cls):
        return cls.table_columns_cls()[1:-1]

    def table_columns(self):
        return self.__class__.table_columns_cls()


class ItemMixin(TableMixin):

    _insert_query_pattern = 'INSERT INTO %s (%s) VALUES (%s)'
    _select_query_pattern = 'SELECT %s FROM %s WHERE id = ?'

    def post_keys(self):
        return tuple(self.post_data().keys())

    def post_values(self):
        return [getattr(self, x) for x in self.post_keys()]

    def post_data(self):
        return self.dict(exclude={'id', 'created_at'})

    def get_insert_query(self):
        post_keys = self.post_keys()
        args = (self._table_name, ', '.join(post_keys), ', '.join('?' for _ in post_keys))
        return self._insert_query_pattern % args

    def get_select_query(self):
        response_keys = self.table_columns()
        args = (', '.join(response_keys), self._table_name)
        return self._select_query_pattern % args

    @classmethod
    def serialize_data(cls, records):
        keys = cls.table_columns_cls()
        return [dict(zip(keys, x)) for x in records]


class ItemListBase(BaseModel, TableMixin):

    errors: list = []

    def scan(self):
        for x in getattr(self, self._table_name):
            yield x


class PhraseMeta(BaseModel, ItemMixin):

    _table_name = 'phrase_meta'

    id: int = 0
    state: str = 'todo'
    channel_id: str
    message_id: int
    message_date: str
    with_error: bool = False
    created_at: str = ''


class PhraseMetaList(ItemListBase):

    _table_name = PhraseMeta._table_name

    phrase_meta: List[PhraseMeta]


class PhrasePl(BaseModel, ItemMixin):

    _table_name = 'phrase_pl'

    id: int = 0
    meta_id: int = 0
    state: str = 'todo'
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
    created_at: str = ''


class PhrasePlList(ItemListBase):

    _table_name = PhrasePl._table_name

    phrase_pl: List[PhrasePl]
