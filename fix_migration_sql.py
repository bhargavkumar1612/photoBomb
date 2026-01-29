
import os

MIGRATION_DIR = "backend/alembic/versions"

def process_001(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix unquoted schema
    content = content.replace(
        "op.execute(f'CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}')",
        "op.execute(f'CREATE SCHEMA IF NOT EXISTS \"{settings.DB_SCHEMA}\"')"
    )
    content = content.replace(
        "op.execute(f'DROP SCHEMA IF EXISTS {settings.DB_SCHEMA} CASCADE')",
        "op.execute(f'DROP SCHEMA IF EXISTS \"{settings.DB_SCHEMA}\" CASCADE')"
    )
    
    with open(filepath, 'w') as f:
        f.write(content)

def process_abdd(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix hardcoded photobomb. usage
    content = content.replace(
        'op.execute("DROP TABLE IF EXISTS photobomb.faces CASCADE")',
        'op.execute(f"DROP TABLE IF EXISTS \\"{settings.DB_SCHEMA}\\".faces CASCADE")'
    )
    content = content.replace(
        'op.execute("DROP TABLE IF EXISTS photobomb.people CASCADE")',
        'op.execute(f"DROP TABLE IF EXISTS \\"{settings.DB_SCHEMA}\\".people CASCADE")'
    )
    
    with open(filepath, 'w') as f:
        f.write(content)

def process_58b(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix broken f-string from previous script (op.execute("f'UPDATE..."))
    # Also add quotes for schema
    
    # Pattern: op.execute("f'UPDATE {settings.DB_SCHEMA}.photos
    # Target:  op.execute(f"UPDATE \"{settings.DB_SCHEMA}\".photos
    
    # Since specific lines might vary slightly, I'll replace the exact broken prefix
    content = content.replace(
        'op.execute("f\'UPDATE {settings.DB_SCHEMA}.photos',
        'op.execute(f"UPDATE \\"{settings.DB_SCHEMA}\\".photos'
    )
    content = content.replace(
        'op.execute("f\'UPDATE {settings.DB_SCHEMA}.photo_files',
        'op.execute(f"UPDATE \\"{settings.DB_SCHEMA}\\".photo_files'
    )
    
    # Fix the trailing part: ...'") -> ...")
    # But wait, the original string ended with '") (single quote inside double quote)
    # New string should end with ")
    
    # Let's replace the whole lines for safety
    
    # Upgrade lines
    content = content.replace(
        "op.execute(\"f'UPDATE {settings.DB_SCHEMA}.photos SET storage_provider = 's3' WHERE storage_provider = 'b2_native'\")",
        "op.execute(f\"UPDATE \\\"{settings.DB_SCHEMA}\\\".photos SET storage_provider = 's3' WHERE storage_provider = 'b2_native'\")"
    )
    content = content.replace(
        "op.execute(\"f'UPDATE {settings.DB_SCHEMA}.photo_files SET storage_backend = 's3' WHERE storage_backend = 'b2'\")",
        "op.execute(f\"UPDATE \\\"{settings.DB_SCHEMA}\\\".photo_files SET storage_backend = 's3' WHERE storage_backend = 'b2'\")"
    )

    # Downgrade lines
    content = content.replace(
        "op.execute(\"f'UPDATE {settings.DB_SCHEMA}.photos SET storage_provider = 'b2_native' WHERE storage_provider = 's3'\")",
        "op.execute(f\"UPDATE \\\"{settings.DB_SCHEMA}\\\".photos SET storage_provider = 'b2_native' WHERE storage_provider = 's3'\")"
    )
    content = content.replace(
        "op.execute(\"f'UPDATE {settings.DB_SCHEMA}.photo_files SET storage_backend = 'b2' WHERE storage_backend = 's3'\")",
        "op.execute(f\"UPDATE \\\"{settings.DB_SCHEMA}\\\".photo_files SET storage_backend = 'b2' WHERE storage_backend = 's3'\")"
    )
    
    with open(filepath, 'w') as f:
        f.write(content)

def main():
    for filename in os.listdir(MIGRATION_DIR):
        if "001_initial_schema" in filename:
            print(f"Fixing {filename}")
            process_001(os.path.join(MIGRATION_DIR, filename))
        if "abdd8b3b7828" in filename:
            print(f"Fixing {filename}")
            process_abdd(os.path.join(MIGRATION_DIR, filename))
        if "58b6b50a0398" in filename:
            print(f"Fixing {filename}")
            process_58b(os.path.join(MIGRATION_DIR, filename))

if __name__ == "__main__":
    main()
