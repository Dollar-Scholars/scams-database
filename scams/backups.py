import os
import subprocess
import datetime
from pathlib import Path

# ======================
# CONFIG
# ======================

DB_NAME = "mydb"
DB_USER = "postgres"
DB_HOST = "localhost"   # add this
DB_PORT = "5432"

BACKUP_DIR = Path("/var/backups/myapp")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

REMOTE_SERVERS = [
    "user@server1:/backups/",
    "user@server2:/backups/",
    "user@server3:/backups/",
]

USE_ENCRYPTION = False
GPG_PASSPHRASE = "change-this"

# ======================

def run_command(cmd):
    print(f"\n[RUNNING] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] {result.stderr.strip()}")
        raise RuntimeError("Command failed")

    return result


def create_backup():
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = BACKUP_DIR / f"{DB_NAME}_{date}.sql"
    compressed_file = BACKUP_DIR / f"{DB_NAME}_{date}.sql.gz"

    print(f"\n[INFO] Creating backup: {backup_file}")

    with open(backup_file, "w") as f:
        result = subprocess.run(
            [
                "pg_dump",
                "-U", DB_USER,
                "-h", DB_HOST,
                "-p", DB_PORT,
                DB_NAME
            ],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True
        )

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    print("[INFO] Compressing backup...")
    run_command(["gzip", str(backup_file)])

    return compressed_file


def encrypt_file(file_path):
    encrypted_file = str(file_path) + ".gpg"

    print("[INFO] Encrypting backup...")
    run_command([
        "gpg", "--batch", "--yes",
        "--passphrase", GPG_PASSPHRASE,
        "-c", str(file_path)
    ])

    os.remove(file_path)
    return encrypted_file


def transfer_file(file_path):
    print("\n[INFO] Starting transfers...")
    processes = []

    for server in REMOTE_SERVERS:
        print(f"[INFO] Sending to {server}")
        p = subprocess.Popen(["scp", str(file_path), server])
        processes.append(p)

    for p in processes:
        p.wait()

    print("[INFO] All transfers completed.")


def cleanup_old_backups(days=7):
    print(f"\n[INFO] Cleaning old backups (> {days} days)")

    now = datetime.datetime.now()

    for file in BACKUP_DIR.glob("*"):
        if file.is_file():
            age = now - datetime.datetime.fromtimestamp(file.stat().st_mtime)
            if age.days > days:
                print(f"[INFO] Deleting {file}")
                file.unlink()


def main():
    try:
        backup_file = create_backup()

        if USE_ENCRYPTION:
            backup_file = encrypt_file(backup_file)

        transfer_file(backup_file)
        cleanup_old_backups(7)

        print("\n✅ Backup completed")

    except Exception as e:
        print(f"\n❌ Backup failed: {e}")


if __name__ == "__main__":
    main()
