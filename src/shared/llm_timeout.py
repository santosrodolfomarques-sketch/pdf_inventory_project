from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

T = TypeVar("T")


class LLMTimeoutError(TimeoutError):
    """Erro lançado quando uma chamada LLM excede o tempo máximo configurado."""


def run_with_timeout(func: Callable[[], T], timeout_seconds: int) -> T:
    """
    Executa func() em uma thread e retorna timeout sem bloquear indefinidamente.

    Importante: não usamos ``with ThreadPoolExecutor(...)`` porque o contexto do executor
    aguarda a thread terminar no ``__exit__``. Se a chamada externa estiver pendurada,
    isso faz o processo parecer travado mesmo depois do timeout. Por isso usamos
    ``shutdown(wait=False, cancel_futures=True)`` no finally.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        raise LLMTimeoutError(f"Chamada LLM excedeu {timeout_seconds}s") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
