import os
import glob
import shutil

def delete_migration_files_and_pycache(app_name):
    migrations_path = os.path.join(app_name, 'migrations')
    migration_files = glob.glob(os.path.join(migrations_path, '[0-9]*_*.py'))
    for migration_file in migration_files:
        os.remove(migration_file)
    pycache_path = os.path.join(migrations_path, '__pycache__')
    if os.path.exists(pycache_path):
        shutil.rmtree(pycache_path)

apps = [
    'Challenge',
    'Class',
    'Course', 
    'Discussion',
    'Exam',
    'Institution',
    'Question',
    'Quiz',
    'Subscription',
    'User',
    'Preassessment',
]

for app in apps:
    delete_migration_files_and_pycache(app)
    print(f"Deleted migrations and __pycache__ for {app}")
