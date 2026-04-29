# backup.py
import subprocess
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_database():
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'restaurant_db')
    backup_dir = 'C:/Restaurant_Backups/'

    os.makedirs(backup_dir, exist_ok=True)
    date_str = datetime.now().strftime('%Y%m%d')
    file_name = f"{backup_dir}{db_name}_{date_str}.sql"

    dump_cmd = ['mysqldump', f'-u{db_user}']
    if db_pass:
        dump_cmd.append(f'-p{db_pass}')
    dump_cmd.append(db_name)
    print(f"Starting backup for {db_name}...")
    try:
        with open(file_name, 'w') as f:
            subprocess.run(dump_cmd, stdout=f, check=True)
        print(f"Done: {file_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    backup_database()