"""Unit tests for password hashing."""

import pytest

from src.kernel.identity.password import (
    PasswordHasher,
    hash_password,
    verify_password,
)


class TestPasswordHasher:
    """Tests for PasswordHasher."""
    
    def test_hash_creates_different_hashes(self):
        """Same password should create different hashes (due to salt)."""
        password = "TestPassword123"
        hash1 = PasswordHasher.hash(password)
        hash2 = PasswordHasher.hash(password)
        
        assert hash1 != hash2
        assert hash1.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_correct_password(self):
        """Correct password should verify successfully."""
        password = "TestPassword123"
        hashed = PasswordHasher.hash(password)
        
        assert PasswordHasher.verify(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Wrong password should fail verification."""
        password = "TestPassword123"
        hashed = PasswordHasher.hash(password)
        
        assert PasswordHasher.verify("WrongPassword", hashed) is False
    
    def test_convenience_functions(self):
        """Test hash_password and verify_password functions."""
        password = "TestPassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
