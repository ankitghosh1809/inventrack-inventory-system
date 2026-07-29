import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it in Vercel → Settings → Environment Variables."
        )
    return psycopg2.connect(DATABASE_URL)

def execute_query(query, params=None, fetch=False, many=False):
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
            # Unlike MySQL (cursor.lastrowid), a plain INSERT/UPDATE/DELETE
            # in Postgres has no result set at all -- cur.fetchone() would
            # raise "no results to fetch". Only fetch when the query actually
            # produced rows (e.g. it has a RETURNING clause).
            if cur.description:
                row = cur.fetchone()
                result = list(row.values())[0] if row else cur.rowcount
            else:
                result = cur.rowcount
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
            if cur.description:
                row = cur.fetchone()
                results.append(list(row.values())[0] if row else cur.rowcount)
            else:
                results.append(cur.rowcount)
        conn.commit()
        return results
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
