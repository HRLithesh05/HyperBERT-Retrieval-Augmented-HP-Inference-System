from typing import Iterable

from pymongo import MongoClient, UpdateOne
from pymongo.errors import OperationFailure


class MongoStore:
    def __init__(self, config: dict) -> None:
        self.client = MongoClient(config["uri"])
        self.db = self.client[config["db"]]
        self.collection = self.db[config["collection"]]
        self.clean_collection_name = config.get("clean_collection", "papers_clean")

    def ensure_indexes(self, config: dict) -> None:
        self.collection.create_index([("source", 1), ("source_id", 1)], unique=True)
        self.collection.create_index("title_norm")
        self.collection.create_index("year")
        self.collection.create_index("tags.is_candidate")
        self.collection.create_index("tags.domain_suitable")
        self.collection.create_index("dedup.is_duplicate")

        clean_names = self._clean_collections_from_config(config)
        for name in clean_names:
            clean = self.db[name]
            clean.create_index([("source", 1), ("source_id", 1)], unique=True)
            clean.create_index("tags.domain_suitable")
            clean.create_index("dedup.is_duplicate")

    def ensure_schema(self, config: dict) -> None:
        validation_cfg = config.get("validation", {})
        raw_action = validation_cfg.get("raw_action", "warn")
        clean_action = validation_cfg.get("clean_action", "error")
        level = validation_cfg.get("level", "moderate")

        raw_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["source", "source_id", "title"],
                "properties": {
                    "source": {"bsonType": "string"},
                    "source_id": {"bsonType": "string"},
                    "title": {"bsonType": "string"},
                    "year": {"bsonType": ["int", "null"]},
                },
            }
        }

        clean_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "source",
                    "source_id",
                    "title",
                    "pdf_path",
                    "raw_text_path",
                    "tags",
                    "qc",
                ],
                "properties": {
                    "source": {"bsonType": "string"},
                    "source_id": {"bsonType": "string"},
                    "title": {"bsonType": "string"},
                    "pdf_path": {"bsonType": "string"},
                    "raw_text_path": {"bsonType": "string"},
                    "tags": {
                        "bsonType": "object",
                        "required": ["domain_suitable"],
                        "properties": {"domain_suitable": {"bsonType": "bool"}},
                    },
                    "qc": {
                        "bsonType": "object",
                        "required": ["passed", "checked_at"],
                        "properties": {
                            "passed": {"bsonType": "bool"},
                            "checked_at": {"bsonType": "string"},
                        },
                    },
                },
            }
        }

        self._apply_validator(self.collection.name, raw_validator, raw_action, level)

        for name in self._clean_collections_from_config(config):
            self._apply_validator(name, clean_validator, clean_action, level)

    def _apply_validator(self, name: str, validator: dict, action: str, level: str) -> None:
        try:
            self.db.command(
                "collMod",
                name,
                validator=validator,
                validationAction=action,
                validationLevel=level,
            )
        except OperationFailure as exc:
            if exc.code == 26:
                self.db.create_collection(
                    name,
                    validator=validator,
                    validationAction=action,
                    validationLevel=level,
                )
            else:
                raise

    def upsert_many(self, records: Iterable[dict]) -> None:
        ops = []
        for record in records:
            ops.append(
                UpdateOne(
                    {"source": record["source"], "source_id": record["source_id"]},
                    {"$set": record},
                    upsert=True,
                )
            )
        if ops:
            self.collection.bulk_write(ops, ordered=False)

    def iter_missing_pdfs(self) -> Iterable[dict]:
        return self.collection.find({"pdf_path": {"$exists": False}, "pdf_url": {"$ne": None}})

    def iter_with_pdfs(self) -> Iterable[dict]:
        return self.collection.find({"pdf_path": {"$exists": True}})

    def update_pdf_info(self, record_id, info: dict) -> None:
        self.collection.update_one({"_id": record_id}, {"$set": info})

    def update_text_info(self, record_id, info: dict) -> None:
        self.collection.update_one({"_id": record_id}, {"$set": info})

    def get_collection(self, name: str):
        return self.db[name]

    def _clean_collections_from_config(self, config: dict) -> list[str]:
        mongo_cfg = config.get("mongodb", {})
        clean_list = mongo_cfg.get("clean_collections") or []
        if not clean_list:
            clean_list = [mongo_cfg.get("clean_collection", self.clean_collection_name)]
        return clean_list
