"""
SiteSync AI — GPU / Hardware Detection Utility

Dynamically detects available compute resources at runtime.
Works on any machine: no GPU, any NVIDIA GPU (from GTX 1060 to H200).
sentence-transformers and ChromaDB automatically pick the best device.

Usage:
    from sitesync.utils.hardware import get_device_info, get_embedding_device
    info = get_device_info()
    device = get_embedding_device()
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class DeviceInfo:
    """Hardware profile for the current machine."""
    has_gpu: bool = False
    device: Literal["cuda", "cpu", "mps"] = "cpu"
    gpu_count: int = 0
    gpus: list[dict] = field(default_factory=list)
    # e.g. [{"name": "NVIDIA H200", "vram_gb": 141, "cuda_cores": 16896, "compute": "9.0"}]
    recommended_batch_size: int = 32
    recommended_workers: int = 1

    def summary(self) -> str:
        if not self.has_gpu:
            return f"CPU-only mode (batch={self.recommended_batch_size})"
        names = ", ".join(g["name"] for g in self.gpus)
        vrам = ", ".join(f"{g['vram_gb']:.1f}GB" for g in self.gpus)
        return f"GPU: {names} | VRAM: {vrам} | batch={self.recommended_batch_size}"


_cached: Optional[DeviceInfo] = None


def get_device_info(force_refresh: bool = False) -> DeviceInfo:
    """
    Detect available compute resources. Result is cached after first call.

    Heuristics for batch size:
        VRAM >= 80GB  (H100/H200)  → batch 256
        VRAM >= 40GB  (A100/A6000) → batch 128
        VRAM >= 16GB  (RTX 4090/A4000) → batch 64
        VRAM >= 8GB   (RTX 3070+)  → batch 32
        VRAM < 8GB    (small GPU)  → batch 16
        CPU only                   → batch 32 (sentence-transformers is threaded)
    """
    global _cached
    if _cached is not None and not force_refresh:
        return _cached

    info = DeviceInfo()

    try:
        import torch

        if torch.cuda.is_available():
            info.has_gpu = True
            info.device = "cuda"
            info.gpu_count = torch.cuda.device_count()

            total_vram = 0.0
            for i in range(info.gpu_count):
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / (1024 ** 3)
                total_vram += vram_gb
                info.gpus.append({
                    "index": i,
                    "name": props.name,
                    "vram_gb": round(vram_gb, 1),
                    "cuda_cores": props.multi_processor_count * _sm_to_cores(props.major, props.minor),
                    "compute": f"{props.major}.{props.minor}",
                    "multi_processors": props.multi_processor_count,
                })

            # Batch size heuristic based on TOTAL VRAM across all GPUs
            avg_vram = total_vram / max(info.gpu_count, 1)
            if avg_vram >= 80:
                info.recommended_batch_size = 256
            elif avg_vram >= 40:
                info.recommended_batch_size = 128
            elif avg_vram >= 16:
                info.recommended_batch_size = 64
            elif avg_vram >= 8:
                info.recommended_batch_size = 32
            else:
                info.recommended_batch_size = 16

            info.recommended_workers = info.gpu_count

        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # Apple Silicon
            info.has_gpu = True
            info.device = "mps"
            info.gpu_count = 1
            info.gpus = [{"name": "Apple Silicon MPS", "vram_gb": 0, "cuda_cores": 0, "compute": "mps"}]
            info.recommended_batch_size = 64
            info.recommended_workers = 1

    except ImportError:
        # torch not installed yet — assume CPU
        pass

    if not info.has_gpu:
        import os
        cpu_count = os.cpu_count() or 4
        info.recommended_batch_size = min(64, cpu_count * 8)
        info.recommended_workers = max(1, cpu_count // 2)

    _cached = info
    return info


def get_embedding_device() -> str:
    """Return the string device name for sentence-transformers."""
    return get_device_info().device


def _sm_to_cores(major: int, minor: int) -> int:
    """
    Map CUDA compute capability (SM version) to CUDA cores per SM.
    Covers Volta through Blackwell.
    """
    sm_cores = {
        (7, 0): 64,   # Volta (V100)
        (7, 5): 64,   # Turing (RTX 20xx, T4)
        (8, 0): 64,   # Ampere (A100)
        (8, 6): 128,  # Ampere (RTX 30xx, A10)
        (8, 9): 128,  # Ada Lovelace (RTX 40xx, L4)
        (9, 0): 128,  # Hopper (H100, H200)
        (10, 0): 128, # Blackwell (B100+)
    }
    return sm_cores.get((major, minor), 64)


def print_device_summary() -> None:
    """Print a human-readable hardware summary to console."""
    from rich.console import Console
    from rich.table import Table

    info = get_device_info()
    console = Console()

    if not info.has_gpu:
        console.print(f"[yellow]Hardware:[/yellow] CPU-only mode | batch_size={info.recommended_batch_size} | workers={info.recommended_workers}")
        return

    table = Table(title="GPU Hardware Profile", show_header=True, header_style="bold cyan")
    table.add_column("GPU #")
    table.add_column("Name")
    table.add_column("VRAM")
    table.add_column("CUDA Cores")
    table.add_column("Compute Cap.")

    for g in info.gpus:
        table.add_row(
            str(g["index"]),
            g["name"],
            f"{g['vram_gb']:.1f} GB",
            f"{g['cuda_cores']:,}" if g["cuda_cores"] else "N/A",
            g["compute"],
        )

    console.print(table)
    console.print(f"[green]Recommended batch size:[/green] {info.recommended_batch_size} | [green]Workers:[/green] {info.recommended_workers}")


if __name__ == "__main__":
    print_device_summary()
