import os
import shutil
import zipfile
import tempfile
import requests
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

import discord
from discord.ext import commands

import config


class UpdateStatus(Enum):
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    UPDATE_FAILED = "update_failed"
    UPDATE_SUCCESS = "update_success"


@dataclass
class UpdateInfo:
    status: UpdateStatus
    current_version: str
    latest_version: str
    message: str
    changelog: Optional[str] = None


class BotUpdater:
    def __init__(
            self,
            repo_owner: str = "LegoManchik",
            repo_name: str = "PPV.voice",
            current_version: str = config.BOT_VERSION,
            blacklist: List[str] = None,
            branch: str = "master"
    ):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.branch = branch
        self.blacklist = blacklist or [
            "config.py",
            ".env",
            "data/tickets.db",
            "logs/",
            "blacklist.txt",
            "templates/",
            "backups/"
        ]
        self.github_api = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    def check_for_updates(self) -> UpdateInfo:

        try:
            response = requests.get(f"{self.github_api}/releases/latest", timeout=10)

            if response.status_code == 404:
                return self._check_by_commits()
            elif response.status_code != 200:
                return UpdateInfo(
                    status=UpdateStatus.UPDATE_FAILED,
                    current_version=self.current_version,
                    latest_version="unknown",
                    message=f"GitHub API error: {response.status_code}"
                )

            release_data = response.json()
            latest_version = release_data.get("tag_name", "").lstrip("v")

            if self._compare_versions(latest_version, self.current_version) > 0:
                return UpdateInfo(
                    status=UpdateStatus.UPDATE_AVAILABLE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    message=f"Доступна новая версия {latest_version}",
                    changelog=release_data.get("body", "Нет описания изменений")
                )
            else:
                return UpdateInfo(
                    status=UpdateStatus.UP_TO_DATE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    message="Бот обновлён до последней версии"
                )

        except Exception as e:
            return UpdateInfo(
                status=UpdateStatus.UPDATE_FAILED,
                current_version=self.current_version,
                latest_version="unknown",
                message=f"Ошибка проверки обновлений: {str(e)}"
            )

    def _check_by_commits(self) -> UpdateInfo:
        try:
            response = requests.get(
                f"{self.github_api}/commits/{self.branch}",
                timeout=10
            )

            if response.status_code != 200:
                return UpdateInfo(
                    status=UpdateStatus.UPDATE_FAILED,
                    current_version=self.current_version,
                    latest_version="unknown",
                    message="Не удалось проверить обновления"
                )

            commit_data = response.json()
            latest_sha = commit_data.get("sha", "")[:7]

            if hasattr(config, 'CURRENT_COMMIT'):
                if latest_sha != config.CURRENT_COMMIT:
                    return UpdateInfo(
                        status=UpdateStatus.UPDATE_AVAILABLE,
                        current_version=f"commit-{config.CURRENT_COMMIT}",
                        latest_version=f"commit-{latest_sha}",
                        message="Доступны новые изменения",
                        changelog=commit_data.get("commit", {}).get("message", "")
                    )

            return UpdateInfo(
                status=UpdateStatus.UP_TO_DATE,
                current_version=f"commit-{latest_sha}",
                latest_version=f"commit-{latest_sha}",
                message="Бот обновлён до последней версии"
            )

        except Exception as e:
            return UpdateInfo(
                status=UpdateStatus.UPDATE_FAILED,
                current_version=self.current_version,
                latest_version="unknown",
                message=f"Ошибка: {str(e)}"
            )

    def download_and_update(self, progress_callback: Callable = None) -> bool:
        try:
            if progress_callback:
                progress_callback(10, "Скачивание обновления...")

            zip_path = self._download_repo()
            if not zip_path:
                return False

            if progress_callback:
                progress_callback(30, "Распаковка архива...")

            extract_dir = tempfile.mkdtemp()
            self._extract_zip(zip_path, extract_dir)

            if progress_callback:
                progress_callback(50, "Создание бэкапа...")

            backup_path = self._create_backup()

            if progress_callback:
                progress_callback(70, "Замена файлов...")

            success = self._replace_files(extract_dir)

            if not success:
                if progress_callback:
                    progress_callback(90, "Ошибка! Восстановление из бэкапа...")
                self._restore_from_backup(backup_path)
                return False

            if progress_callback:
                progress_callback(90, "Очистка временных файлов...")

            self._cleanup(zip_path, extract_dir, backup_path)

            if progress_callback:
                progress_callback(100, "Обновление успешно завершено!")

            return True

        except Exception as e:
            print(f"Update failed: {e}")
            return False

    def _download_repo(self) -> Optional[str]:
        try:
            url = f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/heads/{self.branch}.zip"
            response = requests.get(url, stream=True, timeout=30)

            if response.status_code != 200:
                return None

            temp_zip = tempfile.mktemp(suffix=".zip")
            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return temp_zip

        except Exception as e:
            print(f"Download error: {e}")
            return None

    def _extract_zip(self, zip_path: str, extract_to: str):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            root_folder = None
            for name in zip_ref.namelist():
                if '/' in name:
                    root_folder = name.split('/')[0]
                    break

            zip_ref.extractall(extract_to)

            if root_folder:
                extracted_root = os.path.join(extract_to, root_folder)
                for item in os.listdir(extracted_root):
                    shutil.move(
                        os.path.join(extracted_root, item),
                        os.path.join(extract_to, item)
                    )
                os.rmdir(extracted_root)

    def _create_backup(self) -> str:

        backup_dir = f"backup_{self.current_version}"
        backup_path = os.path.join("backups/versions", backup_dir)

        os.makedirs("backups", exist_ok=True)

        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)

        shutil.copytree(".", backup_path, ignore=self._ignore_blacklist)

        return backup_path

    def _ignore_blacklist(self, directory, files):

        ignored = []
        for file in files:
            file_path = os.path.join(directory, file)
            rel_path = os.path.relpath(file_path, ".")

            for pattern in self.blacklist:
                if pattern.endswith('/'):
                    if rel_path.startswith(pattern.rstrip('/')):
                        ignored.append(file)
                        break
                elif pattern in rel_path:
                    ignored.append(file)
                    break
        return ignored

    def _replace_files(self, source_dir: str) -> bool:
        try:
            for root, dirs, files in os.walk(source_dir):
                rel_path = os.path.relpath(root, source_dir)
                if rel_path == '.':
                    rel_path = ''

                should_skip = False
                for pattern in self.blacklist:
                    if pattern.endswith('/') and rel_path.startswith(pattern.rstrip('/')):
                        should_skip = True
                        break

                if should_skip:
                    continue

                for file in files:
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(rel_path, file) if rel_path else file

                    if self._is_blacklisted(dest_file):
                        continue

                    dest_dir = os.path.dirname(dest_file)
                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)

                    shutil.copy2(source_file, dest_file)

            return True

        except Exception as e:
            print(f"Replace files error: {e}")
            return False

    def _is_blacklisted(self, file_path: str) -> bool:
        for pattern in self.blacklist:
            if pattern.endswith('/'):
                if file_path.startswith(pattern.rstrip('/')):
                    return True
            elif pattern in file_path:
                return True
        return False

    def _restore_from_backup(self, backup_path: str):
        if os.path.exists(backup_path):
            for item in os.listdir(backup_path):
                src = os.path.join(backup_path, item)
                dst = os.path.join(".", item)

                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)

                shutil.move(src, dst)

    def _cleanup(self, zip_path: str, extract_dir: str, backup_path: str):
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)

    def _compare_versions(self, v1: str, v2: str) -> int:

        def normalize(v):
            return [int(x) for x in v.split('.')]

        try:
            v1_parts = normalize(v1)
            v2_parts = normalize(v2)

            for i in range(max(len(v1_parts), len(v2_parts))):
                v1_val = v1_parts[i] if i < len(v1_parts) else 0
                v2_val = v2_parts[i] if i < len(v2_parts) else 0

                if v1_val > v2_val:
                    return 1
                elif v1_val < v2_val:
                    return -1
            return 0
        except:
            return 0

    def restart_bot(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)