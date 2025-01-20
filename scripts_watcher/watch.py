from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import requests
import logging
from time import sleep

logger = logging.getLogger(__name__)

class ScriptEventHandler(FileSystemEventHandler):
    def __init__(self, api_url: str):
        self.api_url = api_url

    def on_created(self, event):
        if event.is_directory:
            return
            
        if not event.src_path.endswith('.txt'):
            return
            
        try:
            # Get channel name from parent directory
            channel_name = os.path.basename(os.path.dirname(event.src_path))
            
            # Notify API about new script
            response = requests.post(
                f"{self.api_url}/process_script",
                json={
                    "file_path": event.src_path,
                    "channel_name": channel_name
                }
            )
            response.raise_for_status()
            logger.info(f"Successfully notified API about new script: {event.src_path}")
            
        except Exception as e:
            logger.error(f"Error processing new script {event.src_path}: {str(e)}")

class ScriptWatcher:
    def __init__(self, watch_directory: str, api_url: str):
        self.watch_directory = watch_directory
        self.event_handler = ScriptEventHandler(api_url)
        self.observer = Observer()

    def start(self):
        """
        Start watching the scripts directory
        """
        try:
            self.observer.schedule(
                self.event_handler,
                self.watch_directory,
                recursive=True
            )
            self.observer.start()
            logger.info(f"Started watching directory: {self.watch_directory}")
            
            try:
                while True:
                    sleep(1)
            except KeyboardInterrupt:
                self.observer.stop()
                logger.info("Stopped watching directory due to keyboard interrupt")
            
            self.observer.join()
            
        except Exception as e:
            logger.error(f"Error in script watcher: {str(e)}")
            raise

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scripts_dir = os.getenv("SCRIPTS_DIR")
    api_url = "http://localhost:8000"  # FastAPI server URL
    
    watcher = ScriptWatcher(scripts_dir, api_url)
    watcher.start()
