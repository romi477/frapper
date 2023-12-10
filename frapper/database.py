# python3

import sqlite3
from settings import FRAPPER_DB


def create_db_tables():
    conn = sqlite3.connect(FRAPPER_DB)
    cur = conn.cursor()

    query_phrase_meta = """
        CREATE TABLE phrase_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state CHAR,
            channel_id CHAR,
            message_id INTEGER,
            message_date DATETIME,
            with_error BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(channel_id, message_id)
        )
    """
    query_phrase_pl = """
        CREATE TABLE phrase_pl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER,
            state CHAR,
            active BOOLEAN,
            target CHAR,
            target_tag CHAR,
            translate CHAR,
            translate_tag CHAR,
            target_mask CHAR,
            translate_mask CHAR,
            message_id INTEGER,
            message_date DATETIME,
            metadata CHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(target, target_tag),
            FOREIGN KEY (meta_id) REFERENCES phrase_meta(id)
        )
    """

    cur.execute(query_phrase_meta)
    cur.execute(query_phrase_pl)
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_db_tables()
