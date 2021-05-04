import sqlite3
import os
from pathlib import Path
from functions.general import _human_bytes
from random import randint
import json


class LayerHandling:
    def __init__(self, logger, dir):
        self.logger = logger
        self.mainPath = dir
        self.buildPath = os.path.join(self.mainPath, "build")
        Path(self.buildPath).mkdir(exist_ok=True)

        self.buildDb = os.path.join(self.buildPath, "layers.db")
        self.dumpDb = os.path.join(self.mainPath, "dump.db")

    """
    Dump database
    """

    def clear_dump_db(self):
        if os.path.isfile(self.dumpDb):
            self.logger.warning("dump.db already exists")
            os.remove(self.dumpDb)
        self.logger.debug("Cleared dump database")

    def establish_dump_db(self):
        self.dumpConn = sqlite3.connect(self.dumpDb)
        self.dumpCurs = self.dumpConn.cursor()
        self.logger.debug("Setup dump database")

    def setup_dump_table(self, normalize):
        # Unsafe but safety is not necesssary
        scoreType = "REAL" if normalize["normalize"] else "INTEGER"
        query = f"""CREATE TABLE data (
            id INTEGER PRIMARY KEY,
            comment TEXT,
            score {scoreType}
        )
        """
        self.dumpCurs.execute(query)
        self.dumpConn.commit()
        self.logger.debug(f"Setup dump table {'(normalized)' if normalize else ''}")

    def dump_data(self, comments):
        self.logger.debug(f"Inserting {len(comments)} comments into dump.db..")
        data = tuple(
            [(randint(1, 9999999999), i["comment"], i["score"]) for i in comments]
        )

        chunkID = 0
        for chunk in self.__get_chunks(data, 5):
            chunkID += 1
            self.logger.debug(f"Inserting chunk {chunkID}: {len(chunk)}")
            self.logger.debug(json.dumps(chunk, indent=2))
            self.dumpCurs.executemany(
                "INSERT OR IGNORE INTO data (id, comment, score) VALUES (?, ?, ?)",
                chunk,
            )
            self.logger.debug(
                f"Inserted chunk {chunkID}: {len(chunk) * chunkID}/{len(data)}"
            )
            self.dumpConn.commit()
            self.logger.debug(f"Committed to database")
        self.logger.debug(f"Inserted {len(comments)} rows into dump.db")

    def __get_chunks(self, data, n):
        for i in range(0, len(data), n):
            yield data[i : i + n]

    def __get_dump(self):
        self.dumpCurs.execute("SELECT * FROM data")
        return self.dumpCurs.fetchall()

    def __get_json_dump(self):
        data = self.__get_dump()
        return [
            {
                "comment": i[1],
                "score": i[2],
            }
            for i in data
        ]

    def json_dump(self):
        data = self.__get_json_dump()
        json.dump(
            data,
            open(os.path.join(self.mainPath, "dump.json"), "w"),
            indent=2,
        )

    """
    Build database
    """

    def clear_build_db(self):
        if os.path.isfile(self.buildDb):
            os.remove(self.buildDb)
        self.logger.debug("Cleared build database")

    def establish_build_db(self):
        self.buildConn = sqlite3.connect(self.buildDb)
        self.buildCurs = self.buildConn.cursor()
        self.logger.debug("Setup build database")

    def setup_build_layer(self, layer):
        # Unsafe but safety is not necesssary
        tableName = f"layer{layer}"
        self.buildCurs.execute(
            f"""CREATE TABLE {tableName} (
                id TEXT,
                username TEXT
            )
            """
        )
        self.buildConn.commit()
        self.logger.debug(f"Setup build layer {layer} -- {tableName}")

    def dump_build_layer(self, layer, users):
        tableName = f"layer{layer}"
        self.logger.debug(f"Inserting {len(users)} rows into {tableName}")
        usernames = [("", i.name) for i in users if i is not None]
        self.buildCurs.executemany(
            f"INSERT INTO {tableName} (id, username) VALUES (?, ?)",
            usernames,
        )
        self.buildConn.commit()
        self.logger.debug(f"Dumped {len(usernames)} usernames to {tableName}")

    def read_build_layer(self, layer):
        tableName = f"layer{layer}"
        self.buildCurs.execute(f"SELECT username FROM {tableName}")
        data = [i[0] for i in self.buildCurs.fetchall()]
        self.logger.debug(f"Fetched {len(data)} usernames from {tableName}")
        return data

    def get_size(self):
        return _human_bytes(os.path.getsize(os.path.join(self.mainPath, "data.db")))
