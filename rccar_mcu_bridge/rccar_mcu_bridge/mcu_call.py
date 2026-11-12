"""Awaitable, timeout-guarded service call for rclpy coroutine callbacks."""


async def call_service(node, client, request, timeout_s, group=None):
    """
    Call ``client`` without blocking the executor; return the response or None.

    None means the service was not ready, the call timed out, or it failed.
    The caller's callbacks and the client must share a reentrant callback group,
    otherwise awaiting the response would deadlock a mutually exclusive group.
    """
    if not client.service_is_ready():
        return None
    future = client.call_async(request)
    timer = node.create_timer(timeout_s, future.cancel, callback_group=group)
    try:
        await future
    except Exception as exc:  # noqa: BLE001 - report as a failed call
        node.get_logger().warning(f'service call failed: {exc}')
        return None
    finally:
        node.destroy_timer(timer)
    if future.cancelled():
        client.remove_pending_request(future)
        return None
    return future.result()
