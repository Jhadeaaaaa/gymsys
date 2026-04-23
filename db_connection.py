import os
import re
from datetime import date, datetime, timedelta

import mysql.connector


def _int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _str_env(name, default=None):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


MYSQL_CONFIG = {
    "host": _str_env("MYSQL_HOST", "127.0.0.1"),
    "port": _int_env("MYSQL_PORT", 3306),
    "user": _str_env("MYSQL_USER", "root"),
    "password": _str_env("MYSQL_PASSWORD", "root"),
    "database": _str_env("MYSQL_DATABASE", "gymsys"),
}


class MySQLCompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @staticmethod
    def _normalize_sql(query):
        sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT IGNORE INTO", query, flags=re.IGNORECASE)
        return sql.replace("?", "%s")

    @staticmethod
    def _time_delta_to_hhmmss(delta_value):
        total_seconds = int(delta_value.total_seconds())
        if total_seconds < 0:
            total_seconds = 0
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def _normalize_value(cls, value):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, timedelta):
            return cls._time_delta_to_hhmmss(value)
        return value

    @classmethod
    def _normalize_row(cls, row):
        if row is None:
            return None
        return tuple(cls._normalize_value(v) for v in row)

    def execute(self, query, params=None):
        sql = self._normalize_sql(query)
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        return self

    def fetchone(self):
        return self._normalize_row(self._cursor.fetchone())

    def fetchall(self):
        return [self._normalize_row(row) for row in self._cursor.fetchall()]

    def close(self):
        self._cursor.close()


class MySQLCompatConnection:
    def __init__(self, **config):
        self._raw = mysql.connector.connect(**config)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False

    def cursor(self):
        return MySQLCompatCursor(self._raw.cursor())

    def execute(self, query, params=None):
        cur = self.cursor()
        return cur.execute(query, params)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def connect(_unused_path=None):
    return MySQLCompatConnection(**MYSQL_CONFIG)


IntegrityError = mysql.connector.IntegrityError
Error = mysql.connector.Error
