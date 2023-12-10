# python3

import sqlite3

from fastapi import FastAPI

from .settings import FRAPPER_DB
from .models import PhrasePl, PhraseMeta, PhrasePlList, PhraseMetaList


app = FastAPI()


@app.get('/phrase-pl/target-tag')
def read_target_tag(tag: str):
    query = f"""
        SELECT * FROM phrase_pl
        WHERE active = true AND lower(target_tag) LIKE '%{tag}%'
    """
    records = _generic_select(query)
    record_list = PhrasePl.serialize_data(records)
    return {
        PhrasePl._table_name: record_list,
    }


@app.get('/phrase-pl/translate-tag')
def read_translate_tag(tag: str):
    query = f"""
        SELECT * FROM phrase_pl
        WHERE active = true AND lower(translate_tag) LIKE '%{tag}%'
    """
    records = _generic_select(query)
    record_list = PhrasePl.serialize_data(records)
    return {
        PhrasePl._table_name: record_list,
    }


@app.get('/phrase-pl/fetch-count')
def read_target_count(count: int = 3):
    query = f"""
        SELECT * FROM phrase_pl
        WHERE active = true
        ORDER BY RANDOM() LIMIT {count}
    """
    records = _generic_select(query)
    record_list = PhrasePl.serialize_data(records)
    return {
        PhrasePl._table_name: record_list,
    }


@app.get('/phrase-pl/fetch-slice')
def read_target_slice(since_id: int, count: int = 10):
    query = f"""
        SELECT * FROM phrase_pl
        WHERE id > {since_id} AND active = true
        LIMIT {count}
    """
    records = _generic_select(query)
    record_list = PhrasePl.serialize_data(records)
    return {
        PhrasePl._table_name: record_list,
    }


@app.get('/phrase-pl/fetch-tail')
def read_target_from_tail(tail: int, count: int = 10):
    fetch = _fetch_one("SELECT MAX(id) FROM phrase_pl")

    since_id = (fetch and fetch[0]) - tail
    if since_id < 0:
        since_id = 0

    query = f"""
        SELECT * FROM phrase_pl
        WHERE id > {since_id} AND active = true
        ORDER BY RANDOM() LIMIT {count}
    """
    records = _generic_select(query)
    record_list = PhrasePl.serialize_data(records)
    return {
        PhrasePl._table_name: record_list,
    }


@app.post('/phrase-meta/')
def post_phrase_meta(model: PhraseMetaList):
    records, errors = _generic_insert(model)
    record_list = PhraseMeta.serialize_data(records)
    return {
        model._table_name: record_list,
        'errors': errors,
    }


@app.post('/phrase-pl/')
def post_phrase_pl(model: PhrasePlList):
    records, errors = _generic_insert(model)
    record_list = PhrasePl.serialize_data(records)
    return {
        model._table_name: record_list,
        'errors': errors,
    }


def _generic_select(query):
    conn = sqlite3.connect(FRAPPER_DB)
    cur = conn.cursor()
    cur.execute(query)
    records = cur.fetchall()
    conn.close()
    return records


def _generic_insert(model):
    conn = sqlite3.connect(FRAPPER_DB)
    cr = conn.cursor()

    records, errors = list(), list()
    for item in model.scan():
        insert_query = item.get_insert_query()
        values = item.post_values()
        try:
            cr.execute(insert_query, values)
        except sqlite3.IntegrityError as ex:
            errors.append({
                f'{item._table_name}.IntegrityError': ex.args,
                'insert_data': item.post_data(),
            })
        else:
            select_query = item.get_select_query()
            cr.execute(select_query, (cr.lastrowid,))
            records.append(cr.fetchone())

    conn.commit()
    conn.close()
    return records, errors


def _fetch_one(query):
    conn = sqlite3.connect(FRAPPER_DB)
    cr = conn.cursor()
    cr.execute(query)
    result = cr.fetchone()
    conn.close()
    return result
