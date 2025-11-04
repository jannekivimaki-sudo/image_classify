import os
import json
from datetime import datetime, timedelta
from pathlib import Path

class ImageDatabase:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.db_file = self.base_path / 'image_database.json'
        self.images = self.load_database()
    
    def load_database(self):
        if self.db_file.exists():
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Virhe tietokannan lataamisessa: {e}")
                return {}
        return {}
    
    def save_database(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.images, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Virhe tietokannan tallennuksessa: {e}")
    
    def add_image(self, image_path, timestamp, category, source='filesystem'):
        try:
            # Käytä suhteellista polkua
            if isinstance(image_path, Path):
                rel_path = str(image_path.relative_to(self.base_path))
            else:
                rel_path = str(Path(image_path).relative_to(self.base_path))
            
            self.images[rel_path] = {
                'timestamp': timestamp,
                'category': category,
                'source': source,
                'filename': Path(image_path).name,
                'added': datetime.now().isoformat()
            }
            print(f"Lisätty tietokantaan: {rel_path} - {category}")
        except Exception as e:
            print(f"Virhe kuvan lisäämisessä tietokantaan {image_path}: {e}")
    
    def scan_for_images(self):
        """Skannaa kansion kuvat ja lisää ne tietokantaan jos puuttuvat"""
        print("Skannataan kuvia kansiosta...")
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        added_count = 0
        
        for file_path in self.base_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                try:
                    rel_path = str(file_path.relative_to(self.base_path))
                    
                    # Tarkista onko kuva jo tietokannassa
                    if rel_path not in self.images:
                        # Päätä kategoria tiedostopolun perusteella
                        category = self.determine_category_from_path(rel_path)
                        # Käytä tiedoston muokkausaikaa
                        timestamp = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        
                        self.images[rel_path] = {
                            'timestamp': timestamp,
                            'category': category,
                            'source': 'filesystem',
                            'filename': file_path.name,
                            'added': datetime.now().isoformat()
                        }
                        added_count += 1
                        print(f"Lisätty skannauksessa: {rel_path} - {category}")
                except Exception as e:
                    print(f"Virhe skannatessa tiedostoa {file_path}: {e}")
        
        if added_count > 0:
            self.save_database()
            print(f"Lisätty {added_count} uutta kuvaa tietokantaan")
        
        return added_count
    
    def determine_category_from_path(self, rel_path):
        """Päätä kategoria tiedostopolun perusteella"""
        path_str = str(rel_path)
        
        if '/01_vuodet/' in path_str:
            parts = path_str.split('/01_vuodet/')[1].split('/')
            year = parts[0]
            return f"year_{year}"
        elif '/02_kuukaudet/' in path_str:
            parts = path_str.split('/02_kuukaudet/')[1].split('/')
            month = parts[0]
            return f"month_{month}"
        elif '/03_viikot/' in path_str:
            parts = path_str.split('/03_viikot/')[1].split('/')
            week = parts[0]
            return f"week_{week}"
        elif '/04_paivat/' in path_str:
            parts = path_str.split('/04_paivat/')[1].split('/')
            day = parts[0]
            return f"day_{day}"
        elif '/05_tunnit/' in path_str:
            parts = path_str.split('/05_tunnit/')[1].split('/')
            hour = parts[0]
            return f"hour_{hour}"
        elif '/06_minuutit/' in path_str:
            parts = path_str.split('/06_minuutit/')[1].split('/')
            minute = parts[0]
            return f"minute_{minute}"
        elif '/07_sekunnit/' in path_str:
            parts = path_str.split('/07_sekunnit/')[1].split('/')
            second = parts[0]
            return f"second_{second}"
        else:
            return "unknown"
    
    def get_images_by_date_range(self, start_date, end_date):
        try:
            # Muunna päivämäärät datetime-objekteiksi
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
            else:
                start_dt = None
                
            if end_date:
                # Lisää yksi päivä, jotta saadaan koko päivä mukaan
                end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
            else:
                end_dt = None
            
            print(f"Haetaan kuvia aikaväliltä: {start_dt} - {end_dt}")
            
            matching_images = []
            seen_filenames = set()  # Estä duplikaatit
            
            for rel_path, info in self.images.items():
                try:
                    # Muunna timestamp datetime-objektiksi
                    if isinstance(info['timestamp'], str):
                        img_dt = datetime.fromisoformat(info['timestamp'])
                    else:
                        img_dt = info['timestamp']
                    
                    # Tarkista aikaväli
                    if start_dt and img_dt < start_dt:
                        continue
                    if end_dt and img_dt >= end_dt:  # Huomaa >= koska lisäsimme yhden päivän
                        continue
                    
                    # Tarkista että kuva on olemassa
                    full_path = self.base_path / rel_path
                    if not full_path.exists():
                        print(f"Kuvaa ei löydy: {full_path}")
                        continue
                    
                    # Estä duplikaatit samalla tiedostonimellä
                    if info['filename'] in seen_filenames:
                        print(f"Ohitetaan duplikaatti: {info['filename']}")
                        continue
                    
                    seen_filenames.add(info['filename'])
                    
                    matching_images.append({
                        'path': rel_path,
                        'full_path': str(full_path),
                        'timestamp': info['timestamp'],
                        'category': info['category'],
                        'filename': info['filename'],
                        'date_display': img_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'date_obj': img_dt  # Lisätään datetime-objekti helpompaa järjestämistä varten
                    })
                except Exception as e:
                    print(f"Virhe käsiteltäessä kuvaa {rel_path}: {e}")
                    continue
            
            # Järjestä aikajärjestykseen
            matching_images.sort(key=lambda x: x['date_obj'] if 'date_obj' in x else x['timestamp'], reverse=True)
            print(f"Haettu {len(matching_images)} uniikkia kuvaa aikavälillä {start_date} - {end_date}")
            
            # Debug-tulostus ensimmäisistä kuvista
            if matching_images:
                print(f"Ensimmäiset 3 uniikkia kuvaa:")
                for img in matching_images[:3]:
                    print(f"  - {img['filename']}: {img['date_display']}")
            
            return matching_images
        except Exception as e:
            print(f"Virhe kuvien haussa: {e}")
            return []
    
    def get_unique_images_by_date_range(self, start_date, end_date):
        """Hae kuvat aikavälin perusteella ilman duplikaatteja (tarkempi versio)"""
        try:
            images = self.get_images_by_date_range(start_date, end_date)
            
            # Käytä tarkempaa duplikaattien poistoa
            unique_images = []
            seen_combinations = set()
            
            for image in images:
                # Luo uniikki avain tiedostonimelle ja päivämäärälle
                unique_key = f"{image['filename']}_{image['date_display'][:10]}"  # filename + päivämäärä
                
                if unique_key not in seen_combinations:
                    seen_combinations.add(unique_key)
                    unique_images.append(image)
                else:
                    print(f"Poistetaan duplikaatti: {image['filename']} ({image['date_display']})")
            
            print(f"Palautetaan {len(unique_images)} uniikkia kuvaa (alkuperäisesti {len(images)})")
            return unique_images
        except Exception as e:
            print(f"Virhe uniikkien kuvien haussa: {e}")
            return []
    
    def get_categories(self):
        try:
            categories = set()
            for info in self.images.values():
                categories.add(info['category'])
            return sorted(categories)
        except Exception as e:
            print(f"Virhe kategorioiden haussa: {e}")
            return []
    
    def get_date_range(self):
        try:
            if not self.images:
                return None, None
            
            timestamps = []
            for info in self.images.values():
                try:
                    if isinstance(info['timestamp'], str):
                        ts = datetime.fromisoformat(info['timestamp'])
                    else:
                        ts = info['timestamp']
                    timestamps.append(ts)
                except Exception:
                    continue
            
            if not timestamps:
                return None, None
                
            return min(timestamps), max(timestamps)
        except Exception as e:
            print(f"Virhe aikavälin haussa: {e}")
            return None, None
