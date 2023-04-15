import sqlite3
from fastapi import FastAPI

# from database.db import conn

app = FastAPI()


@app.get('/target/{tag}')
def read_target_tag(tag: str):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrases
        WHERE lower(target_tag) LIKE '%{tag}%'
    """
    return _execute_query(query)


@app.get('/target_translate/{tag}')
def read_target_mess(tag: str):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrases
        WHERE lower(translate_tag) LIKE '%{tag}%'
    """
    return _execute_query(query)


@app.get('/target_count/{count}')
def read_target_count(count: int):
    query = f"""
        SELECT id, message_id, target, target_mask, translate, translate_mask
        FROM phrases
        ORDER BY RANDOM() LIMIT {count}
    """
    return _execute_query(query)


def _execute_query(query):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute(query)

    res = cur.fetchall()
    conn.close()
    return {'messages': res}
