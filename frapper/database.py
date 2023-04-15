import sqlite3


def create_phrases_table():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    query = """
        CREATE TABLE phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            state CHAR,
            status BOOLEAN,
            target CHAR,
            target_tag CHAR,
            translate CHAR,
            translate_tag CHAR,
            target_mask CHAR,
            translate_mask CHAR,
            metadata CHAR,
            width INTEGER,
            height INTEGER,
            file_name CHAR,
            file_index INTEGER,
            file_date DATETIME,
            bin_data BLOB
        )
    """
    cur.execute(query)
    conn.commit()
    conn.close()


create_phrases_table()

# conn = sqlite3.connect('database.db')
