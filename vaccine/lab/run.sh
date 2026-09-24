#!/usr/bin/env bash
# Lance le lab sur le moteur demande.
#
#   ./run.sh            -> sqlite (defaut)
#   ./run.sh mysql      -> demarre le conteneur MySQL puis le lab
#
# Ctrl-C pour arreter. Le conteneur MySQL, lui, continue de tourner.

set -e
cd "$(dirname "$0")"
ENGINE="${1:-sqlite}"

# sudo seulement si le socket docker n'est pas accessible directement
DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

# tue un lab deja en cours pour liberer le port 5000
pkill -f "venv/bin/python app.py" 2>/dev/null || true

if [ "$ENGINE" = "mysql" ]; then
    # recree le conteneur s'il manque, ou s'il n'publie pas le port 3306
    if ! $DOCKER inspect -f '{{.HostConfig.PortBindings}}' vaccine-mysql 2>/dev/null | grep -q 3306; then
        echo "-> (re)creation du conteneur vaccine-mysql"
        $DOCKER rm -f vaccine-mysql >/dev/null 2>&1 || true
        $DOCKER run -d --name vaccine-mysql -p 3306:3306 \
            -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=shop mysql:8 >/dev/null
    else
        $DOCKER start vaccine-mysql >/dev/null
    fi

    printf -- "-> attente de mysql"
    for _ in $(seq 45); do
        if $DOCKER exec vaccine-mysql mysql -uroot -proot -e "SELECT 1" shop >/dev/null 2>&1; then
            echo " pret"
            break
        fi
        printf "."
        sleep 2
    done
fi

echo "-> lab en $ENGINE sur http://127.0.0.1:5000"
VACCINE_DB="$ENGINE" exec ./venv/bin/python app.py
