import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def execute_query(query, params=None, fetch=False, many=False):
    query = query.replace("AUTO_INCREMENT", "").replace("auto_increment", "")
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if many:
            cur.executemany(query, params)
        else:
            cur.execute(query, params or ())
        if fetch:
            result = [dict(r) for r in cur.fetchall()]
        else:
            conn.commit()
            row = cur.fetchone()
            result = list(row.values())[0] if row else cur.rowcount
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def execute_transaction(queries_and_params):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    results = []
    try:
        for query, params in queries_and_params:
            cur.execute(query, params or ())
            row = cur.fetchone()
            results.append(list(row.values())[0] if row else cur.rowcount)
        conn.commit()
        return results
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
