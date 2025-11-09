#!/usr/bin/env python3
"""
Automaattinen kuvien luokittelupalvelu
Tämä palvelu valvoo /data/source kansiota ja luokittelee uudet kuvat automaattisesti.
"""
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Lisää projektikansio polkuun
sys.path.insert(0, os.path.dirname(__file__))

from classify_images import classify_images_hierarchical
from app import ImageDatabase

# Konfiguraatio
SOURCE_DIR = Path('/data/source')
TARGET_DIR = Path('/data/classified')
CHECK_INTERVAL = 60  # Tarkista uudet kuvat 60 sekunnin välein
BATCH_DELAY = 5  # Odota 5 sekuntia ennen luokittelua (antaa aikaa useille tiedostoille)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ImageClassifierHandler(FileSystemEventHandler):
    """Käsittelee tiedostojärjestelmän tapahtumat ja luokittelee kuvat"""
    
    def __init__(self, source_dir, target_dir, db):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.db = db
        self.pending_files = set()
        self.last_classification = 0
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.jfif'}
        logger.info(f"ImageClassifierHandler alustettu: source={source_dir}, target={target_dir}")
    
    def is_image_file(self, path):
        """Tarkista onko tiedosto kuva"""
        return Path(path).suffix.lower() in self.image_extensions
    
    def on_created(self, event):
        """Käsitellään uuden tiedoston luonti"""
        if not event.is_directory and self.is_image_file(event.src_path):
            logger.info(f"Uusi kuva havaittu: {event.src_path}")
            self.pending_files.add(event.src_path)
    
    def on_moved(self, event):
        """Käsitellään tiedoston siirto"""
        if not event.is_directory and self.is_image_file(event.dest_path):
            logger.info(f"Kuva siirretty: {event.dest_path}")
            self.pending_files.add(event.dest_path)
    
    def process_pending_files(self):
        """Luokittele odottavat tiedostot"""
        current_time = time.time()
        
        # Tarkista onko tarpeeksi aikaa viimeisestä luokittelusta
        if current_time - self.last_classification < BATCH_DELAY:
            return
        
        if not self.pending_files:
            return
        
        logger.info(f"Aloitetaan luokittelu {len(self.pending_files)} kuvalle")
        self.pending_files.clear()
        
        try:
            # Suorita luokittelu
            result = classify_images_hierarchical(
                str(self.source_dir),
                str(self.target_dir),
                self.db
            )
            
            if 'error' in result:
                logger.error(f"Luokittelu epäonnistui: {result['error']}")
            else:
                logger.info(f"Luokittelu onnistui: {result.get('stats', {})}")
                
            self.last_classification = current_time
            
        except Exception as e:
            logger.error(f"Virhe luokittelussa: {e}", exc_info=True)

def scan_for_new_images(source_dir, target_dir, db):
    """Skannaa lähdekansio ja luokittele uudet kuvat"""
    try:
        if not source_dir.exists():
            logger.warning(f"Lähdekansio ei ole olemassa: {source_dir}")
            return
        
        # Laske kuvien määrä lähdekansiossa
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.jfif'}
        image_count = sum(1 for f in source_dir.rglob('*') if f.is_file() and f.suffix.lower() in image_extensions)
        
        if image_count == 0:
            logger.debug(f"Ei uusia kuvia lähdekansiossa: {source_dir}")
            return
        
        logger.info(f"Löytyi {image_count} kuvaa lähdekansiosta. Aloitetaan luokittelu...")
        
        # Suorita luokittelu
        result = classify_images_hierarchical(
            str(source_dir),
            str(target_dir),
            db
        )
        
        if 'error' in result:
            logger.error(f"Luokittelu epäonnistui: {result['error']}")
        else:
            stats = result.get('stats', {})
            logger.info(f"Luokittelu valmis: {stats.get('total', 0)} kuvaa käsitelty")
            
    except Exception as e:
        logger.error(f"Virhe skannauksessa: {e}", exc_info=True)

def main():
    """Pääohjelma"""
    logger.info("=" * 80)
    logger.info("Automaattinen kuvien luokittelupalvelu käynnistyy")
    logger.info("=" * 80)
    
    # Varmista että kansiot ovat olemassa
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    # Alusta tietokanta
    logger.info(f"Alustetaan tietokanta: {TARGET_DIR}")
    db = ImageDatabase(TARGET_DIR)
    
    # Suorita ensimmäinen skannaus käynnistyksen yhteydessä
    logger.info("Suoritetaan ensimmäinen skannaus...")
    scan_for_new_images(SOURCE_DIR, TARGET_DIR, db)
    
    # Alusta tiedostojärjestelmän tarkkailija
    logger.info(f"Aloitetaan kansion valvonta: {SOURCE_DIR}")
    event_handler = ImageClassifierHandler(SOURCE_DIR, TARGET_DIR, db)
    observer = Observer()
    observer.schedule(event_handler, str(SOURCE_DIR), recursive=True)
    observer.start()
    
    logger.info(f"Palvelu käynnissä. Tarkistetaan uudet kuvat {CHECK_INTERVAL} sekunnin välein.")
    logger.info("Paina Ctrl+C lopettaaksesi")
    
    try:
        last_scan = time.time()
        
        while True:
            time.sleep(1)
            
            # Käsittele odottavat tiedostot
            event_handler.process_pending_files()
            
            # Suorita säännöllinen skannaus
            current_time = time.time()
            if current_time - last_scan >= CHECK_INTERVAL:
                logger.debug(f"Suoritetaan säännöllinen skannaus...")
                scan_for_new_images(SOURCE_DIR, TARGET_DIR, db)
                last_scan = current_time
                
    except KeyboardInterrupt:
        logger.info("Vastaanotettu keskeytyskäsky, pysäytetään palvelu...")
        observer.stop()
    except Exception as e:
        logger.error(f"Odottamaton virhe: {e}", exc_info=True)
        observer.stop()
    
    observer.join()
    logger.info("Palvelu pysäytetty")

if __name__ == '__main__':
    main()
