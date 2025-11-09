#!/bin/bash
# Käynnistä molemmat palvelut
# - Automaattinen kuvien luokittelupalvelu taustalla
# - Web-käyttöliittymä etualalla

echo "=================================================="
echo "Käynnistetään kuvien luokittelupalvelut"
echo "=================================================="

# Käynnistä automaattinen luokittelupalvelu taustalle
echo "Käynnistetään automaattinen luokittelupalvelu..."
python3 /app/auto_classify_service.py &
CLASSIFIER_PID=$!
echo "Luokittelupalvelu käynnistetty (PID: $CLASSIFIER_PID)"

# Odota hetki että palvelu käynnistyy
sleep 2

# Käynnistä web-käyttöliittymä etualalle
echo "Käynnistetään web-käyttöliittymä..."
python3 /app/web_interface.py &
WEB_PID=$!
echo "Web-käyttöliittymä käynnistetty (PID: $WEB_PID)"

# Odota että molemmat prosessit ovat käynnissä
echo "=================================================="
echo "Molemmat palvelut käynnissä:"
echo "  - Automaattinen luokittelu (PID: $CLASSIFIER_PID)"
echo "  - Web-käyttöliittymä (PID: $WEB_PID)"
echo "=================================================="

# Funktio clean shutdown
cleanup() {
    echo ""
    echo "Pysäytetään palvelut..."
    kill $CLASSIFIER_PID 2>/dev/null
    kill $WEB_PID 2>/dev/null
    echo "Palvelut pysäytetty"
    exit 0
}

# Aseta trap keskeytyssignaaleille
trap cleanup SIGTERM SIGINT

# Odota jompikumpi prosessi loppumaan
wait -n

# Jos jompikumpi prosessi loppuu, lopeta molemmat
echo "Jokin palvelu loppui, pysäytetään kaikki..."
cleanup
