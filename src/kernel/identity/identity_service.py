"""
Identity service for user management operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.kernel.models.user import User, UserRole, RefreshToken
from src.kernel.models.event_log import EventType
from src.kernel.events.event_store import EventStore
from src.kernel.identity.password import hash_password, verify_password
from src.kernel.identity.jwt import JWTManager, TokenPair


class IdentityService:
    """
    Service for user identity operations.
    
    Handles user registration, authentication, and token management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.jwt_manager = JWTManager()
        self.event_store = EventStore(session)
    
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.STUDENT,
        ip_address: Optional[str] = None,
    ) -> User:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            full_name: User's full name
            role: User role (default: student)
            ip_address: Client IP for audit
            
        Returns:
            The created User object
            
        Raises:
            ValueError: If email already exists
        """
        # Check for existing user
        existing = await self.get_user_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=role,
        )
        
        self.session.add(user)
        await self.session.flush()  # Get the ID
        
        # Log the event
        await self.event_store.log(
            event_type=EventType.USER_REGISTERED,
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            payload={"email": user.email, "role": user.role.value if hasattr(user.role, "value") else user.role},
            ip_address=ip_address,
        )
        
        return user
    
    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[tuple[User, TokenPair]]:
        """
        Authenticate a user and return tokens.
        
        Args:
            email: User's email
            password: Plain text password
            ip_address: Client IP for audit
            user_agent: Client user agent for audit
            
        Returns:
            Tuple of (User, TokenPair) if successful, None otherwise
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        # Create tokens (role may be enum or str when loaded from SQLite)
        role_value = user.role.value if hasattr(user.role, "value") else user.role
        token_pair, access_jti, refresh_jti = self.jwt_manager.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=role_value,
        )
        
        # Store refresh token
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=JWTManager.hash_token(token_pair.refresh_token),
            expires_at=datetime.now(timezone.utc) + 
                       __import__('datetime').timedelta(days=self.jwt_manager.refresh_token_expire_days),
        )
        self.session.add(refresh_token_record)
        
        # Log the event
        await self.event_store.log(
            event_type=EventType.USER_LOGGED_IN,
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            payload={"method": "password"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return user, token_pair
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
    ) -> Optional[tuple[User, TokenPair]]:
        """
        Refresh tokens using a refresh token.
        
        Implements refresh token rotation for security.
        
        Args:
            refresh_token: The refresh token
            ip_address: Client IP for audit
            
        Returns:
            Tuple of (User, new TokenPair) if successful, None otherwise
        """
        # Verify the refresh token
        payload = self.jwt_manager.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        # Check if token is in database and not revoked
        token_hash = JWTManager.hash_token(refresh_token)
        query = select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(query)
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            return None
        
        # Get user
        user = await self.get_user_by_id(uuid.UUID(payload.sub))
        if not user or not user.is_active:
            return None
        
        # Revoke old refresh token (rotation)
        token_record.revoked = True
        
        # Create new token pair
        role_val = user.role.value if hasattr(user.role, "value") else user.role
        new_token_pair, access_jti, refresh_jti = self.jwt_manager.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=role_val,
        )
        
        # Store new refresh token
        new_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=JWTManager.hash_token(new_token_pair.refresh_token),
            expires_at=datetime.now(timezone.utc) + 
                       __import__('datetime').timedelta(days=self.jwt_manager.refresh_token_expire_days),
        )
        self.session.add(new_refresh_token)
        
        return user, new_token_pair
    
    async def logout(
        self,
        user_id: uuid.UUID,
        refresh_token: Optional[str] = None,
        revoke_all: bool = False,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Log out a user by revoking refresh tokens.
        
        Args:
            user_id: The user's ID
            refresh_token: Specific token to revoke (if not revoking all)
            revoke_all: Whether to revoke all user's tokens
            ip_address: Client IP for audit
            
        Returns:
            True if successful
        """
        if revoke_all:
            # Revoke all user's refresh tokens
            query = select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,
                )
            )
            result = await self.session.execute(query)
            tokens = result.scalars().all()
            
            for token in tokens:
                token.revoked = True
        elif refresh_token:
            # Revoke specific token
            token_hash = JWTManager.hash_token(refresh_token)
            query = select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
            result = await self.session.execute(query)
            token_record = result.scalar_one_or_none()
            
            if token_record:
                token_record.revoked = True
        
        # Log the event
        await self.event_store.log(
            event_type=EventType.USER_LOGGED_OUT,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            payload={"revoke_all": revoke_all},
            ip_address=ip_address,
        )
        
        return True
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get a user by ID."""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        query = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_user(
        self,
        user_id: uuid.UUID,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[User]:
        """
        Update user profile.
        
        Args:
            user_id: The user's ID
            full_name: New full name (optional)
            email: New email (optional)
            ip_address: Client IP for audit
            
        Returns:
            Updated user or None if not found
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        changes = {}
        
        if full_name is not None:
            user.full_name = full_name.strip()
            changes["full_name"] = full_name
        
        if email is not None:
            new_email = email.lower().strip()
            # Check if email is taken
            existing = await self.get_user_by_email(new_email)
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            user.email = new_email
            changes["email"] = new_email
        
        if changes:
            await self.event_store.log(
                event_type=EventType.USER_UPDATED,
                entity_type="user",
                entity_id=user_id,
                user_id=user_id,
                payload=changes,
                ip_address=ip_address,
            )
        
        return user
    
    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Change user's password.
        
        Args:
            user_id: The user's ID
            current_password: Current password for verification
            new_password: New password
            ip_address: Client IP for audit
            
        Returns:
            True if successful, False if current password is wrong
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = hash_password(new_password)
        
        # Revoke all refresh tokens on password change
        await self.logout(user_id, revoke_all=True, ip_address=ip_address)
        
        return True
    
    async def verify_email(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Mark a user's email as verified."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.verified_at = datetime.now(timezone.utc)
        return True
    
    async def change_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        changed_by: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Change a user's role (admin only).
        
        Args:
            user_id: The user's ID
            new_role: New role
            changed_by: Admin user making the change
            ip_address: Client IP for audit
            
        Returns:
            True if successful
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        old_role = user.role
        user.role = new_role
        
        await self.event_store.log(
            event_type=EventType.USER_ROLE_CHANGED,
            entity_type="user",
            entity_id=user_id,
            user_id=changed_by,
            payload={
                "previous_role": old_role.value,
                "new_role": new_role.value,
            },
            ip_address=ip_address,
        )
        
        return True
