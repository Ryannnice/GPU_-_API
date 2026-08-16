#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = SCRIPT_DIR / "runtime"


@dataclass
class Gpu:
    index: int
    bus_id: str
    util: int
    memory_mib: int


@dataclass
class ComputeApp:
    gpu_index: int | None
    bus_id: str
    pid: int
    name: str
    memory_mib: int


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def parse_gpus(value: str, visible: list[int]) -> list[int]:
    if value == "all":
        return visible
    selected = [int(part.strip()) for part in value.split(",") if part.strip()]
    unknown = sorted(set(selected) - set(visible))
    if unknown:
        raise SystemExit(f"unknown GPU index: {unknown}")
    return selected


def run_nvidia_smi(args: list[str]) -> str:
    result = subprocess.run(
        ["nvidia-smi", *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def read_gpus() -> list[Gpu]:
    output = run_nvidia_smi(
        [
            "--query-gpu=index,pci.bus_id,utilization.gpu,memory.used",
            "--format=csv,noheader,nounits",
        ]
    )
    gpus: list[Gpu] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        index, bus_id, util, memory = [part.strip() for part in line.split(",")]
        gpus.append(Gpu(int(index), bus_id, int(util), int(memory)))
    return gpus


def read_compute_apps(bus_to_index: dict[str, int]) -> list[ComputeApp]:
    output = run_nvidia_smi(
        [
            "--query-compute-apps=gpu_bus_id,pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    apps: list[ComputeApp] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        bus_id, pid, name, memory = [part.strip() for part in line.split(",", 3)]
        apps.append(
            ComputeApp(
                gpu_index=bus_to_index.get(bus_id),
                bus_id=bus_id,
                pid=int(pid),
                name=name,
                memory_mib=int(memory),
            )
        )
    return apps


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def pid_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode(errors="replace").strip()


def pid_has_env(pid: int, key: str, value: str) -> bool:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return False
    prefix = f"{key}=".encode()
    for item in raw.split(b"\0"):
        if item.startswith(prefix):
            return item[len(prefix) :].decode(errors="replace") == value
    return False


def descendant_pids(root_pid: int) -> set[int]:
    children: dict[int, list[int]] = {}
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        stat_path = proc_dir / "stat"
        try:
            stat = stat_path.read_text()
        except OSError:
            continue

        # comm can contain spaces inside parentheses. The ppid is the second
        # field after the final close paren.
        try:
            pid = int(proc_dir.name)
            tail = stat.rsplit(")", 1)[1].strip().split()
            ppid = int(tail[1])
        except (IndexError, ValueError):
            continue
        children.setdefault(ppid, []).append(pid)

    owned = {root_pid}
    stack = [root_pid]
    while stack:
        pid = stack.pop()
        for child in children.get(pid, []):
            if child not in owned:
                owned.add(child)
                stack.append(child)
    return owned


def stop_process(proc: subprocess.Popen, reason: str) -> None:
    if proc.poll() is not None:
        return
    log(f"stopping owned gpu_busy pid={proc.pid}: {reason}")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        log(f"owned gpu_busy pid={proc.pid} did not exit; killing it")
        proc.kill()
        proc.wait(timeout=15)


def write_pid_file(path: Path) -> None:
    path.write_text(f"{os.getpid()}\n")


def remove_pid_file(path: Path) -> None:
    try:
        if path.read_text().strip() == str(os.getpid()):
            path.unlink()
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run gpu_busy.py only while selected GPUs are otherwise idle."
    )
    parser.add_argument(
        "--duration-sec",
        type=int,
        default=0,
        help="Run forever by default. Set a positive number to stop after N seconds.",
    )
    parser.add_argument("--interval-sec", type=float, default=5.0)
    parser.add_argument("--threshold", type=int, default=1, help="GPU util percent considered idle")
    parser.add_argument(
        "--yield-util-threshold",
        type=int,
        default=0,
        help=(
            "While gpu_busy is running, yield if GPU utilization exceeds this percent. "
            "Use 0 to disable."
        ),
    )
    parser.add_argument("--gpus", default="all", help="'all' or comma-separated GPU ids")
    parser.add_argument("--busy-python", default=sys.executable)
    parser.add_argument("--busy-script", default=str(SCRIPT_DIR / "gpu_busy.py"))
    parser.add_argument("--busy-mem-frac", type=float, default=0.02)
    parser.add_argument("--busy-matrix-size", type=int, default=4096)
    parser.add_argument("--busy-duty-cycle", type=float, default=0.02)
    parser.add_argument("--busy-period-sec", type=float, default=0.1)
    parser.add_argument("--busy-log", default=str(RUNTIME_DIR / "gpu_busy.log"))
    parser.add_argument("--busy-pid-file", default=str(RUNTIME_DIR / "gpu_busy.pid"))
    parser.add_argument("--pid-file", default=str(RUNTIME_DIR / "gpu_guard.pid"))
    args = parser.parse_args()
    if not 0 <= args.yield_util_threshold <= 100:
        raise SystemExit("--yield-util-threshold must be between 0 and 100")

    pid_file = Path(args.pid_file)
    for runtime_path in (pid_file, Path(args.busy_pid_file), Path(args.busy_log)):
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
        except ValueError:
            existing_pid = -1
        if existing_pid > 0 and process_exists(existing_pid):
            raise SystemExit(f"gpu_guard already running with pid {existing_pid}")

    write_pid_file(pid_file)

    stopping = False
    busy_proc: subprocess.Popen | None = None
    busy_gpus: set[int] = set()
    busy_log_handle = None

    def handle_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    deadline = None if args.duration_sec <= 0 else time.monotonic() + args.duration_sec
    last_status = ""
    last_heartbeat = 0.0

    try:
        visible_gpus = read_gpus()
        selected = parse_gpus(args.gpus, [gpu.index for gpu in visible_gpus])
        duration_text = "forever" if deadline is None else f"{args.duration_sec}s"
        log(
            "guard started: "
            f"duration={duration_text} interval={args.interval_sec}s "
            f"threshold={args.threshold}% yield_util_threshold={args.yield_util_threshold}% "
            f"gpus={selected}"
        )

        while not stopping and (deadline is None or time.monotonic() < deadline):
            if busy_proc is not None and busy_proc.poll() is not None:
                log(f"owned gpu_busy pid={busy_proc.pid} exited code={busy_proc.returncode}")
                busy_proc = None
                busy_gpus = set()
                if busy_log_handle is not None:
                    busy_log_handle.close()
                    busy_log_handle = None

            gpus = read_gpus()
            bus_to_index = {gpu.bus_id: gpu.index for gpu in gpus}
            selected_gpus = [gpu for gpu in gpus if gpu.index in selected]
            apps = [app for app in read_compute_apps(bus_to_index) if app.gpu_index in selected]
            owned_pids = descendant_pids(busy_proc.pid) if busy_proc is not None else set()
            owner_id = str(os.getpid())
            owned_apps = [
                app
                for app in apps
                if app.pid in owned_pids or pid_has_env(app.pid, "GPU_GUARD_OWNER", owner_id)
            ]
            external_apps = [app for app in apps if app not in owned_apps]

            # Some GPU runtimes report host PIDs that are not visible inside
            # this container. Each owned gpu_busy worker creates one context,
            # so allow one such unmatched context per owned GPU.
            if busy_proc is not None:
                for gpu_index in busy_gpus:
                    if any(app.gpu_index == gpu_index for app in owned_apps):
                        continue
                    unmapped_owned = next(
                        (
                            app
                            for app in external_apps
                            if app.gpu_index == gpu_index and not pid_cmdline(app.pid)
                        ),
                        None,
                    )
                    if unmapped_owned is not None:
                        external_apps.remove(unmapped_owned)

            if external_apps:
                summary = ", ".join(
                    f"gpu={app.gpu_index} pid={app.pid} mem={app.memory_mib}MiB"
                    for app in external_apps[:8]
                )
                status = f"external compute app detected: {summary}"
                if status != last_status or time.monotonic() - last_heartbeat >= 60:
                    log(status)
                    last_status = status
                    last_heartbeat = time.monotonic()
                if busy_proc is not None:
                    stop_process(busy_proc, "external GPU process detected")
                    busy_proc = None
                    busy_gpus = set()
                    if busy_log_handle is not None:
                        busy_log_handle.close()
                        busy_log_handle = None
                time.sleep(args.interval_sec)
                continue

            util_summary = ", ".join(f"{gpu.index}:{gpu.util}%" for gpu in selected_gpus)
            high_util_gpus = [
                gpu
                for gpu in selected_gpus
                if busy_proc is not None
                and args.yield_util_threshold > 0
                and gpu.index in busy_gpus
                and gpu.util > args.yield_util_threshold
            ]
            if high_util_gpus:
                summary = ", ".join(f"{gpu.index}:{gpu.util}%" for gpu in high_util_gpus)
                status = f"high GPU utilization detected: {summary}"
                if status != last_status or time.monotonic() - last_heartbeat >= 60:
                    log(status)
                    last_status = status
                    last_heartbeat = time.monotonic()
                stop_process(
                    busy_proc,
                    f"GPU utilization exceeded {args.yield_util_threshold}%",
                )
                busy_proc = None
                busy_gpus = set()
                if busy_log_handle is not None:
                    busy_log_handle.close()
                    busy_log_handle = None
                time.sleep(args.interval_sec)
                continue

            idle_gpus = [gpu for gpu in selected_gpus if gpu.util <= args.threshold]
            desired_busy_gpus = busy_gpus | {gpu.index for gpu in idle_gpus}

            if busy_proc is not None and desired_busy_gpus != busy_gpus:
                stop_process(
                    busy_proc,
                    "selected idle GPU set changed "
                    f"from {sorted(busy_gpus)} to {sorted(desired_busy_gpus)}",
                )
                busy_proc = None
                busy_gpus = set()
                if busy_log_handle is not None:
                    busy_log_handle.close()
                    busy_log_handle = None

            if busy_proc is None and desired_busy_gpus:
                busy_gpus = set(desired_busy_gpus)
                idle_ids = ",".join(str(gpu) for gpu in sorted(busy_gpus))
                busy_log_handle = open(args.busy_log, "a", buffering=1)
                cmd = [
                    args.busy_python,
                    args.busy_script,
                    "--gpus",
                    idle_ids,
                    "--mem-frac",
                    str(args.busy_mem_frac),
                    "--matrix-size",
                    str(args.busy_matrix_size),
                    "--duty-cycle",
                    str(args.busy_duty_cycle),
                    "--period-sec",
                    str(args.busy_period_sec),
                ]
                log(
                    "starting owned gpu_busy: "
                    f"gpus={idle_ids} util={util_summary} mem_frac={args.busy_mem_frac} "
                    f"duty_cycle={args.busy_duty_cycle}"
                )
                env = os.environ.copy()
                env["GPU_GUARD_OWNER"] = str(os.getpid())
                busy_proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=busy_log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    text=True,
                    env=env,
                )
                Path(args.busy_pid_file).write_text(f"{busy_proc.pid}\n")
            else:
                status = (
                    f"owned gpu_busy pid={busy_proc.pid} running gpus={sorted(busy_gpus)}; "
                    f"util={util_summary}"
                    if busy_proc is not None
                    else f"all selected GPUs above threshold; util={util_summary}"
                )
                if status != last_status or time.monotonic() - last_heartbeat >= 60:
                    log(status)
                    last_status = status
                    last_heartbeat = time.monotonic()

            time.sleep(args.interval_sec)

    finally:
        if busy_proc is not None:
            stop_process(busy_proc, "guard exiting")
        if busy_log_handle is not None:
            busy_log_handle.close()
        remove_pid_file(pid_file)
        log("guard stopped")


if __name__ == "__main__":
    main()
