__all__ = [
    "File",
]

import dataclasses
import json
import os
import sqlite3
from typing import Union, Optional, Any


@dataclasses.dataclass
class File:
    DB_PATH = "rsc/faces.db"

    image_id: int
    input_hash: str
    processed: bool = False
    failed: bool = False
    meta: Optional[str] = None

    @property
    def result_url(self):
        return f"output/{self.image_id}"

    def save(self):
        con = self._create_connection()
        cur = con.cursor()

        cur.execute(
            """
            INSERT OR REPLACE INTO files
              VALUES(?, ?, ?, ?, ?)
            """,
            (
                self.image_id,
                self.input_hash,
                int(self.processed),
                int(self.failed),
                self.meta,
            )
        )

        return con.commit()

    def delete(self):
        con = self._create_connection()
        cur = con.cursor()

        cur.execute(
            """
            DELETE FROM faces
            WHERE id = ?
            """,
            (
                self.image_id,
            )
        )

        return con.commit()

    def refresh(self):
        file = self.find_file_by_id(self.image_id)

        self.input_hash = file.input_hash
        self.processed = file.processed
        self.failed = file.failed
        self.meta = file.meta

    def get_faces_found(self) -> Union[int, None]:
        faces = None
        meta = json.loads(self.meta)
        if isinstance(meta, dict):
            faces = meta.get("faces", 0)

        return faces

    @classmethod
    def find_file_by_id(cls, image_id: int) -> Union["File", None]:
        return cls._find_by("id", image_id)

    @classmethod
    def find_file_by_hash(cls, input_hash: str) -> Union[None, "File"]:
        return cls._find_by("input_hash", input_hash)

    @classmethod
    def _find_by(cls, field: str, value: Any) -> Union[None, "File"]:
        con = cls._create_connection()
        cur = con.cursor()

        cur.execute(f"""
                SELECT
                    *
                FROM files
                WHERE {field} = ?
            """, (
            value,
        ))

        file = cur.fetchone()
        if file is None:
            return None

        return cls(*file)

    @classmethod
    def _create_connection(cls):
       return sqlite3.connect(cls.DB_PATH)

    @classmethod
    def _init_db(cls):
        db_dir = os.path.dirname(cls.DB_PATH)
        if not os.path.isdir(db_dir):
            os.makedirs(db_dir, mode=0o775, exist_ok=True)

            print("CREATED!")

        con = cls._create_connection()
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS 
            files (
                id INTEGER PRIMARY KEY,
                input_hash VARCHAR(64) UNIQUE NOT NULL,
                processed BOOLEAN NOT NULL DEFAULT 0,
                failed BOOLEAN NOT NULL DEFAULT 0,
                meta TEXT
        )""")

        con.commit()


File._init_db()  # pylint: disable
