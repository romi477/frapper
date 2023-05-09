# python3

import sqlite3

from fastapi import FastAPI

from .models import PhraseMetaList, PhrasePlList
from .settings import FRAPPER_DB


app = FastAPI()


@app.post('/phrase-meta/')
def post_phrase_meta(model: PhraseMetaList):
    post_keys = model.post_keys()

    insert_query = f"""
        INSERT INTO phrase_meta ({', '.join(post_keys)})
        VALUES ({', '.join('?' for _ in post_keys)})
    """

    response_keys = model.response_keys()

    select_query = f"""
        SELECT {', '.join(response_keys)} FROM phrase_meta
        WHERE id = ?
    """

    conn = sqlite3.connect(FRAPPER_DB)
    cr = conn.cursor()

    result, errors = list(), list()
    for item in model.phrase_meta:
        try:
            cr.execute(insert_query, item.post_values())
        except sqlite3.IntegrityError as ex:
            errors.append({
                'phrase_meta.IntegrityError': ex.args,
                'values': item.post_values(),
            })
        else:
            cr.execute(select_query, (cr.lastrowid,))
            result.append(
                dict(zip(response_keys, cr.fetchone())),
            )

    conn.commit()
    conn.close()

    return {
        'phrase_meta': result,
        'errors': errors,
    }


@app.post('/phrase-pl/')
def post_phrase_pl(model: PhrasePlList):
    post_keys = model.post_keys()

    insert_query = f"""
        INSERT INTO phrase_pl ({', '.join(post_keys)})
        VALUES ({', '.join('?' for _ in post_keys)})
    """

    response_keys = model.response_keys()

    select_query = f"""
        SELECT {', '.join(response_keys)} FROM phrase_pl
        WHERE id = ?
    """

    conn = sqlite3.connect(FRAPPER_DB)
    cr = conn.cursor()

    result, errors = list(), list()
    for item in model.phrase_pl:
        try:
            cr.execute(insert_query, item.post_values())
        except sqlite3.IntegrityError as ex:
            errors.append({
                'phrase_pl.IntegrityError': ex.args,
                'values': item.post_values(),
            })
        else:
            cr.execute(select_query, (cr.lastrowid,))
            result.append(
                dict(zip(response_keys, cr.fetchone())),
            )

    conn.commit()
    conn.close()

    return {
        'phrase_pl': result,
        'errors': errors,
    }


@app.get('/phrase-pl/target-tag')
def read_target_tag(tag: str):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrase_pl
        WHERE active = true AND lower(target_tag) LIKE '%{tag}%'
    """
    return _execute_fetch_query(query)


@app.get('/phrase-pl/translate-tag')
def read_translate_tag(tag: str):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrase_pl
        WHERE active = true AND lower(translate_tag) LIKE '%{tag}%'
    """
    return _execute_fetch_query(query)


@app.get('/phrase-pl/fetch-count')
def read_target_count(count: int = 3):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrase_pl
        WHERE active = true
        ORDER BY RANDOM() LIMIT {count}
    """
    return _execute_fetch_query(query)


def _execute_fetch_query(query):
    conn = sqlite3.connect(FRAPPER_DB)
    cur = conn.cursor()
    cur.execute(query)

    res = cur.fetchall()
    conn.close()
    return {'messages': res}
