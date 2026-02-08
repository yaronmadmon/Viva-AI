"""
Password hashing utilities using bcrypt.
"""

import bcrypt

# Number of rounds for bcrypt hashing (12 is secure default)
BCRYPT_ROUNDS = 12


class PasswordHasher:
    """Password hashing service."""
    
    @staticmethod
    def _truncate_password(password: str) -> bytes:
        """
        Truncate password to 72 bytes (bcrypt limit) and encode.
        
        bcrypt only uses the first 72 bytes of a password.
        This method ensures we don't exceed that limit.
        """
        return password.encode('utf-8')[:72]
    
    @staticmethod
    def hash(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        # Truncate to 72 bytes (bcrypt limit) and encode
        pwd_bytes = PasswordHasher._truncate_password(password)
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Truncate to 72 bytes (bcrypt limit) for consistency
            pwd_bytes = PasswordHasher._truncate_password(plain_password)
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        except Exception:
            return False
    
    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """
        Check if a password hash needs to be upgraded.
        
        Currently checks if the hash uses a different number of rounds.
        
        Args:
            hashed_password: Existing password hash
            
        Returns:
            True if hash should be regenerated
        """
        try:
            # bcrypt hashes encode the rounds in positions 4-6
            # Format: $2b$XX$... where XX is the rounds
            parts = hashed_password.split('$')
            if len(parts) >= 3:
                current_rounds = int(parts[2])
                return current_rounds != BCRYPT_ROUNDS
            return True
        except Exception:
            return True


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password."""
    return PasswordHasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password."""
    return PasswordHasher.verify(plain_password, hashed_password)
