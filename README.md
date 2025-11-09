# Image Classify

Automaattinen kuvien luokittelu- ja selaujärjestelmä.

## Ominaisuudet

- **Automaattinen luokittelu taustalla**: Kuvat luokitellaan automaattisesti kun ne saapuvat `/data/source` kansioon
- **Web-käyttöliittymä**: Selaa ja vertaile kuvia ajassa
- **Hierarkkinen organisointi**: Kuvat järjestetään vuosien, kuukausien, viikkojen, päivien, tuntien, minuuttien ja sekuntien mukaan
- **RTSP-tuki**: Katso kamerastreameja suoraan käyttöliittymässä
- **Timelapse**: Luo aikavälikatselu valitusta ajanjaksosta

## Käynnistys

### Docker Compose

```bash
docker-compose up -d
```

Tämä käynnistää:
1. **Automaattisen luokittelupalvelun** - Valvoo `/data/source` kansiota ja luokittelee kuvat automaattisesti
2. **Web-käyttöliittymän** - Käytettävissä osoitteessa http://localhost:5000
3. **SFTP-palvelimen** - Vastaanottaa kuvia kamerasta portissa 2222

## Kuinka se toimii

### Automaattinen luokittelu

Kun kontti käynnistyy:
1. Palvelu suorittaa ensimmäisen skannauksen `/data/source` kansiossa oleville kuville
2. Watchdog-kirjasto alkaa valvoa uusia tiedostoja
3. Kun uusi kuva ilmestyy, se luokitellaan automaattisesti
4. Lisäksi suoritetaan säännöllinen skannaus 60 sekunnin välein

Luokitteluperusteet:
- **EXIF-metadata**: Ensisijaisesti käytetään kuvan EXIF-tietoja
- **Tiedostojärjestelmä**: Jos EXIF puuttuu, käytetään tiedoston aikaleimaa

### Hierarkkinen rakenne

Kuvat tallennetaan `/data/classified` kansioon seuraavasti:
```
/data/classified/
├── years/2024/
├── months/2024/11/
├── weeks/2024/W45/
├── days/2024/11/09/
├── hours/2024/11/09/12/
├── minutes/2024/11/09/12/30/
└── seconds/2024/11/09/12/30/45/
```

## Kansiorakenne

- `/data/source` - Lähdekansio uusille kuville
- `/data/classified` - Luokitellut kuvat hierarkkisessa rakenteessa
- `/data/static` - Staattiset tiedostot (HLS-streamit)

## Ympäristömuuttujat

- `FLASK_ENV` - Flask-ympäristö (production/development)
- `LINK_MODE` - Tiedostojen linkitystapa (symlink/hardlink/copy)
- `TZ` - Aikavyöhyke (esim. Europe/Helsinki)
- `PYTHONUNBUFFERED` - Python-tulostuksen puskurointi pois päältä

## Palvelut

### Automaattinen luokittelupalvelu (auto_classify_service.py)

Taustaprosessi joka:
- Valvoo `/data/source` kansiota watchdog-kirjastolla
- Luokittelee kuvat heti kun ne ilmestyvät
- Suorittaa säännöllisiä skannauksia varmuuden vuoksi
- Logittaa kaikki toiminnot

### Web-käyttöliittymä (web_interface.py)

Flask-sovellus joka tarjoaa:
- Kuvien selauksen aikavälillä
- Hierarkkisen navigoinnin kansiorakenteessa
- Kuvien vertailun
- Timelapse-toiminnon
- RTSP-streamien katselun

## Kehitys

### Vaatimukset

- Python 3.11+
- Docker & Docker Compose
- FFmpeg (RTSP-toiminnallisuutta varten)

### Riippuvuudet

```
Flask==2.3.3
Pillow==10.0.1
Werkzeug==2.3.7
watchdog==3.0.0
```

## Lokit

Palvelun lokit näet komennolla:
```bash
docker-compose logs -f image-classifier
```

Automaattisen luokittelun lokit:
```bash
docker-compose logs -f image-classifier | grep "auto_classify"
```
