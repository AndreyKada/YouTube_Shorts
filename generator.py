import os
import sys
import requests
import random
import time
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip

class GitHubShortsGenerator:
    def __init__(self):
        # Получаем API ключи из переменных окружения
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        self.freesound_api_key = os.getenv('FREESOUND_API_KEY')
        
        if not self.pexels_api_key or not self.freesound_api_key:
            print("Ошибка: API ключи не найдены в переменных окружения")
            sys.exit(1)
        
        self.pexels_url = "https://api.pexels.com/videos/search"
        self.freesound_url = "https://freesound.org/apiv2"
        
        print(f"API ключи загружены. Pexels: {self.pexels_api_key[:10]}...")
    
    def search_videos(self, query, per_page=10):
        headers = {"Authorization": self.pexels_api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "portrait"
        }
        
        try:
            response = requests.get(self.pexels_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка поиска видео: {e}")
            return None
    
    def download_video(self, video_url, filename):
        try:
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            filepath = f"downloads/videos/{filename}"
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
        except Exception as e:
            print(f"Ошибка скачивания видео: {e}")
            return None
    
    def search_sounds(self, query, duration_max=30):
        headers = {"Authorization": f"Token {self.freesound_api_key}"}
        params = {
            "query": query,
            "page_size": 10,
            "fields": "id,name,url,previews,duration",
            "filter": f"duration:[0 TO {duration_max}]"
        }
        
        try:
            response = requests.get(f"{self.freesound_url}/search/text/", 
                                 headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка поиска аудио: {e}")
            return None
    
    def download_audio(self, audio_url, filename):
        try:
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()
            
            filepath = f"downloads/audio/{filename}"
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
        except Exception as e:
            print(f"Ошибка скачивания аудио: {e}")
            return None
    
    def convert_to_shorts_format(self, clip, target_width=1080, target_height=1920):
        current_w, current_h = clip.size
        target_ratio = target_width / target_height
        current_ratio = current_w / current_h
        
        if current_ratio > target_ratio:
            new_width = int(current_h * target_ratio)
            x_start = (current_w - new_width) // 2
            clip = clip.crop(x1=x_start, x2=x_start + new_width)
        else:
            new_height = int(current_w / target_ratio)
            y_start = (current_h - new_height) // 2
            clip = clip.crop(y1=y_start, y2=y_start + new_height)
        
        clip = clip.on_color(
            size=(target_width, target_height),
            color=(0, 0, 0),
            pos='center'
        )
        
        return clip
    
    def generate_single_video(self):
        """Генерирует одно видео - оптимизировано для GitHub Actions"""
        
        # Наборы тем
        theme_sets = {
            'nature': {
                'video': ["forest peaceful", "ocean waves", "sunset nature", "rain window"],
                'audio': ["forest sounds", "ocean waves", "rain sounds", "nature ambient"]
            },
            'cozy': {
                'video': ["coffee morning", "fireplace warm", "candle flame", "cozy home"],
                'audio': ["cafe atmosphere", "meditation music", "lo-fi chill"]
            }
        }
        
        # Выбираем случайную тематику
        theme_name = random.choice(list(theme_sets.keys()))
        themes = theme_sets[theme_name]
        
        print(f"Выбрана тематика: {theme_name}")
        
        # Скачиваем 3 видеоклипа
        video_files = []
        for i in range(3):
            theme = random.choice(themes['video'])
            print(f"Ищем видео: {theme}")
            
            videos_data = self.search_videos(theme, per_page=5)
            if not videos_data or not videos_data.get('videos'):
                continue
            
            video = random.choice(videos_data['videos'])
            video_url = video['video_files'][0]['link']
            filename = f"clip_{i}_{int(time.time())}.mp4"
            
            filepath = self.download_video(video_url, filename)
            if filepath:
                video_files.append(filepath)
                print(f"Скачан: {filename}")
            
            time.sleep(2)  # Пауза между запросами
        
        if len(video_files) < 2:
            print("Недостаточно видео для создания ролика")
            return None
        
        # Скачиваем аудио
        audio_file = None
        theme = random.choice(themes['audio'])
        print(f"Ищем аудио: {theme}")
        
        audio_data = self.search_sounds(theme)
        if audio_data and audio_data.get('results'):
            audio = random.choice(audio_data['results'])
            if 'previews' in audio and 'preview-hq-mp3' in audio['previews']:
                audio_url = audio['previews']['preview-hq-mp3']
                filename = f"background_{int(time.time())}.mp3"
                audio_file = self.download_audio(audio_url, filename)
                if audio_file:
                    print(f"Скачано аудио: {filename}")
        
        # Создаем видео
        print("Создаем финальное видео...")
        clips = []
        
        try:
            for i, video_file in enumerate(video_files):
                clip = VideoFileClip(video_file)
                
                # Ограничиваем длительность
                duration = min(3, clip.duration)
                if clip.duration > duration:
                    start_time = random.uniform(0, clip.duration - duration)
                    clip = clip.subclip(start_time, start_time + duration)
                
                # Приводим к формату 9:16
                clip = self.convert_to_shorts_format(clip)
                clips.append(clip)
            
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Добавляем аудио
            if audio_file:
                background_audio = AudioFileClip(audio_file)
                if background_audio.duration > final_video.duration:
                    background_audio = background_audio.subclip(0, final_video.duration)
                
                final_video = final_video.set_audio(background_audio.volumex(0.7))
            
            # Экспорт
            output_path = f"output/shorts_github_{int(time.time())}.mp4"
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                preset='ultrafast'  # Быстрый экспорт для GitHub Actions
            )
            
            print(f"Видео создано: {output_path}")
            
            # Закрываем клипы
            for clip in clips:
                clip.close()
            final_video.close()
            if audio_file:
                background_audio.close()
            
            return output_path
            
        except Exception as e:
            print(f"Ошибка создания видео: {e}")
            return None

if __name__ == "__main__":
    print("Запуск генератора для GitHub Actions")
    
    generator = GitHubShortsGenerator()
    result = generator.generate_single_video()
    
    if result:
        print(f"Успешно создано: {result}")
        # Показываем размер файла
        size_mb = os.path.getsize(result) / (1024 * 1024)
        print(f"Размер: {size_mb:.1f} MB")
    else:
        print("Не удалось создать видео")
        sys.exit(1)
