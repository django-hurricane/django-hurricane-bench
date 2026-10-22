#!/usr/bin/env bash
set -eo pipefail

HURRICANE_VERSION="${HURRICANE_VERSION:-2.0.0rc1}"
BENCH_USERS="${BENCH_USERS:-150}"
BENCH_SPAWN_RATE="${BENCH_SPAWN_RATE:-25}"
BENCH_DURATION="${BENCH_DURATION:-45s}"
BENCH_FLAVORS="${BENCH_FLAVORS:-django-wsgi django-asgi django-asgi-async}"

echo "======================================================================"
echo " Starting Django Hurricane Benchmark Suite"
echo " Django Hurricane Version: ${HURRICANE_VERSION}"
echo " Concurrent Users:         ${BENCH_USERS}"
echo " Spawn Rate:               ${BENCH_SPAWN_RATE} users/sec"
echo " Duration per Scenario:    ${BENCH_DURATION}"
echo " Scenarios:                ${BENCH_FLAVORS}"
echo "======================================================================"

mkdir -p reports

echo "--> Building container images (HURRICANE_VERSION=${HURRICANE_VERSION})..."
docker compose build --build-arg HURRICANE_VERSION="${HURRICANE_VERSION}"

echo "--> Starting base infrastructure (PostgreSQL & Fake API)..."
docker compose up -d postgres fake-api

echo "--> Waiting for PostgreSQL and Fake API to become healthy..."
until docker compose exec postgres pg_isready -U benchuser -d benchdb > /dev/null 2>&1; do
    echo "    Waiting for PostgreSQL..."
    sleep 2
done

echo "--> Applying database migrations & seeding benchmark data..."
docker compose run --rm django-wsgi python manage.py migrate --noinput
docker compose run --rm django-wsgi python manage.py seed_db --force

for flavor in ${BENCH_FLAVORS}; do
    echo "======================================================================"
    echo " [BENCHMARK] Executing Scenario: ${flavor}"
    echo "======================================================================"

    # Start target container
    docker compose up -d "${flavor}"

    echo "--> Waiting for ${flavor} readiness probe (/health)..."
    ready=0
    for i in {1..30}; do
        if docker compose exec "${flavor}" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" > /dev/null 2>&1; then
            echo "    ${flavor} is READY (attempt ${i})"
            ready=1
            break
        fi
        sleep 1
    done

    if [ "$ready" -ne 1 ]; then
        echo "ERROR: ${flavor} failed readiness check after 30 seconds."
        docker compose logs "${flavor}"
        docker compose stop "${flavor}"
        exit 1
    fi

    # Warmup traffic (5 seconds)
    echo "--> Warming up ${flavor} (5s)..."
    docker compose run --rm -e TARGET_HOST="http://${flavor}:8000" locust \
        -f locustfile.py --headless -H "http://${flavor}:8000" \
        -u 20 -r 10 --run-time 5s > /dev/null 2>&1 || true

    # Benchmark run
    echo "--> Running Locust load test against ${flavor}..."
    docker compose run --rm -e TARGET_HOST="http://${flavor}:8000" locust \
        -f locustfile.py --headless -H "http://${flavor}:8000" \
        -u "${BENCH_USERS}" -r "${BENCH_SPAWN_RATE}" \
        --run-time "${BENCH_DURATION}" \
        --csv="/reports/${flavor}"

    echo "--> Stopping ${flavor} to prevent resource bleed..."
    docker compose stop "${flavor}"
    docker compose rm -f "${flavor}"

    echo "--> Cooling down for 5 seconds..."
    sleep 5
done

echo "======================================================================"
echo " Generating Visual Benchmark Report & Updating README.md"
echo "======================================================================"
python3 scripts/update_readme.py "${HURRICANE_VERSION}"

echo "Benchmark complete! Reports saved to ./reports and README.md updated."
