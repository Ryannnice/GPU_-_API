#!/usr/bin/env python3
import argparse
import os
import signal
import time
from multiprocessing import get_context

import torch


def parse_gpus(value: str) -> list[int]:
    if value == "all":
        return list(range(torch.cuda.device_count()))
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def worker(
    gpu: int,
    mem_frac: float,
    matrix_size: int,
    dtype_name: str,
    duty_cycle: float,
    period_sec: float,
) -> None:
    torch.cuda.set_device(gpu)
    device = torch.device(f"cuda:{gpu}")
    dtype = getattr(torch, dtype_name)
    stop = False

    def handle_stop(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    props = torch.cuda.get_device_properties(device)
    total = props.total_memory
    target = int(total * mem_frac)
    elem_size = torch.empty((), dtype=dtype, device=device).element_size()

    # Three matrices are used in the hot path. Extra 1-D chunks hold memory so
    # the card stays visibly occupied without making the GEMM dimensions huge.
    matrix_bytes = 3 * matrix_size * matrix_size * elem_size
    filler_bytes = max(0, target - matrix_bytes)
    filler_elems = filler_bytes // elem_size

    torch.manual_seed(1000 + gpu)
    a = torch.randn((matrix_size, matrix_size), device=device, dtype=dtype)
    b = torch.randn((matrix_size, matrix_size), device=device, dtype=dtype)
    c = torch.empty((matrix_size, matrix_size), device=device, dtype=dtype)
    filler = None
    if filler_elems:
        filler = torch.empty((filler_elems,), device=device, dtype=dtype)
        filler.fill_(0.125)

    torch.cuda.synchronize(device)
    print(
        f"gpu={gpu} pid={os.getpid()} target_mem={target / 1024**3:.1f}GiB "
        f"matrix={matrix_size} dtype={dtype_name} duty_cycle={duty_cycle:g}",
        flush=True,
    )

    i = 0
    while not stop:
        period_start = time.monotonic()
        active_until = period_start + period_sec * duty_cycle

        while not stop and (duty_cycle >= 1.0 or time.monotonic() < active_until):
            torch.matmul(a, b, out=c)
            a, c = c, a
            if duty_cycle < 1.0:
                torch.cuda.synchronize(device)
            if filler is not None and i % 100 == 0:
                filler.mul_(1.000001)
            if i % 200 == 0:
                torch.cuda.synchronize(device)
                print(f"gpu={gpu} iter={i}", flush=True)
            i += 1

            if duty_cycle >= 1.0:
                break

        if duty_cycle < 1.0:
            torch.cuda.synchronize(device)
            sleep_sec = period_start + period_sec - time.monotonic()
            if sleep_sec > 0:
                time.sleep(sleep_sec)

    torch.cuda.synchronize(device)
    print(f"gpu={gpu} stopping", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpus", default="all", help="'all' or comma-separated GPU ids")
    parser.add_argument("--mem-frac", type=float, default=0.82)
    parser.add_argument("--matrix-size", type=int, default=8192)
    parser.add_argument("--dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--duty-cycle", type=float, default=1.0)
    parser.add_argument("--period-sec", type=float, default=1.0)
    args = parser.parse_args()
    if not 0.0 < args.duty_cycle <= 1.0:
        raise SystemExit("--duty-cycle must be in (0, 1]")
    if args.period_sec <= 0:
        raise SystemExit("--period-sec must be positive")

    gpus = parse_gpus(args.gpus)
    if not gpus:
        raise SystemExit("no GPUs selected")

    ctx = get_context("spawn")
    processes = []
    for gpu in gpus:
        proc = ctx.Process(
            target=worker,
            args=(gpu, args.mem_frac, args.matrix_size, args.dtype, args.duty_cycle, args.period_sec),
        )
        proc.start()
        processes.append(proc)

    def stop_children() -> None:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
        for proc in processes:
            proc.join(timeout=10)
        for proc in processes:
            if proc.is_alive():
                proc.kill()
                proc.join()

    def handle_parent_stop(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_parent_stop)
    signal.signal(signal.SIGINT, handle_parent_stop)

    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        stop_children()


if __name__ == "__main__":
    main()
