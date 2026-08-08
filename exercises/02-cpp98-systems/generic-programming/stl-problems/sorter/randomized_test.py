import random, subprocess, sys
binary = sys.argv[1]
random.seed(42)
for n in range(1, 80):
    for _ in range(5):
        values = [random.randint(0, 500) for _ in range(n)]
        out = subprocess.check_output(
            [binary] + [str(v) for v in values],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        line = next(x for x in out.splitlines() if x.startswith('정렬 후:'))
        got = [int(x) for x in line.split(':', 1)[1].split()]
        if got != sorted(values):
            raise SystemExit(f'정렬 결과가 다릅니다: {values} -> {got}')
print('sorter 고정 시드 무작위 검사: 통과')
