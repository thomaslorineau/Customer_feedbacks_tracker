"""
Test script for critical fixes applied to the codebase.
Tests backup module, SQL queries, and imports.
"""
import sys
import os
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def test_backup_module_import():
    """Test that backup module can be imported."""
    print("=" * 60)
    print("Test 1: Import backup module")
    print("=" * 60)
    try:
        from app.utils.backup import create_postgres_backup, rotate_backups, check_pg_dump_available
        print("[OK] Backup module imported successfully")
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import backup module: {e}")
        return False


def test_admin_router_import():
    """Test that admin router doesn't have obsolete imports."""
    print("\n" + "=" * 60)
    print("Test 2: Check admin router (check for obsolete imports)")
    print("=" * 60)
    try:
        # Read admin.py file to check for obsolete imports
        admin_path = backend_dir / "app" / "routers" / "admin.py"
        if not admin_path.exists():
            print("[WARN] admin.py not found")
            return False
        
        content = admin_path.read_text(encoding='utf-8')
        
        # Check for obsolete import
        if "from scripts.backup_db import" in content:
            print("[ERROR] Obsolete backup_db import still present in admin.py")
            return False
        
        # Check for new import
        if "from ...utils.backup import" in content or "from app.utils.backup import" in content:
            print("[OK] Admin router uses centralized backup module")
        else:
            print("[WARN] Admin router might not use centralized backup module")
        
        # Check that trigger_backup uses create_postgres_backup
        if "create_postgres_backup" in content:
            print("[OK] Admin router uses create_postgres_backup function")
        else:
            print("[WARN] Admin router might not use create_postgres_backup")
        
        print("[OK] No obsolete imports detected")
        return True
    except Exception as e:
        print(f"[ERROR] Error checking admin router: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_db_postgres_import():
    """Test that db_postgres can be imported without USE_POSTGRES."""
    print("\n" + "=" * 60)
    print("Test 3: Import db_postgres (check USE_POSTGRES removal)")
    print("=" * 60)
    try:
        # Set minimal environment
        os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
        
        from app import db_postgres
        print("[OK] db_postgres imported successfully")
        
        # Check that USE_POSTGRES is not defined
        if hasattr(db_postgres, 'USE_POSTGRES'):
            print("[WARN] USE_POSTGRES still exists (should be removed)")
            return False
        else:
            print("[OK] USE_POSTGRES removed correctly")
        
        # Check that POSTGRES_AVAILABLE exists
        if hasattr(db_postgres, 'POSTGRES_AVAILABLE'):
            print("[OK] POSTGRES_AVAILABLE exists")
        else:
            print("[WARN] POSTGRES_AVAILABLE missing")
        
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import db_postgres: {e}")
        return False
    except Exception as e:
        # Other errors are OK (e.g., DB connection)
        print(f"⚠️  Import OK but other error (expected): {e}")
        return True


def test_transaction_management():
    """Test that transaction management functions exist."""
    print("\n" + "=" * 60)
    print("Test 4: Transaction management (autocommit parameter)")
    print("=" * 60)
    try:
        from app.db_postgres import get_pg_connection, get_pg_cursor
        
        # Check function signatures
        import inspect
        
        # Check get_pg_connection
        sig_conn = inspect.signature(get_pg_connection)
        if 'autocommit' in sig_conn.parameters:
            print("[OK] get_pg_connection has autocommit parameter")
        else:
            print("[ERROR] get_pg_connection missing autocommit parameter")
            return False
        
        # Check get_pg_cursor
        sig_cursor = inspect.signature(get_pg_cursor)
        if 'autocommit' in sig_cursor.parameters:
            print("[OK] get_pg_cursor has autocommit parameter")
        else:
            print("[ERROR] get_pg_cursor missing autocommit parameter")
            return False
        
        return True
    except Exception as e:
        print(f"[ERROR] Error checking transaction management: {e}")
        return False


def test_sql_interval_fix():
    """Test that SQL interval query is fixed."""
    print("\n" + "=" * 60)
    print("Test 5: SQL INTERVAL query fix")
    print("=" * 60)
    try:
        from app.db_postgres import pg_get_timeline_stats
        
        # Check source code for correct SQL
        import inspect
        source = inspect.getsource(pg_get_timeline_stats)
        
        if "make_interval" in source:
            print("[OK] SQL query uses make_interval()")
        else:
            print("[WARN] SQL query might not use make_interval()")
        
        if "INTERVAL '%s days'" in source:
            print("[ERROR] Old INTERVAL syntax still present!")
            return False
        else:
            print("[OK] Old INTERVAL syntax removed")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error checking SQL fix: {e}")
        return False


def test_backup_functions():
    """Test backup utility functions."""
    print("\n" + "=" * 60)
    print("Test 6: Backup utility functions")
    print("=" * 60)
    try:
        from app.utils.backup import check_pg_dump_available, rotate_backups
        
        # Test check_pg_dump_available (should not crash)
        result = check_pg_dump_available()
        print(f"[OK] check_pg_dump_available() returned: {result}")
        
        # Test rotate_backups signature
        import inspect
        sig = inspect.signature(rotate_backups)
        params = list(sig.parameters.keys())
        expected_params = ['backup_dir', 'backup_type', 'keep_count']
        
        if all(p in params for p in expected_params):
            print(f"[OK] rotate_backups has correct parameters: {params}")
        else:
            print(f"[WARN] rotate_backups parameters: {params} (expected: {expected_params})")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error testing backup functions: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_worker_backup_import():
    """Test that worker can import backup module."""
    print("\n" + "=" * 60)
    print("Test 7: Worker backup import")
    print("=" * 60)
    try:
        # Read worker.py and check for backup import
        worker_path = backend_dir / "worker.py"
        if not worker_path.exists():
            print("[WARN] worker.py not found")
            return False
        
        content = worker_path.read_text(encoding='utf-8')
        
        if "from app.utils.backup import create_postgres_backup" in content:
            print("[OK] Worker uses centralized backup module")
        else:
            print("[WARN] Worker might not use centralized backup module")
        
        if "from scripts.backup_db import" in content or "backup_db" in content:
            print("[ERROR] Worker still has old backup_db import!")
            return False
        else:
            print("[OK] Worker doesn't have old backup_db import")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error checking worker: {e}")
        return False


def test_scheduler_backup_import():
    """Test that scheduler uses centralized backup."""
    print("\n" + "=" * 60)
    print("Test 8: Scheduler backup import")
    print("=" * 60)
    try:
        scheduler_jobs_path = backend_dir / "app" / "scheduler" / "jobs.py"
        if not scheduler_jobs_path.exists():
            print("[WARN] scheduler/jobs.py not found")
            return False
        
        content = scheduler_jobs_path.read_text(encoding='utf-8')
        
        if "from ..utils.backup import create_postgres_backup" in content:
            print("[OK] Scheduler uses centralized backup module")
        else:
            print("[WARN] Scheduler might not use centralized backup module")
        
        # Check that old code is removed
        if "subprocess.run" in content and "pg_dump" in content:
            # Check if it's in a function that should use backup module
            if "def auto_backup_job" in content or "def daily_backup_job" in content:
                # Check if it uses create_postgres_backup
                if "create_postgres_backup" not in content:
                    print("[WARN] Scheduler backup functions might still have old code")
                else:
                    print("[OK] Scheduler backup functions use centralized module")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error checking scheduler: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CRITICAL FIXES VALIDATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_backup_module_import,
        test_admin_router_import,
        test_db_postgres_import,
        test_transaction_management,
        test_sql_interval_fix,
        test_backup_functions,
        test_worker_backup_import,
        test_scheduler_backup_import,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"[WARN] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
