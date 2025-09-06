import mysql.connector
from mysql.connector import Error, pooling
from config import Config


# Using a connection pool so we don't open a new connection per request.
# Pool size of 5 is reasonable for a small to mid-sized deployment.
_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="inventory_pool",
            pool_size=5,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            autocommit=False,
        )
    return _pool


def get_connection():
    """Return a connection from the pool. Caller is responsible for closing it."""
    try:
        return get_pool().get_connection()
    except Error as e:
        raise ConnectionError(f"Could not connect to MySQL: {e}")


def execute_query(query, params=None, fetch=False, many=False):
    """
    Thin wrapper around mysql-connector for DRY usage across the app.

    Args:
        query  : SQL string with %s placeholders
        params : tuple or list of tuples (for many=True)
        fetch  : if True, return fetched rows; if False, return lastrowid
        many   : use executemany (for bulk inserts)

    Returns:
        list of dicts (fetch=True) or lastrowid/rowcount (fetch=False)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params or ())

        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount

        return result
    except Error as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_transaction(queries_and_params):
    """
    Execute multiple queries as a single transaction.
    queries_and_params: list of (query, params) tuples
    Returns list of lastrowids.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    results = []
    try:
        for query, params in queries_and_params:
            cursor.execute(query, params or ())
            results.append(cursor.lastrowid)
        conn.commit()
        return results
    except Error as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
