# image_classify

## Kuvien luokittelu- ja katselusovellus

Tämä sovellus luokittelee kuvat automaattisesti aikaleiman perusteella hierarkkiseen kansiorakenteeseen ja tarjoaa web-käyttöliittymän niiden selaamiseen ja vertailuun.

## Turvallisuusnäkökohdat

⚠️ **TÄRKEÄÄ - Turvallisuus:**

1. **Vaihda oletussalasanat**: Kopioi `.env.example` tiedostoksi `.env` ja päivitä SFTP-salasana:
   ```bash
   cp .env.example .env
   # Muokkaa .env tiedostoa ja vaihda salasana
   ```

2. **Suojaa SFTP-palvelu**: SFTP-palvelu on oletuksena portissa 2222. Käytä palomuuria rajoittamaan pääsy vain luotetuista IP-osoitteista.

3. **HTTPS suositeltu**: Tuotantokäytössä asenna sovellus käänteisen välityspalvelimen (nginx/Apache) taakse HTTPS:llä.

4. **Säännölliset päivitykset**: Pidä Docker-kuvat ja riippuvuudet ajan tasalla turvallisuuspäivitysten varalta.

## Asennus ja käyttö

### Docker Compose (suositeltu)

```bash
# Kopioi ympäristömuuttujat
cp .env.example .env

# Muokkaa .env tiedostoa ja vaihda salasanat
nano .env

# Käynnistä palvelut
docker-compose up -d
```

Sovellus on nyt saatavilla osoitteessa: http://localhost:5000

### SFTP-lataus

Lataa kuvia SFTP:n kautta:
```bash
sftp -P 2222 camera@localhost
# Käytä .env tiedostossa määriteltyä salasanaa
```

## Ominaisuudet

- Automaattinen kuvien luokittelu EXIF-metatietojen perusteella
- Hierarkkinen selaus (vuosi, kuukausi, viikko, päivä, tunti, minuutti, sekunti)
- Kuvavertailu (ennen/jälkeen)
- Timelapse-toisto
- RTSP-streamien tuki (valinnainen)
- Kameran tunnistus tiedostonimestä

## Lisenssi

Katso LICENSE-tiedosto.
