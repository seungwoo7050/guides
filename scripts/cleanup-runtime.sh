#!/bin/sh
set -u

usage()
{
    echo "사용법: $0 {check|clean|assert-clean} RUN_ID" >&2
    exit 2
}

[ "$#" -eq 2 ] || usage
mode=$1
run_id=$2
case "$mode" in
    check|clean|assert-clean) ;;
    *) usage ;;
esac
case "$run_id" in
    ''|*[!a-z0-9-]*)
        echo "안전하지 않은 RUN_ID입니다: $run_id" >&2
        exit 2
        ;;
esac

prefix="web-infra-$run_id-"
builder="${prefix}builder"
builder_container="buildx_buildkit_${builder}0"
builder_volume="buildx_buildkit_${builder}0_state"
found=0

projects()
{
    for exercise in 03 04 05 06
    do
        for implementation in skeleton reference
        do
            printf '%s\n' "${prefix}exercise${exercise}-${implementation}"
        done
    done
    for scenario in \
        wrong-db-host \
        wrong-db-password \
        missing-secret \
        wrong-fcgi-port \
        broken-healthcheck \
        data-loss
    do
        printf '%s\n' "${prefix}exercise07-${scenario}"
    done
}

report_runtime()
{
    for implementation in skeleton reference
    do
        container="${prefix}exercise02-${implementation}"
        image="${prefix}exercise02-${implementation}:verify"
        if docker container inspect "$container" >/dev/null 2>&1
        then
            printf '남은 container: %s\n' "$container" >&2
            found=1
        fi
        if docker image inspect "$image" >/dev/null 2>&1
        then
            printf '남은 image: %s\n' "$image" >&2
            found=1
        fi
    done

    projects | while IFS= read -r project
    do
        containers=$(docker ps -aq --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
        networks=$(docker network ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
        volumes=$(docker volume ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
        [ -z "$containers" ] || printf '남은 Compose container (%s): %s\n' "$project" "$containers" >&2
        [ -z "$networks" ] || printf '남은 Compose network (%s): %s\n' "$project" "$networks" >&2
        [ -z "$volumes" ] || printf '남은 Compose volume (%s): %s\n' "$project" "$volumes" >&2
    done

    # Pipeline subshell의 found 값에 의존하지 않고 별도의 존재 검사를 수행합니다.
    for project in $(projects)
    do
        if [ -n "$(docker ps -aq --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)" ] || \
           [ -n "$(docker network ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)" ] || \
           [ -n "$(docker volume ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)" ]
        then
            found=1
        fi
    done

    docker image ls --format '{{.Repository}} {{.ID}}' 2>/dev/null |
    while IFS=' ' read -r repository image_id
    do
        case "$repository" in
            "$prefix"*) printf '남은 run image: %s (%s)\n' "$repository" "$image_id" >&2 ;;
        esac
    done
    if docker image ls --format '{{.Repository}}' 2>/dev/null | grep -q "^$prefix"
    then
        found=1
    fi

    if [ "$mode" = assert-clean ]
    then
        if docker buildx inspect "$builder" >/dev/null 2>&1
        then
            printf '남은 Buildx builder: %s\n' "$builder" >&2
            found=1
        fi
        if docker container inspect "$builder_container" >/dev/null 2>&1
        then
            printf '남은 BuildKit container: %s\n' "$builder_container" >&2
            found=1
        fi
        if docker volume inspect "$builder_volume" >/dev/null 2>&1
        then
            printf '남은 BuildKit cache volume: %s\n' "$builder_volume" >&2
            found=1
        fi
    fi

    [ "$found" -eq 0 ]
}

remove_project()
{
    project=$1

    for id in $(docker ps -aq --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
    do
        docker rm -f "$id" >/dev/null 2>&1 || true
    done
    for id in $(docker network ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
    do
        docker network rm "$id" >/dev/null 2>&1 || true
    done
    for name in $(docker volume ls -q --filter "label=com.docker.compose.project=$project" 2>/dev/null || true)
    do
        docker volume rm -f "$name" >/dev/null 2>&1 || true
    done
}

clean_runtime()
{
    for implementation in skeleton reference
    do
        docker rm -f "${prefix}exercise02-${implementation}" >/dev/null 2>&1 || true
        docker image rm -f "${prefix}exercise02-${implementation}:verify" >/dev/null 2>&1 || true
    done

    for project in $(projects)
    do
        remove_project "$project"
    done

    docker image ls --format '{{.Repository}} {{.ID}}' 2>/dev/null |
    while IFS=' ' read -r repository image_id
    do
        case "$repository" in
            "$prefix"*) docker image rm -f "$image_id" >/dev/null 2>&1 || true ;;
        esac
    done

    docker buildx rm -f "$builder" >/dev/null 2>&1 || true
    docker rm -f "$builder_container" >/dev/null 2>&1 || true
    docker volume rm -f "$builder_volume" >/dev/null 2>&1 || true
}

case "$mode" in
    check|assert-clean)
        if report_runtime
        then
            exit 0
        fi
        exit 1
        ;;
    clean)
        clean_runtime
        exit 0
        ;;
esac
