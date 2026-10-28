#!/usr/bin/env bash
set -eo pipefail

HURRICANE_VERSION="${HURRICANE_VERSION:-2.0.0rc2}"
BENCH_USERS="${BENCH_USERS:-150}"
BENCH_SPAWN_RATE="${BENCH_SPAWN_RATE:-25}"
BENCH_DURATION="${BENCH_DURATION:-45s}"
BENCH_FLAVORS="${BENCH_FLAVORS:-django-asgi-sync django-asgi django-asgi-auto django-asgi-async}"
BENCH_WORKLOADS="${BENCH_WORKLOADS:-all}"

if [ "${BENCH_WORKLOADS}" = "all" ]; then
    BENCH_WORKLOADS="mixed baseline_valid security_flood gateway_aggregate catalog_render external_fetch items_get items_post catalog_search auth"
fi

echo "======================================================================"
echo " Starting Django Hurricane Benchmark Suite (Pure ASGI)"
echo " Django Hurricane Version: ${HURRICANE_VERSION}"
echo " Concurrent Users:         ${BENCH_USERS}"
echo " Spawn Rate:               ${BENCH_SPAWN_RATE} users/sec"
echo " Duration per Scenario:    ${BENCH_DURATION}"
echo " Scenarios:                ${BENCH_FLAVORS}"
echo " Workloads:                ${BENCH_WORKLOADS}"
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
docker compose run --rm django-asgi-sync python manage.py migrate --noinput
docker compose run --rm django-asgi-sync python manage.py seed_db --force

for flavor in ${BENCH_FLAVORS}; do
    echo "======================================================================"
    echo " [BENCHMARK] Executing Scenario: ${flavor}"
    echo "======================================================================"

    echo "--> Resetting and seeding database for ${flavor} to guarantee clean initial state..."
    docker compose run --rm django-asgi-sync python manage.py seed_db --force

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
    docker compose run --rm -e TARGET_HOST="http://${flavor}:8000" -e USE_STEP_LOAD="false" locust \
        -f locustfile.py --headless -H "http://${flavor}:8000" \
        -u 20 -r 10 --run-time 5s --exit-code-on-error 0 > /dev/null 2>&1 || true

    # Benchmark runs (mixed, security_flood, baseline_valid, and/or isolated workloads)
    for workload in ${BENCH_WORKLOADS}; do
        # If testing multiple workloads, ensure clean database state before each workload
        if [ "${workload}" != "mixed" ]; then
            echo "--> [Workload: ${workload}] Resetting database state..."
            docker compose run --rm django-asgi-sync python manage.py seed_db --force > /dev/null 2>&1 || true
        fi

        echo "--> [Workload: ${workload}] Running Locust load test against ${flavor}..."
        csv_prefix="/reports/${flavor}"
        if [ "${workload}" != "mixed" ]; then
            csv_prefix="/reports/${flavor}_${workload}"
        fi

        docker compose run --rm \
            -e TARGET_HOST="http://${flavor}:8000" \
            -e BENCH_USERS="${BENCH_USERS}" \
            -e BENCH_DURATION="${BENCH_DURATION}" \
            -e BENCH_WORKLOAD="${workload}" \
            locust \
            -f locustfile.py --headless -H "http://${flavor}:8000" \
            -u "${BENCH_USERS}" -r "${BENCH_SPAWN_RATE}" \
            --run-time "${BENCH_DURATION}" \
            --exit-code-on-error 0 \
            --csv="${csv_prefix}"
    done

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
