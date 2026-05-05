import os
import json
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


class YouTubeUploader:
    """Класс для загрузки видео на YouTube с поддержкой отложенной публикации."""
    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    def __init__(self, oauth_client_json_path: str = None, token_path: str = "token.pickle"):
        """
        Инициализация YouTube загрузчика.
        
        Args:
            oauth_client_json_path: Путь к файлу OAuth 2.0 клиента (client_secret.json)
            token_path: Путь для сохранения access token
        """
        self.oauth_client_json_path = oauth_client_json_path
        self.token_path = token_path
        self.youtube = None
        self.authenticated = False
        
    def authenticate(self) -> bool:
        """Аутентификация через OAuth 2.0."""
        creds = None
        
        # Check for token file
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not self.oauth_client_json_path or not os.path.exists(self.oauth_client_json_path):
                    raise FileNotFoundError(
                        f"OAuth client JSON file not found: {self.oauth_client_json_path}. "
                        "Please download from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_client_json_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        try:
            self.youtube = build('youtube', 'v3', credentials=creds)
            self.authenticated = True
            print("✅ Успешно авторизован в YouTube API")
            return True
        except Exception as e:
            print(f"❌ Ошибка авторизации YouTube: {e}")
            return False
    
    def generate_metadata(self, video_title: str, story_draft_path: str = "data/story_draft.txt") -> Dict:
        """
        Генерация метаданных для видео (название, описание, хештеги).
        
        Args:
            video_title: Название видео
            story_draft_path: Путь к сценарию для генерации описания
            
        Returns:
            Словарь с метаданными
        """
        # Читаем сценарий для описания
        description = ""
        if os.path.exists(story_draft_path):
            with open(story_draft_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Берем первые 3 абзаца или 500 символов
                paragraphs = content.split('\n\n')
                description = '\n\n'.join(paragraphs[:3])[:4500]  # YouTube limit: 5000 chars
        
        # Генерация хештегов на основе названия
        tags = self._generate_tags(video_title)
        
        # Категория по умолчанию (Entertainment: 24, Education: 27)
        category_id = "24"  # Entertainment
        
        metadata = {
            "title": video_title[:100],  # YouTube limit: 100 chars
            "description": description,
            "tags": tags[:500],  # YouTube limit: 500 tags total
            "category_id": category_id,
            "privacy_status": "private",  # Default to private for scheduling
            "made_for_kids": False
        }
        
        return metadata
    
    def _generate_tags(self, title: str) -> List[str]:
        """Генерация релевантных хештегов на основе названия."""
        # Базовые теги для AI видео
        base_tags = ["AI", "искусственныйинтеллект", "видеогенерация", "нейросети"]
        
        # Извлекаем ключевые слова из названия
        words = title.lower().split()
        keywords = [word for word in words if len(word) > 3][:10]
        
        # Русские теги
        russian_tags = ["видео", "русский", "ютуб", "контент", "создание", "автоматизация"]
        
        # Комбинируем все теги
        all_tags = base_tags + keywords + russian_tags
        
        # Удаляем дубликаты и ограничиваем количество
        unique_tags = []
        for tag in all_tags:
            clean_tag = tag.strip().replace(" ", "")
            if clean_tag and clean_tag not in unique_tags and len(unique_tags) < 30:
                unique_tags.append(clean_tag)
        
        return unique_tags
    
    def upload_video(
        self,
        video_path: str,
        metadata: Dict,
        schedule_time: Optional[str] = None,
        notify_subscribers: bool = True
    ) -> Tuple[bool, str, str]:
        """
        Загрузка видео на YouTube.
        
        Args:
            video_path: Путь к видеофайлу
            metadata: Словарь метаданных
            schedule_time: Время отложенной публикации в формате RFC 3339
            notify_subscribers: Уведомлять подписчиков
            
        Returns:
            Кортеж (успех, video_id, ссылка)
        """
        if not self.authenticated or not self.youtube:
            if not self.authenticate():
                return False, "", "Не удалось аутентифицироваться"
        
        if not os.path.exists(video_path):
            return False, "", f"Файл не найден: {video_path}"
        
        try:
            # Подготовка body запроса
            body = {
                "snippet": {
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "tags": metadata["tags"],
                    "categoryId": metadata["category_id"],
                },
                "status": {
                    "privacyStatus": metadata.get("privacy_status", "private"),
                    "selfDeclaredMadeForKids": metadata.get("made_for_kids", False),
                    "notifySubscribers": notify_subscribers,
                }
            }
            
            # Добавляем отложенную публикацию если указана
            if schedule_time:
                body["status"]["publishAt"] = schedule_time
                print(f"📅 Установлено время публикации: {schedule_time}")
            else:
                # Если не указано время, публикуем как unlisted для проверки
                body["status"]["privacyStatus"] = "unlisted"
                print("⚠️  Время публикации не указано. Видео будет загружено как unlisted.")
            
            # Подготовка медиафайла
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            # Вызов API для загрузки
            print(f"📤 Начинаю загрузку: {video_path}")
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Выполнение загрузки
            response = request.execute()
            video_id = response.get("id")
            video_url = f"https://youtube.com/watch?v={video_id}"
            
            print(f"✅ Видео загружено успешно!")
            print(f"   ID: {video_id}")
            print(f"   Ссылка: {video_url}")
            print(f"   Статус: {response.get('status', {}).get('uploadStatus', 'unknown')}")
            
            return True, video_id, video_url
            
        except HttpError as e:
            error_msg = f"Ошибка YouTube API: {e}"
            print(f"❌ {error_msg}")
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Ошибка загрузки: {e}"
            print(f"❌ {error_msg}")
            return False, "", error_msg
    
    def get_video_status(self, video_id: str) -> Dict:
        """Получение статуса видео."""
        if not self.authenticated or not self.youtube:
            return {"error": "Not authenticated"}
        
        try:
            request = self.youtube.videos().list(
                part="status,statistics",
                id=video_id
            )
            response = request.execute()
            return response.get("items", [{}])[0] if response.get("items") else {}
        except Exception as e:
            return {"error": str(e)}
    
    def list_uploaded_videos(self, max_results: int = 10) -> List[Dict]:
        """Список загруженных видео."""
        if not self.authenticated or not self.youtube:
            return []
        
        try:
            request = self.youtube.videos().list(
                part="snippet,status",
                myRating="like",
                maxResults=max_results
            )
            response = request.execute()
            return response.get("items", [])
        except Exception as e:
            print(f"Ошибка получения списка видео: {e}")
            return []


# Вспомогательные функции для интеграции
def find_latest_video(outputs_dir: str = "outputs/final_videos") -> Optional[str]:
    """Поиск последнего созданного видеофайла."""
    if not os.path.exists(outputs_dir):
        return None
    
    video_files = []
    for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        video_files.extend(Path(outputs_dir).glob(f"*{ext}"))
    
    if not video_files:
        return None
    
    # Берем самый новый файл
    latest_video = max(video_files, key=os.path.getmtime)
    return str(latest_video)


def generate_schedule_time(days_from_now: int = 1, hour: int = 18, minute: int = 0) -> str:
    """
    Генерация времени публикации в формате RFC 3339.
    
    Args:
        days_from_now: Через сколько дней опубликовать
        hour: Час публикации (0-23)
        minute: Минута публикации (0-59)
    
    Returns:
        Строка времени в формате RFC 3339
    """
    publish_time = datetime.now() + timedelta(days=days_from_now)
    publish_time = publish_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return publish_time.isoformat() + "Z"


def save_upload_record(video_id: str, video_url: str, metadata: Dict, 
                      schedule_time: Optional[str] = None, file_path: str = "youtube_uploads.json"):
    """Сохранение записи о загрузке в JSON файл."""
    record = {
        "video_id": video_id,
        "video_url": video_url,
        "metadata": metadata,
        "schedule_time": schedule_time,
        "upload_time": datetime.now().isoformat()
    }
    
    # Читаем существующие записи или создаем новый список
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                records = []
    else:
        records = []
    
    records.append(record)
    
    # Сохраняем
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"📝 Запись о загрузке сохранена в {file_path}")


if __name__ == "__main__":
    # Пример использования
    uploader = YouTubeUploader(oauth_client_json_path="client_secret.json")
    
    # Авторизация
    if uploader.authenticate():
        # Поиск последнего видео
        video_path = find_latest_video()
        if video_path:
            print(f"📹 Найдено видео: {video_path}")
            
            # Генерация метаданных
            video_title = f"AI Generated Video - {datetime.now().strftime('%Y-%m-%d')}"
            metadata = uploader.generate_metadata(video_title)
            
            # Генерация времени публикации (завтра в 18:00)
            schedule_time = generate_schedule_time(days_from_now=1, hour=18, minute=0)
            
            # Загрузка
            success, video_id, video_url = uploader.upload_video(
                video_path=video_path,
                metadata=metadata,
                schedule_time=schedule_time
            )
            
            if success:
                save_upload_record(video_id, video_url, metadata, schedule_time)
        else:
            print("❌ Видео для загрузки не найдено")
    else:
        print("❌ Ошибка аутентификации")