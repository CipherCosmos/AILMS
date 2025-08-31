"""
Unit tests for utils module.
"""
import pytest
from utils import serialize_mongo_doc
from bson import ObjectId
from datetime import datetime


class TestSerializeMongoDoc:
    """Test MongoDB document serialization functionality."""

    def test_serialize_simple_dict(self):
        """Test serialization of simple dictionary."""
        doc = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }

        result = serialize_mongo_doc(doc)
        assert result == doc

    def test_serialize_with_object_id(self):
        """Test serialization of document with ObjectId."""
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Test Document",
            "value": 42
        }

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["name"] == "Test Document"
        assert result["value"] == 42

    def test_serialize_nested_dict(self):
        """Test serialization of nested dictionary."""
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "user": {
                "name": "John Doe",
                "profile": {
                    "_id": ObjectId("507f1f77bcf86cd799439012"),
                    "bio": "Software developer"
                }
            },
            "metadata": {
                "created_at": datetime(2023, 1, 1, 12, 0, 0),
                "tags": ["test", "nested"]
            }
        }

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["user"]["name"] == "John Doe"
        assert result["user"]["profile"]["_id"] == "507f1f77bcf86cd799439012"
        assert result["user"]["profile"]["bio"] == "Software developer"
        assert result["metadata"]["created_at"] == datetime(2023, 1, 1, 12, 0, 0)
        assert result["metadata"]["tags"] == ["test", "nested"]

    def test_serialize_list(self):
        """Test serialization of list containing documents."""
        doc = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Document 1"
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "name": "Document 2"
            }
        ]

        result = serialize_mongo_doc(doc)
        assert len(result) == 2
        assert result[0]["_id"] == "507f1f77bcf86cd799439011"
        assert result[0]["name"] == "Document 1"
        assert result[1]["_id"] == "507f1f77bcf86cd799439012"
        assert result[1]["name"] == "Document 2"

    def test_serialize_mixed_list(self):
        """Test serialization of list with mixed data types."""
        doc = [
            ObjectId("507f1f77bcf86cd799439011"),
            "string_value",
            42,
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "nested": True
            }
        ]

        result = serialize_mongo_doc(doc)
        assert result[0] == "507f1f77bcf86cd799439011"
        assert result[1] == "string_value"
        assert result[2] == 42
        assert result[3]["_id"] == "507f1f77bcf86cd799439012"
        assert result[3]["nested"] is True

    def test_serialize_none_value(self):
        """Test serialization when input is None."""
        result = serialize_mongo_doc(None)
        assert result is None

    def test_serialize_empty_dict(self):
        """Test serialization of empty dictionary."""
        doc = {}
        result = serialize_mongo_doc(doc)
        assert result == {}

    def test_serialize_empty_list(self):
        """Test serialization of empty list."""
        doc = []
        result = serialize_mongo_doc(doc)
        assert result == []

    def test_serialize_complex_nested_structure(self):
        """Test serialization of complex nested structure."""
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "courses": [
                {
                    "_id": ObjectId("507f1f77bcf86cd799439012"),
                    "title": "Course 1",
                    "lessons": [
                        {
                            "_id": ObjectId("507f1f77bcf86cd799439013"),
                            "title": "Lesson 1"
                        },
                        {
                            "_id": ObjectId("507f1f77bcf86cd799439014"),
                            "title": "Lesson 2"
                        }
                    ]
                }
            ],
            "metadata": {
                "created_by": ObjectId("507f1f77bcf86cd799439015"),
                "stats": {
                    "total_lessons": 2,
                    "difficulty": "intermediate"
                }
            }
        }

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert len(result["courses"]) == 1
        assert result["courses"][0]["_id"] == "507f1f77bcf86cd799439012"
        assert result["courses"][0]["title"] == "Course 1"
        assert len(result["courses"][0]["lessons"]) == 2
        assert result["courses"][0]["lessons"][0]["_id"] == "507f1f77bcf86cd799439013"
        assert result["courses"][0]["lessons"][1]["title"] == "Lesson 2"
        assert result["metadata"]["created_by"] == "507f1f77bcf86cd799439015"
        assert result["metadata"]["stats"]["total_lessons"] == 2

    def test_serialize_preserves_non_object_id_values(self):
        """Test that non-ObjectId values are preserved."""
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "string_field": "test_string",
            "int_field": 123,
            "float_field": 45.67,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"key": "value"},
            "datetime_field": datetime(2023, 1, 1, 12, 0, 0)
        }

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["string_field"] == "test_string"
        assert result["int_field"] == 123
        assert result["float_field"] == 45.67
        assert result["bool_field"] is True
        assert result["list_field"] == [1, 2, 3]
        assert result["dict_field"] == {"key": "value"}
        assert result["datetime_field"] == datetime(2023, 1, 1, 12, 0, 0)

    def test_serialize_handles_duplicate_keys(self):
        """Test serialization handles duplicate keys appropriately."""
        # This tests that the function doesn't crash on edge cases
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Test",
            "name": "Override"  # This would be the last value in Python dict
        }

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["name"] == "Override"  # Last value wins

    def test_serialize_large_document(self):
        """Test serialization of a large document with many ObjectIds."""
        # Create a document with many ObjectId fields
        doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "users": []
        }

        # Add many users with ObjectIds
        for i in range(100):
            doc["users"].append({
                "_id": ObjectId(f"507f1f77bcf86cd79943{i:04d}"),
                "name": f"User {i}",
                "email": f"user{i}@example.com"
            })

        result = serialize_mongo_doc(doc)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert len(result["users"]) == 100

        for i in range(100):
            assert result["users"][i]["_id"] == f"507f1f77bcf86cd79943{i:04d}"
            assert result["users"][i]["name"] == f"User {i}"
            assert result["users"][i]["email"] == f"user{i}@example.com"