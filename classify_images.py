import os
import shutil
from datetime import datetime
from pathlib import Path
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS

def get_image_hash(file_path):
    """Laskee kuvan hash-arvon tunnistamaan duplikaatit"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Virhe hashin laskennassa {file_path}: {e}")
        return None

def get_week_number(date):
    """Palauttaa viikkonumeron"""
    return date.isocalendar()[1]

def get_exif_date(image):
    """Yrittää hakea kuvan päivämäärän EXIF-tiedoista"""
    try:
        exif_data = image._getexif()
        if exif_data:
            # Tunnisteet päivämäärälle
            date_tags = [
                36867,  # DateTimeOriginal (kuvausaika)
                36868,  # DateTimeDigitized (digitoimisaika)
                306,    # DateTime (muokkausaika)
            ]
            
            for tag_id in date_tags:
                if tag_id in exif_data:
                    date_str = exif_data[tag_id]
                    try:
                        # Yleisin EXIF-datemuoto: 'YYYY:MM:DD HH:MM:SS'
                        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        # Kokeile muita muotoja
                        try:
                            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
    except Exception:
        pass
    return None

def get_image_metadata_date(file_path):
    """Yrittää hakea kuvan päivämäärän metadata-tiedoista"""
    try:
        with Image.open(file_path) as img:
            # Yritä EXIF-tietoja ensin
            exif_date = get_exif_date(img)
            if exif_date:
                return exif_date, 'exif'
            
            # Yritä kuvan muita metadata-tietoja
            try:
                if hasattr(img, '_getexif') and img._getexif():
                    for tag_id, value in img._getexif().items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if 'date' in tag_name.lower() or 'time' in tag_name.lower():
                            if isinstance(value, str) and len(value) > 8:
                                try:
                                    parsed_date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                    return parsed_date, 'exif_other'
                                except ValueError:
                                    continue
            except Exception:
                pass
            
    except Exception as e:
        print(f"Virhe avattaessa kuvaa {file_path}: {e}")
    
    return None, 'none'

def get_best_available_date(file_path):
    """Hakee parhaan saatavilla olevan päivämäärän"""
    # Yritä ensin EXIF-metadataa
    metadata_date, source = get_image_metadata_date(file_path)
    if metadata_date:
        return metadata_date, source
    
    # Fallback: tiedostojärjestelmän aikaleima
    try:
        filesystem_time = file_path.stat().st_mtime
        return datetime.fromtimestamp(filesystem_time), 'filesystem'
    except Exception as e:
        print(f"Virhe aikaleiman haussa {file_path}: {e}")
        return None, 'none'

def classify_images_hierarchical(source_dir, target_base_dir, db):
    """
    Luokittelee kuvat hierarkkisesti käyttäen kuvan sisäistä metadataa
    Tallentaa kuvat linkkeinä (symlink tai hardlink) levytilan säästämiseksi.
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.jfif'}
    source_path = Path(source_dir)
    target_base_path = Path(target_base_dir)
    
    if not source_path.exists():
        return {"error": f"Lähdekansiota ei löydy: {source_dir}"}
    
    # Varmista että kohdekansio on olemassa
    target_base_path.mkdir(parents=True, exist_ok=True)
    
    all_images = []
    stats = {'total': 0, 'exif': 0, 'exif_other': 0, 'filesystem': 0, 'failed': 0}
    
    print(f"Etsitään kuvia kansiosta: {source_dir}")
    
    # Käy läpi kaikki tiedostot
    for file_path in source_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            stats['total'] += 1
            
            try:
                image_date, source = get_best_available_date(file_path)
                if not image_date:
                    stats['failed'] += 1
                    print(f"Ei aikaleimaa: {file_path.name}")
                    continue
                
                # Päivitä tilastot
                if source == 'exif':
                    stats['exif'] += 1
                elif source == 'exif_other':
                    stats['exif_other'] += 1
                elif source == 'filesystem':
                    stats['filesystem'] += 1
                
                image_hash = get_image_hash(file_path)
                if not image_hash:
                    continue
                
                image_info = {
                    'path': file_path,
                    'date': image_date,
                    'hash': image_hash,
                    'filename': file_path.name,
                    'source': source
                }
                all_images.append(image_info)
                
                if stats['total'] % 100 == 0:
                    print(f"Analysoitu {stats['total']} kuvaa...")
                    print(f"  - EXIF: {stats['exif']}, EXIF-muu: {stats['exif_other']}, Tiedosto: {stats['filesystem']}")
                
            except Exception as e:
                stats['failed'] += 1
                print(f"Virhe käsiteltäessä tiedostoa {file_path.name}: {e}")
    
    if not all_images:
        return {"error": f"Ei kuvia löytynyt kansiosta {source_dir} tai kaikissa puuttuu päivämäärä"}
    
    # Järjestä kuvat aikaleiman mukaan
    all_images.sort(key=lambda x: x['date'])
    
    print(f"Löydetty {len(all_images)} kuvaa")
    print(f"Aikaväli: {all_images[0]['date']} - {all_images[-1]['date']}")
    print(f"Lähteet: EXIF: {stats['exif']}, EXIF-muu: {stats['exif_other']}, Tiedosto: {stats['filesystem']}")
    
    # Kopioi (tai linkitä) kuvat ja päivitä tietokanta
    copy_results = copy_all_images_to_structure(all_images, target_base_path, db)
    
    result = {
        "stats": stats,
        "classified": copy_results,
        "date_range": {
            "start": all_images[0]['date'].isoformat(),
            "end": all_images[-1]['date'].isoformat()
        }
    }
    
    return result

def copy_all_images_to_structure(all_images, target_base_path, db):
    """Kopioi kaikki kuvat hierarkkiseen kansiorakenteeseen (LINK MODE mahdollinen)"""
    results = {}
    
    categories = [
        ('01_vuodet', 'year'),
        ('02_kuukaudet', 'month'),
        ('03_viikot', 'week'),
        ('04_paivat', 'day'),
        ('05_tunnit', 'hour'),
        ('06_minuutit', 'minute'),
        ('07_sekunnit', 'second')
    ]
    
    # Link-mode: 'symlink' (oletus), 'hardlink', tai 'copy'
    LINK_MODE = os.environ.get('LINK_MODE', 'symlink').lower()
    
    # Käytä settiä seurattavaksi jo käsitellyistä kuvista
    processed_images = set()
    
    for dir_name, category_type in categories:
        category_dir = target_base_path / dir_name
        category_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Käsitellään kategoriaa: {dir_name}")
        
        image_count = 0
        folder_count = 0
        processed_folders = set()
        
        for image in all_images:
            # Tarkista onko kuva jo käsitelty (estää duplikaatit samassa kategoriassa)
            image_key = f"{image['filename']}_{image['hash']}"
            if image_key in processed_images:
                continue
                
            date = image['date']
            
            if category_type == 'year':
                time_key = str(date.year)
                folder_name = time_key
            elif category_type == 'month':
                time_key = f"{date.year}-{date.month:02d}"
                folder_name = time_key
            elif category_type == 'week':
                time_key = f"{date.year}-W{get_week_number(date):02d}"
                folder_name = time_key
            elif category_type == 'day':
                time_key = f"{date.year}-{date.month:02d}-{date.day:02d}"
                folder_name = time_key
            elif category_type == 'hour':
                time_key = f"{date.year}-{date.month:02d}-{date.day:02d}-{date.hour:02d}"
                folder_name = time_key
            elif category_type == 'minute':
                time_key = f"{date.year}-{date.month:02d}-{date.day:02d}-{date.hour:02d}-{date.minute:02d}"
                folder_name = time_key
            elif category_type == 'second':
                time_key = f"{date.year}-{date.month:02d}-{date.day:02d}-{date.hour:02d}-{date.minute:02d}-{date.second:02d}"
                folder_name = time_key
            else:
                continue
            
            # Luo kansio jos ei ole jo olemassa
            time_dir = category_dir / folder_name
            if folder_name not in processed_folders:
                time_dir.mkdir(parents=True, exist_ok=True)
                processed_folders.add(folder_name)
                folder_count += 1
            
            # Kohdetiedosto
            target_file = time_dir / image['filename']
            try:
                if not target_file.exists():
                    if LINK_MODE == 'symlink':
                        try:
                            os.symlink(os.path.abspath(str(image['path'])), str(target_file))
                        except Exception as e:
                            print(f"Symlink epäonnistui, yritetään kopioida: {e}")
                            shutil.copy2(image['path'], target_file)
                    elif LINK_MODE == 'hardlink':
                        try:
                            os.link(image['path'], target_file)
                        except Exception as e:
                            print(f"Hardlink epäonnistui, yritetään kopioida: {e}")
                            shutil.copy2(image['path'], target_file)
                    else:
                        shutil.copy2(image['path'], target_file)
                    
                    # Päivitä tiedostoon aikaleima kuvan datan perusteella
                    try:
                        os.utime(target_file, (image['date'].timestamp(), image['date'].timestamp()))
                    except Exception:
                        pass
                
                # Lisää tietokantaan vain jos ei ole jo lisätty
                rel_path = str(target_file.relative_to(target_base_path))
                if rel_path not in db.images:
                    db.add_image(target_file, image['date'].isoformat(), f"{category_type}_{time_key}", image['source'])
                    image_count += 1
                    processed_images.add(image_key)  # Merkkaa käsitellyksi
            except Exception as e:
                print(f"Virhe käsiteltäessä {image['filename']}: {e}")
        
        results[category_type] = {
            'folders': folder_count,
            'images': image_count
        }
        print(f"  - Luotu {folder_count} kansiota, {image_count} uniikkia kuvaa")
    
    db.save_database()
    
    # Skannaa myös manuaalisesti kaikki kuvat varmuuden vuoksi
    print("Skannataan kuvat uudelleen varmuuden vuoksi...")
    added_count = db.scan_for_images()
    if added_count > 0:
        print(f"Skannauksessa lisätty {added_count} uutta kuvaa tietokantaan")
    
    return results
