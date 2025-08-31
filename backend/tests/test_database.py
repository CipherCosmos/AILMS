"""
Unit tests for database module.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from database import _insert_one, _update_one, _find_one, _require, get_database, init_database
from fastapi import HTTPException


class TestDatabaseInitialization:
    """Test database initialization functionality."""

    @pytest.mark.asyncio
    async def test_get_database_initializes_when_none(self):
        """Test that get_database initializes database when it's None."""
        with patch('database.db', None), \
             patch('database.init_database') as mock_init:

            mock_init.return_value = (MagicMock(), MagicMock())
            result = get_database()

            mock_init.assert_called_once()
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_database_returns_existing_db(self):
        """Test that get_database returns existing database instance."""
        with patch('database.db', MagicMock()), \
             patch('database.init_database') as mock_init:

            result = get_database()

            # init_database should not be called when db already exists
            mock_init.assert_not_called()
            assert result is not None

    @pytest.mark.asyncio
    async def test_init_database_success(self):
        """Test successful database initialization."""
        with patch('database.client', None), \
             patch('database.AsyncIOMotorClient') as mock_client_class, \
             patch('database.AsyncIOMotorGridFSBucket') as mock_fs_class:

            mock_client = MagicMock()
            mock_db = MagicMock()
            mock_fs = MagicMock()

            mock_client_class.return_value = mock_client
            mock_client.__getitem__.return_value = mock_db
            mock_fs_class.return_value = mock_fs

            db, fs = init_database()

            assert db == mock_db
            assert fs == mock_fs
            mock_client_class.assert_called_once()
            mock_fs_class.assert_called_once_with(mock_db)


class TestDatabaseOperations:
    """Test database CRUD operations."""

    @pytest.mark.asyncio
    async def test_insert_one_success(self):
        """Test successful document insertion."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch('database.get_database', return_value=mock_db), \
             patch('database._uuid', return_value='test_uuid'):

            await _insert_one('users', {'name': 'Test User'})

            # Verify _id was added
            call_args = mock_collection.insert_one.call_args[0][0]
            assert call_args['_id'] == 'test_uuid'
            assert call_args['name'] == 'Test User'

    @pytest.mark.asyncio
    async def test_insert_one_with_existing_id(self):
        """Test insertion when document already has _id."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch('database.get_database', return_value=mock_db):
            doc_with_id = {'_id': 'existing_id', 'name': 'Test User'}
            await _insert_one('users', doc_with_id)

            # Verify existing _id was preserved
            call_args = mock_collection.insert_one.call_args[0][0]
            assert call_args['_id'] == 'existing_id'
            assert call_args['name'] == 'Test User'

    @pytest.mark.asyncio
    async def test_update_one_success(self):
        """Test successful document update."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        with patch('database.get_database', return_value=mock_db):
            await _update_one('users', {'_id': 'user_123'}, {'name': 'Updated Name'})

            mock_collection.update_one.assert_called_once_with(
                {'_id': 'user_123'},
                {'$set': {'name': 'Updated Name'}}
            )

    @pytest.mark.asyncio
    async def test_find_one_success(self):
        """Test successful document retrieval."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        expected_doc = {'_id': 'user_123', 'name': 'Test User'}
        mock_collection.find_one.return_value = expected_doc

        with patch('database.get_database', return_value=mock_db):
            result = await _find_one('users', {'_id': 'user_123'})

            assert result == expected_doc
            mock_collection.find_one.assert_called_once_with({'_id': 'user_123'})

    @pytest.mark.asyncio
    async def test_find_one_not_found(self):
        """Test document retrieval when document doesn't exist."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.find_one.return_value = None

        with patch('database.get_database', return_value=mock_db):
            result = await _find_one('users', {'_id': 'nonexistent'})

            assert result is None
            mock_collection.find_one.assert_called_once_with({'_id': 'nonexistent'})

    @pytest.mark.asyncio
    async def test_require_success(self):
        """Test successful document requirement."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        expected_doc = {'_id': 'user_123', 'name': 'Test User'}
        mock_collection.find_one.return_value = expected_doc

        with patch('database.get_database', return_value=mock_db):
            result = await _require('users', {'_id': 'user_123'}, 'User not found')

            assert result == expected_doc
            mock_collection.find_one.assert_called_once_with({'_id': 'user_123'})

    @pytest.mark.asyncio
    async def test_require_not_found(self):
        """Test document requirement when document doesn't exist."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.find_one.return_value = None

        with patch('database.get_database', return_value=mock_db):
            with pytest.raises(HTTPException) as exc_info:
                await _require('users', {'_id': 'nonexistent'}, 'User not found')

            assert exc_info.value.status_code == 404
            assert 'User not found' in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_custom_error_message(self):
        """Test document requirement with custom error message."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.find_one.return_value = None

        with patch('database.get_database', return_value=mock_db):
            with pytest.raises(HTTPException) as exc_info:
                await _require('courses', {'_id': 'course_123'}, 'Course not found')

            assert exc_info.value.status_code == 404
            assert 'Course not found' in exc_info.value.detail


class TestDatabaseErrorHandling:
    """Test error handling in database operations."""

    @pytest.mark.asyncio
    async def test_insert_one_database_error(self):
        """Test handling of database errors during insertion."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.insert_one.side_effect = Exception("Database connection failed")

        with patch('database.get_database', return_value=mock_db):
            with pytest.raises(Exception) as exc_info:
                await _insert_one('users', {'name': 'Test User'})

            assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_one_database_error(self):
        """Test handling of database errors during update."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.update_one.side_effect = Exception("Update failed")

        with patch('database.get_database', return_value=mock_db):
            with pytest.raises(Exception) as exc_info:
                await _update_one('users', {'_id': 'user_123'}, {'name': 'Updated'})

            assert "Update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_one_database_error(self):
        """Test handling of database errors during find."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.find_one.side_effect = Exception("Query failed")

        with patch('database.get_database', return_value=mock_db):
            with pytest.raises(Exception) as exc_info:
                await _find_one('users', {'_id': 'user_123'})

            assert "Query failed" in str(exc_info.value)


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.mark.asyncio
    async def test_complete_crud_cycle(self):
        """Test complete CRUD cycle with database operations."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        # Mock successful operations
        mock_collection.insert_one.return_value = MagicMock()
        mock_collection.find_one.return_value = {'_id': 'user_123', 'name': 'Test User'}
        mock_collection.update_one.return_value = MagicMock()

        with patch('database.get_database', return_value=mock_db), \
             patch('database._uuid', return_value='user_123'):

            # Create
            await _insert_one('users', {'name': 'Test User'})

            # Read
            user = await _find_one('users', {'_id': 'user_123'})
            assert user['name'] == 'Test User'

            # Update
            await _update_one('users', {'_id': 'user_123'}, {'name': 'Updated User'})

            # Verify calls
            assert mock_collection.insert_one.call_count == 1
            assert mock_collection.find_one.call_count == 1
            assert mock_collection.update_one.call_count == 1

    @pytest.mark.asyncio
    async def test_database_operations_with_different_collections(self):
        """Test database operations with different collections."""
        mock_db = MagicMock()

        # Mock different collections
        users_collection = MagicMock()
        courses_collection = MagicMock()
        assignments_collection = MagicMock()

        def get_collection(collection_name):
            collections = {
                'users': users_collection,
                'courses': courses_collection,
                'assignments': assignments_collection
            }
            return collections.get(collection_name, MagicMock())

        mock_db.__getitem__.side_effect = get_collection

        with patch('database.get_database', return_value=mock_db):
            # Test operations on different collections
            await _insert_one('users', {'name': 'User'})
            await _insert_one('courses', {'title': 'Course'})
            await _insert_one('assignments', {'title': 'Assignment'})

            # Verify each collection was accessed
            users_collection.insert_one.assert_called_once()
            courses_collection.insert_one.assert_called_once()
            assignments_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self):
        """Test concurrent database operations."""
        import asyncio

        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        async def mock_operation():
            await _find_one('users', {'_id': 'user_123'})
            return "completed"

        with patch('database.get_database', return_value=mock_db):
            # Run multiple operations concurrently
            tasks = [mock_operation() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(result == "completed" for result in results)
            assert mock_collection.find_one.call_count == 5