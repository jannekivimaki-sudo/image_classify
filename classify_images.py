import os
import shutil
from datetime import datetime
from pathlib import Path
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS

def get_image_hash(file_path):
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
    return date.isocalendar()[1]

def get_exif_date(image):
    try:
        # Use getexif() instead of deprecated _getexif()
        exif_data = image.getexif()
        if exif_data:
            date_tags = [36867, 36868, 306]  # DateTimeOriginal, DateTimeDigitized, DateTime
            for tag_id in date_tags:
                if tag_id in exif_data:
                    date_str = exif_data[tag_id]
                    try:
                        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        try:
                            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
    except Exception:
        pass
    return None

def get_image_metadata_date(file_path):
    try:
        with Image.open(file_path) as img:
            exif_date = get_exif_date(img)
            if exif_date:
                return exif_date, 'exif'
            try:
                # Use getexif() instead of deprecated _getexif()
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if isinstance(tag_name, str) and ('date' in tag_name.lower() or 'time' in tag_name.lower()):
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
    metadata_date, source = get_image_metadata_date(file_path)
    if metadata_date:
        return metadata_date, source
    try:
        filesystem_time = file_path.stat().st_mtime
        return datetime.fromtimestamp(filesystem_time), 'filesystem'
    except Exception as e:
        print(f"Virhe aikaleiman haussa {file_path}: {e}")
        return None, 'none'

def classify_images_hierarchical(source_dir, target_base_dir, db):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.jfif'}
    source_path = Path(source_dir)
    target_base_path = Path(target_base_dir)
    if not source_path.exists():
        return {"error": f"Lähdekansiota ei löydy: {source_dir}"}
    target_base_path.mkdir(parents=True, exist_ok=True)
    all_images = []
    stats = {'total': 0, 'exif': 0, 'exif_other': 0, 'filesystem': 0, 'failed': 0}
    for file_path in source_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            stats['total'] += 1
            try:
                image_date, source = get_best_available_date(file_path)
                if not image_date:
                    stats['failed'] += 1
                    continue
                if source == 'exif':
                    stats['exif'] += 1
                elif source == 'exif_other':
                    stats['exif_other'] += 1
                elif source == 'filesystem':
                    stats['filesystem'] += 1
                image_hash = get_image_hash(file_path)
                if not image_hash:
                    continue
                image_info = {'path': file_path, 'date': image_date, 'hash': image_hash, 'filename': file_path.name, 'source': source}
                all_images.append(image_info)
            except Exception as e:
                stats['failed'] += 1
    if not all_images:
        return {"error": f"Ei kuvia löytynyt kansiosta {source_dir} tai kaikissa puuttuu päivämäärä"}
    all_images.sort(key=lambda x: x['date'])
    copy_results = copy_all_images_to_hierarchical_structure(all_images, target_base_path, db)
    result = {"stats": stats, "classified": copy_results, "date_range": {"start": all_images[0]['date'].isoformat(), "end": all_images[-1]['date'].isoformat()}}
    return result

def copy_all_images_to_hierarchical_structure(all_images, target_base_path, db):
    results = {}
    LINK_MODE = os.environ.get('LINK_MODE', 'symlink').lower()
    
    print(f"Aloitetaan kuvien kopiointi {len(all_images)} kuvalle")
    print("Luodaan hierarkkinen kansiorakenne...")
    
    # Luodaan ensin pääkansiot
    main_categories = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    for category in main_categories:
        (target_base_path / category).mkdir(parents=True, exist_ok=True)
    
    total_copied = 0
    
    for image in all_images:
        date = image['date']
        year = date.year
        month = date.month
        week = get_week_number(date)
        day = date.day
        hour = date.hour
        minute = date.minute
        second = date.second
        
        # Määritellään hierarkkiset polut
        hierarchical_paths = {
            'year': target_base_path / 'years' / str(year),
            'month': target_base_path / 'months' / str(year) / f"{month:02d}",
            'week': target_base_path / 'weeks' / str(year) / f"W{week:02d}",
            'day': target_base_path / 'days' / str(year) / f"{month:02d}" / f"{day:02d}",
            'hour': target_base_path / 'hours' / str(year) / f"{month:02d}" / f"{day:02d}" / f"{hour:02d}",
            'minute': target_base_path / 'minutes' / str(year) / f"{month:02d}" / f"{day:02d}" / f"{hour:02d}" / f"{minute:02d}",
            'second': target_base_path / 'seconds' / str(year) / f"{month:02d}" / f"{day:02d}" / f"{hour:02d}" / f"{minute:02d}" / f"{second:02d}"
        }
        
        for category_type, target_dir in hierarchical_paths.items():
            try:
                # Varmistetaan että kohdekansio on olemassa
                target_dir.mkdir(parents=True, exist_ok=True)
                
                target_file = target_dir / image['filename']
                
                if not target_file.exists():
                    # Kopioi/linkitä tiedosto
                    if LINK_MODE == 'symlink':
                        try:
                            os.symlink(os.path.abspath(str(image['path'])), str(target_file))
                        except Exception as e:
                            shutil.copy2(image['path'], target_file)
                    elif LINK_MODE == 'hardlink':
                        try:
                            os.link(image['path'], target_file)
                        except Exception as e:
                            shutil.copy2(image['path'], target_file)
                    else:
                        shutil.copy2(image['path'], target_file)
                    
                    try:
                        os.utime(target_file, (image['date'].timestamp(), image['date'].timestamp()))
                    except Exception:
                        pass
                    
                    print(f"Kopioitu {category_type}: {target_file}")
                    total_copied += 1
                
                # Lisää tietokantaan
                rel_path = str(target_file.relative_to(target_base_path))
                if rel_path not in db.images:
                    time_key = f"{year}" if category_type == 'year' else \
                              f"{year}-{month:02d}" if category_type == 'month' else \
                              f"{year}-W{week:02d}" if category_type == 'week' else \
                              f"{year}-{month:02d}-{day:02d}" if category_type == 'day' else \
                              f"{year}-{month:02d}-{day:02d}-{hour:02d}" if category_type == 'hour' else \
                              f"{year}-{month:02d}-{day:02d}-{hour:02d}-{minute:02d}" if category_type == 'minute' else \
                              f"{year}-{month:02d}-{day:02d}-{hour:02d}-{minute:02d}-{second:02d}"
                    
                    db.add_image(target_file, image['date'].isoformat(), f"{category_type}_{time_key}", image['source'])
                    
            except Exception as e:
                print(f"Virhe käsiteltäessä {image['filename']} kategoriaan {category_type}: {e}")
    
    # Lasketaan tulokset
    for category in main_categories:
        category_path = target_base_path / category
        image_count = 0
        folder_count = 0
        
        # Laske kuvat ja kansiot
        for root, dirs, files in os.walk(category_path):
            folder_count += len(dirs)
            image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'))]
            image_count += len(image_files)
        
        category_type = category[:-1]  # Poista 's' lopusta: years -> year
        results[category_type] = {'folders': folder_count, 'images': image_count}
        print(f"Kategoria {category}: {image_count} kuvaa {folder_count} kansiossa")
    
    db.save_database()
    added_count = db.scan_for_images()
    if added_count > 0:
        print(f"Skannauksessa lisätty {added_count} uutta kuvaa tietokantaan")
    
    print(f"Yhteensä kopioitu {total_copied} kuvakopiota hierarkkiseen rakenteeseen")
    return results

# Vaihtoehtoinen funktio jos haluat säilyttää myös vanhan rakenteen
def copy_all_images_to_structure(all_images, target_base_path, db):
    """Vanha funktio - käytä copy_all_images_to_hierarchical_structure sen sijaan"""
    return copy_all_images_to_hierarchical_structure(all_images, target_base_path, db)
