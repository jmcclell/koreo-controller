import asyncio
import logging

import kr8s.asyncio

logger = logging.getLogger("koreo.controller.resource")

LOOKUP_TIMEOUT = 15

_plural_map: dict[str, str] = {}

_lookup_locks: dict[str, asyncio.Event] = {}
_lookup_locks_guard = asyncio.Lock()


async def get_full_kind(
    api: kr8s.asyncio.Api, kind: str, api_version: str
) -> str | None:
    lookup_kind = f"{kind}.{api_version}"

    async def wait_for_result(lookup_lock: asyncio.Event) -> str | None:
        """Wait for the lookup lock to be set and return the full kind."""
        logger.debug(f"Waiting for plural kind lookup lock for {lookup_kind}")
        await lookup_lock.wait()
        if lookup_kind in _plural_map:
            logger.debug(f"Received plural kind for {lookup_kind} after waiting.")
            return _plural_map[lookup_kind]
        raise Exception(f"Waiting on {lookup_kind} failed.")

    async def get_result(lookup_lock: asyncio.Event) -> str | None:
        attempts = 3
        try:
            for attempt in range(1, attempts):
                logger.debug(f"Attempting to find plural kind for {lookup_kind} (attempt {attempt} of {attempts})")
                try:
                    async with asyncio.timeout(LOOKUP_TIMEOUT):
                        try:
                            (_, plural_kind, _) = await api.lookup_kind(lookup_kind)
                            break
                        except ValueError as e:
                            logger.debug(
                                    f"Failed to find plural kind for {lookup_kind} on attempt {attempt}: {e}"
                            )
                            logger.exception(
                                f"Failed to find Kind (`{lookup_kind}`) information. Can not start controller!"
                            )
                            return None
                except asyncio.TimeoutError:
                    logger.debug(
                        f"Timed out while looking up plural kind for {lookup_kind} on attempt {attempt}"
                    )
                    continue
            else:
                logger.error(
                    f"Too many failed attempts to find plural kind for {lookup_kind}."
                )
                raise Exception(
                    f"Too many failed attempts to find plural kind for {lookup_kind}"
                )
            logger.debug(f"Found plural kind for {lookup_kind}: {plural_kind}")
            full_kind = f"{plural_kind}.{api_version}"
            logger.debug(f"Setting plural kind for {lookup_kind} to {full_kind}")
            _plural_map[lookup_kind] = full_kind
            return full_kind
        finally:
            logger.debug(f"Cleaning up locks and triggering event for {lookup_kind}")
            lookup_lock.set()
            del _lookup_locks[lookup_kind]

    if lookup_kind in _plural_map:
        return _plural_map[lookup_kind]

    async with _lookup_locks_guard:
        if lookup_kind in _lookup_locks:
            lookup_lock = _lookup_locks[lookup_kind]
            return await wait_for_result(lookup_lock)
        else:
            lookup_lock = asyncio.Event()
            _lookup_locks[lookup_kind] = lookup_lock
            return await get_result(lookup_lock)


def _reset():
    """Helper for unit testing; not intended for usage in normal code."""
    _plural_map.clear()

    for lock in _lookup_locks.values():
        lock.set()

    _lookup_locks.clear()
