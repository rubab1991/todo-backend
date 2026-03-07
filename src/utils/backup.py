import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from sqlmodel import select
from ..models.task import Task
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.user import User
from ..db.session import AsyncSessionLocal
from ..config import settings


class BackupService:
    """
    Service for backing up and recovering data
    """
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    async def create_backup(self, backup_name: str = None) -> str:
        """
        Create a backup of all data
        """
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_path = self.backup_dir / f"{backup_name}.json"

        # Collect all data to backup
        backup_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "backup_name": backup_name,
                "version": "1.0"
            },
            "users": await self._backup_users(),
            "tasks": await self._backup_tasks(),
            "conversations": await self._backup_conversations(),
            "messages": await self._backup_messages()
        }

        # Write backup to file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)

        return str(backup_path)

    async def _backup_users(self) -> List[Dict[str, Any]]:
        """
        Backup all users
        """
        async with AsyncSessionLocal() as session:
            statement = select(User)
            results = await session.exec(statement)
            users = results.all()

            user_data = []
            for user in users:
                user_dict = user.dict()
                # Convert datetime objects to ISO format strings
                for key, value in user_dict.items():
                    if isinstance(value, datetime):
                        user_dict[key] = value.isoformat()

                user_data.append(user_dict)

            return user_data

    async def _backup_tasks(self) -> List[Dict[str, Any]]:
        """
        Backup all tasks
        """
        async with AsyncSessionLocal() as session:
            statement = select(Task)
            results = await session.exec(statement)
            tasks = results.all()

            task_data = []
            for task in tasks:
                task_dict = task.dict()
                # Convert datetime objects to ISO format strings
                for key, value in task_dict.items():
                    if isinstance(value, datetime):
                        task_dict[key] = value.isoformat()

                task_data.append(task_dict)

            return task_data

    async def _backup_conversations(self) -> List[Dict[str, Any]]:
        """
        Backup all conversations
        """
        async with AsyncSessionLocal() as session:
            statement = select(Conversation)
            results = await session.exec(statement)
            conversations = results.all()

            conv_data = []
            for conv in conversations:
                conv_dict = conv.dict()
                # Convert datetime objects to ISO format strings
                for key, value in conv_dict.items():
                    if isinstance(value, datetime):
                        conv_dict[key] = value.isoformat()

                conv_data.append(conv_dict)

            return conv_data

    async def _backup_messages(self) -> List[Dict[str, Any]]:
        """
        Backup all messages
        """
        async with AsyncSessionLocal() as session:
            statement = select(Message)
            results = await session.exec(statement)
            messages = results.all()

            msg_data = []
            for msg in messages:
                msg_dict = msg.dict()
                # Convert datetime objects to ISO format strings
                for key, value in msg_dict.items():
                    if isinstance(value, datetime):
                        msg_dict[key] = value.isoformat()

                msg_data.append(msg_dict)

            return msg_data

    async def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore data from a backup file
        """
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        # This is a simplified restore that would need more sophisticated handling
        # in a real implementation to avoid conflicts and maintain referential integrity

        # In a real implementation, you would:
        # 1. Clear existing data (with proper validation)
        # 2. Restore users first
        # 3. Restore conversations (after users)
        # 4. Restore tasks (after users)
        # 5. Restore messages (after conversations and users)

        print(f"Restoring from backup: {backup_path}")
        print(f"Backup metadata: {backup_data.get('metadata', {})}")

        # Count records to be restored
        users_count = len(backup_data.get('users', []))
        tasks_count = len(backup_data.get('tasks', []))
        conversations_count = len(backup_data.get('conversations', []))
        messages_count = len(backup_data.get('messages', []))

        print(f"Records to restore - Users: {users_count}, Tasks: {tasks_count}, "
              f"Conversations: {conversations_count}, Messages: {messages_count}")

        # NOTE: Full implementation would require proper database transaction handling
        # and referential integrity management
        return True

    def list_backups(self) -> List[str]:
        """
        List all available backups
        """
        backups = []
        for file in self.backup_dir.glob("*.json"):
            backups.append(file.name)
        return sorted(backups, reverse=True)

    async def cleanup_old_backups(self, days_to_keep: int = 30) -> List[str]:
        """
        Remove backups older than specified days
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_backups = []

        for file in self.backup_dir.glob("*.json"):
            # Extract date from filename (assuming format backup_YYYYMMDD_HHMMSS.json)
            try:
                # Parse date from filename
                filename = file.stem  # Remove .json extension
                if filename.startswith("backup_"):
                    date_str = filename[7:]  # Remove "backup_" prefix
                    backup_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")

                    if backup_date < cutoff_date:
                        file.unlink()  # Delete the file
                        removed_backups.append(str(file))
            except ValueError:
                # If we can't parse the date, skip this file
                continue

        return removed_backups


class BackupScheduler:
    """
    Service for scheduling automated backups
    """
    def __init__(self, backup_service: BackupService):
        self.backup_service = backup_service
        self.is_running = False

    async def start_scheduler(self, interval_hours: int = 24):
        """
        Start the backup scheduler
        """
        if self.is_running:
            return

        self.is_running = True
        print(f"Starting backup scheduler with {interval_hours} hour intervals")

        while self.is_running:
            try:
                backup_path = await self.backup_service.create_backup()
                print(f"Automatic backup created: {backup_path}")

                # Clean up backups older than 30 days
                old_backups = await self.backup_service.cleanup_old_backups(days_to_keep=30)
                if old_backups:
                    print(f"Cleaned up old backups: {old_backups}")

            except Exception as e:
                print(f"Error during scheduled backup: {e}")

            # Wait for the specified interval
            await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds

    def stop_scheduler(self):
        """
        Stop the backup scheduler
        """
        self.is_running = False


# Global backup service instance
backup_service = BackupService()


async def schedule_daily_backups():
    """
    Convenience function to start daily backups
    """
    scheduler = BackupScheduler(backup_service)
    await scheduler.start_scheduler(interval_hours=24)