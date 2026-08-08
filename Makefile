SHELL := /bin/sh

.PHONY: check build e2e smoke verify exercise-create exercise-01 exercise-02 \
	exercise-03 exercise-04 exercise-05 exercise-check exercise-build \
	exercise-e2e exercise-smoke exercise-verify clean

check:
	pnpm check

build:
	pnpm build

e2e:
	pnpm build
	pnpm test:e2e

smoke:
	pnpm build
	pnpm smoke

verify:
	pnpm verify

exercise-create:
	pnpm exercise:create

exercise-01:
	pnpm exercise:verify:01

exercise-02:
	pnpm exercise:verify:02

exercise-03:
	pnpm exercise:verify:03

exercise-04:
	pnpm exercise:verify:04

exercise-05:
	pnpm exercise:verify:05

exercise-check:
	pnpm exercise:check

exercise-build:
	pnpm exercise:build

exercise-e2e:
	pnpm exercise:test:e2e

exercise-smoke:
	pnpm exercise:smoke

exercise-verify:
	pnpm exercise:verify

clean:
	pnpm clean
