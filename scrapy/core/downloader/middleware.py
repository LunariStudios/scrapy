"""
Downloader Middleware manager

See documentation in docs/topics/downloader-middleware.rst
"""

from __future__ import annotations

import time
import warnings
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from scrapy import signals
from scrapy.exceptions import ScrapyDeprecationWarning, _InvalidOutput
from scrapy.http import Request, Response
from scrapy.middleware import MiddlewareManager
from scrapy.utils.conf import build_component_list
from scrapy.utils.defer import (
    _defer_sleep_async,
    deferred_from_coro,
    ensure_awaitable,
    maybe_deferred_to_future,
)
from scrapy.utils.python import global_object_name

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from twisted.internet.defer import Deferred

    from scrapy import Spider
    from scrapy.settings import BaseSettings


class DownloaderMiddlewareManager(MiddlewareManager):
    component_name = "downloader middleware"

    @classmethod
    def _get_mwlist_from_settings(cls, settings: BaseSettings) -> list[Any]:
        return build_component_list(settings.getwithbase("DOWNLOADER_MIDDLEWARES"))

    def _add_middleware(self, mw: Any) -> None:
        if hasattr(mw, "process_request"):
            self.methods["process_request"].append(mw.process_request)
            self._check_mw_method_spider_arg(mw.process_request)
        if hasattr(mw, "process_response"):
            self.methods["process_response"].appendleft(mw.process_response)
            self._check_mw_method_spider_arg(mw.process_response)
        if hasattr(mw, "process_exception"):
            self.methods["process_exception"].appendleft(mw.process_exception)
            self._check_mw_method_spider_arg(mw.process_exception)

    def download(
        self,
        download_func: Callable[[Request, Spider], Deferred[Response]],
        request: Request,
        spider: Spider,
    ) -> Deferred[Response | Request]:
        warnings.warn(
            "DownloaderMiddlewareManager.download() is deprecated, use download_async() instead",
            ScrapyDeprecationWarning,
            stacklevel=2,
        )

        @wraps(download_func)
        async def download_func_wrapped(request: Request) -> Response:
            return await maybe_deferred_to_future(download_func(request, spider))

        self._set_compat_spider(spider)
        return deferred_from_coro(self.download_async(download_func_wrapped, request))

    async def download_async(
        self,
        download_func: Callable[[Request], Coroutine[Any, Any, Response]],
        request: Request,
    ) -> Response | Request:
        async def process_request(request: Request) -> Response | Request:
            chain_start_time = time.perf_counter()
            middlewares_executed: list[str] = []
            chain_error: BaseException | None = None
            
            try:
                for method in self.methods["process_request"]:
                    method = cast("Callable", method)
                    middleware_name = method.__qualname__.split('.')[0] if hasattr(method, '__qualname__') else 'Unknown'
                    middlewares_executed.append(middleware_name)
                    
                    method_start = time.perf_counter()
                    method_error: BaseException | None = None
                    try:
                        if method in self._mw_methods_requiring_spider:
                            response = await ensure_awaitable(
                                method(request=request, spider=self._spider),
                                _warn=global_object_name(method),
                            )
                        else:
                            response = await ensure_awaitable(
                                method(request=request), _warn=global_object_name(method)
                            )
                        if response is not None and not isinstance(
                            response, (Response, Request)
                        ):
                            raise _InvalidOutput(
                                f"Middleware {method.__qualname__} must return None, Response or "
                                f"Request, got {response.__class__.__name__}"
                            )
                    except BaseException as exc:
                        method_error = exc
                        raise
                    finally:
                        method_duration = time.perf_counter() - method_start
                        if self.crawler:
                            self.crawler.signals.send_catch_log(
                                signal=signals.middleware_method_complete,
                                manager_type=self.component_name,
                                method_name="process_request",
                                middleware_name=middleware_name,
                                duration=method_duration,
                                error=method_error,
                            )
                    if response:
                        return response
                return await download_func(request)
            except BaseException as exc:
                chain_error = exc
                raise
            finally:
                chain_duration = time.perf_counter() - chain_start_time
                if self.crawler:
                    self.crawler.signals.send_catch_log(
                        signal=signals.middleware_chain_complete,
                        manager=self,
                        method_name="process_request",
                        obj=request,
                        args=(),
                        middlewares_executed=middlewares_executed,
                        middleware_count=len(middlewares_executed),
                        start_time=chain_start_time,
                        duration=chain_duration,
                        error=chain_error,
                    )

        async def process_response(response: Response | Request) -> Response | Request:
            if response is None:
                raise TypeError("Received None in process_response")
            if isinstance(response, Request):
                return response

            chain_start_time = time.perf_counter()
            middlewares_executed: list[str] = []
            chain_error: BaseException | None = None
            
            try:
                for method in self.methods["process_response"]:
                    method = cast("Callable", method)
                    middleware_name = method.__qualname__.split('.')[0] if hasattr(method, '__qualname__') else 'Unknown'
                    middlewares_executed.append(middleware_name)
                    
                    method_start = time.perf_counter()
                    method_error: BaseException | None = None
                    try:
                        if method in self._mw_methods_requiring_spider:
                            response = await ensure_awaitable(
                                method(request=request, response=response, spider=self._spider),
                                _warn=global_object_name(method),
                            )
                        else:
                            response = await ensure_awaitable(
                                method(request=request, response=response),
                                _warn=global_object_name(method),
                            )
                        if not isinstance(response, (Response, Request)):
                            raise _InvalidOutput(
                                f"Middleware {method.__qualname__} must return Response or Request, "
                                f"got {type(response)}"
                            )
                    except BaseException as exc:
                        method_error = exc
                        raise
                    finally:
                        method_duration = time.perf_counter() - method_start
                        if self.crawler:
                            self.crawler.signals.send_catch_log(
                                signal=signals.middleware_method_complete,
                                manager_type=self.component_name,
                                method_name="process_response",
                                middleware_name=middleware_name,
                                duration=method_duration,
                                error=method_error,
                            )
                    if isinstance(response, Request):
                        return response
                return response
            except BaseException as exc:
                chain_error = exc
                raise
            finally:
                chain_duration = time.perf_counter() - chain_start_time
                if self.crawler:
                    self.crawler.signals.send_catch_log(
                        signal=signals.middleware_chain_complete,
                        manager=self,
                        method_name="process_response",
                        obj=response,
                        args=(),
                        middlewares_executed=middlewares_executed,
                        middleware_count=len(middlewares_executed),
                        start_time=chain_start_time,
                        duration=chain_duration,
                        error=chain_error,
                    )

        async def process_exception(exception: Exception) -> Response | Request:
            chain_start_time = time.perf_counter()
            middlewares_executed: list[str] = []
            chain_error: BaseException | None = None
            
            try:
                for method in self.methods["process_exception"]:
                    method = cast("Callable", method)
                    middleware_name = method.__qualname__.split('.')[0] if hasattr(method, '__qualname__') else 'Unknown'
                    middlewares_executed.append(middleware_name)
                    
                    method_start = time.perf_counter()
                    method_error: BaseException | None = None
                    try:
                        if method in self._mw_methods_requiring_spider:
                            response = await ensure_awaitable(
                                method(
                                    request=request, exception=exception, spider=self._spider
                                ),
                                _warn=global_object_name(method),
                            )
                        else:
                            response = await ensure_awaitable(
                                method(request=request, exception=exception),
                                _warn=global_object_name(method),
                            )
                        if response is not None and not isinstance(
                            response, (Response, Request)
                        ):
                            raise _InvalidOutput(
                                f"Middleware {method.__qualname__} must return None, Response or "
                                f"Request, got {type(response)}"
                            )
                    except BaseException as exc:
                        method_error = exc
                        raise
                    finally:
                        method_duration = time.perf_counter() - method_start
                        if self.crawler:
                            self.crawler.signals.send_catch_log(
                                signal=signals.middleware_method_complete,
                                manager_type=self.component_name,
                                method_name="process_exception",
                                middleware_name=middleware_name,
                                duration=method_duration,
                                error=method_error,
                            )
                    if response:
                        return response
                raise exception
            except BaseException as exc:
                chain_error = exc
                raise
            finally:
                chain_duration = time.perf_counter() - chain_start_time
                if self.crawler:
                    self.crawler.signals.send_catch_log(
                        signal=signals.middleware_chain_complete,
                        manager=self,
                        method_name="process_exception",
                        obj=request,
                        args=(),
                        middlewares_executed=middlewares_executed,
                        middleware_count=len(middlewares_executed),
                        start_time=chain_start_time,
                        duration=chain_duration,
                        error=chain_error,
                    )

        try:
            result: Response | Request = await process_request(request)
        except Exception as ex:
            await _defer_sleep_async()
            # either returns a request or response (which we pass to process_response())
            # or reraises the exception
            result = await process_exception(ex)
        return await process_response(result)
