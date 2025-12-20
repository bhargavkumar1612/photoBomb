#!/bin/bash
# Database migration helper script

set -e

case "$1" in
  init)
    echo "Initializing Alembic..."
    cd backend
    alembic init alembic
    echo "✓ Alembic initialized"
    ;;
    
  create)
    if [ -z "$2" ]; then
      echo "Usage: $0 create 'migration message'"
      exit 1
    fi
    echo "Creating migration: $2"
    cd backend
    alembic revision --autogenerate -m "$2"
    echo "✓ Migration created"
    ;;
    
  upgrade)
    echo "Upgrading database to latest..."
    cd backend
    alembic upgrade head
    echo "✓ Database upgraded"
    ;;
    
  downgrade)
    echo "Downgrading database by 1 revision..."
    cd backend
    alembic downgrade -1
    echo "✓ Database downgraded"
    ;;
    
  current)
    echo "Current database revision:"
    cd backend
    alembic current
    ;;
    
  history)
    echo "Migration history:"
    cd backend
    alembic history
    ;;
    
  *)
    echo "Database migration helper"
    echo ""
    echo "Usage: $0 {init|create|upgrade|downgrade|current|history}"
    echo ""
    echo "Commands:"
    echo "  init              Initialize Alembic"
    echo "  create 'message'  Create new migration"
    echo "  upgrade           Upgrade to latest"
    echo "  downgrade         Downgrade by 1"
    echo "  current           Show current revision"
    echo "  history           Show migration history"
    exit 1
    ;;
esac
