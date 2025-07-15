# Database Migrations

This directory contains SQL migration files for the RPO Automation system.

## Running Migrations

To apply migrations to your Supabase database:

1. Go to your Supabase Dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of each migration file in order
4. Execute the SQL

## Migration Files

- `001_initial_schema.sql` - Initial database schema
- `002_add_jobs_fields.sql` - Adds fields needed for AI matching jobs

## Important Notes

- Always backup your database before running migrations
- Run migrations in numerical order
- Each migration is designed to be idempotent (safe to run multiple times)