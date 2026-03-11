"""Supabase database connection and client."""

from supabase import create_client, Client

from app.core.config import get_settings


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client with service role key."""
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
