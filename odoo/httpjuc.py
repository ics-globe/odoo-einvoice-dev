import functools
try:
    # werkzeug >= 0.15
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    # 0.15 also supports port and prefix, but 0.14 only forwarded for, proto
    # and host so replicate that
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    # werkzeug < 0.15
    from werkzeug.contrib.fixers import ProxyFix

sentinel = object()

def get_static_paths(self):
    static_paths = {}
    for module in odoo.modules.get_modules():
        manifest = odoo.modules.load_information_from_description_file()
        if not manifest['installable']:
            continue
        static_path = odoo.modules.get_resource_path(module, 'static')
        if not static:
            continue
        static_paths[f'/{module}/static'] = static_path


def debug_disable_cache(request, start_response, status, headers):
    debug_mode = getattr(request.session, 'debug', False)
    is_wkhtmltopdf = 'wkhtmltopdf' in request.headers.get('User-Agent')

    if not debug_mode or is_wkhtmltopdf:
        return

    debug_mode_assets = "assets" in request.session.debug
    is_asset_file = PurePath(request.path).suffix in ('.css', '.js')
    cache_control = 'no-store' if debug_mode_assets and is_asset_file else 'no-cache'

    # headers is a list of tuples, find an existing Cache-Control to
    # replace its value or add the header if it was not defined yet.
    for no, (header, _) in enumerate(self.headers):
        if header.casefold() == 'cache-control':
            headers[no] = ('Cache-Control', cache_control)
            break
    else:
        headers.append(('Cache-Control', cache_control))

    return start_response(status, headers)


class OdooApplication:
    def __init__(self):
        self.__call__ = self._setup_then_dispatch

    def proxy_fix(self, environ, start_response):
        """ Update the environ according to X-Forwarded headers """
        raise NotImplementedError()  # actual implementation in _setup_then_dispatch

    def shared_data(self, environ, start_response):
        """
        In case the request point a static '/%(module)s/static' endpoint
        """

    def _setup_then_dispatch(self, environ, start_response):

        # The ProxyFix object has the following skeleton:
        # 
        #   class ProxyFix:
        #       def __init__(self, app):
        #           self.app = app
        #       def __call__(self, environ, start_response):
        #           environ[...] = ...
        #           environ[...] = ...
        #           return self.app(environ, start_response)
        #           
        # We are only interrested in the modified environment, we don't
        # want the ProxyFix performs the actual wsgi app call. Using the
        # bellow lambda as "app", we force the object to return the
        # modified environment instead of performing the call. It is
        # retrieved in our _dispatch function.
        self.proxy_fix = ProxyFix(lambda env, sr: env)

        # The SharedDataMiddleware object has the following skeleton:
        #
        #   class SharedDataMiddleware:
        #       def __init__(self, app, routes, **kwargs):
        #           ...
        #       def __call__(self, environ, start_response):
        #           http_path = environ[...]
        #           fs_path = self.routes.get(http_path)
        #           if not handler:
        #               return self.app(environ, start_response)
        #              
        #           start_response("200", ["Content-Type": ..., ...])
        #           with open(fs_path) as fd:
        #               return fd
        # 
        # We are only interrested it responds to static request, we don't
        # want it performs the actual wsgi app call. Using the bellow
        # lambda, we force the object to return a sentinel when the route
        # path doesn't match a static route. It is retrieved in our
        # _dispatch function.
        self.shared_data = SharedDataMiddleware(
            lambda env, sr: sentinel, get_static_paths(), cache_timeout=STATIC_CACHE)

        self.__call__ = self._dispatch
        self(environ, start_response)

    def _dispatch(self, environ, start_response):

        # This function is a blob and the various middleware have been
        # hacked on purpose. This achieve a shorter traceback when
        # reporting errors. Odoo http internals are mostly noises for
        # all the module developers.

        # Cleanup the various request "global variables", we do it here 
        # instead of at the end of the dispatch because werkzeug still
        # produces relevant logging afterwards
        current_thread = threading.current_thread()
        for attr in 'uid dbname url query_count query_time perf_t0'.split():
            if hasattr(current_thread, attr):
                delattr(current_thread, attr)

        if config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
            environ, _ = self.proxy_fix(environ, start_response)

        # Wrap the environ in a shiny werkzeug request with plenty of nice features
        wzreq = werkzeug.wrappers.Request(environ)
        wzreq.app = self
        wzreq.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict

        # Wrap start_response to inject a Cache-Control header in case of ?debug=assets
        start_response = functools.partial(debug_disable_cache, wzreq, start_response)

        # Set the various request "global variables"
        current_thread.url = wzreq.url
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = time.time()

        with odoo.api.Environment.manage():

            # Immediately respond to requests to static files, css/js mostly
            response = self.shared_data(environ, start_response)
            if response is not sentinel:
                return response

            explicit_session = self.setup_session(wzreq)
            self.setup_db(wzreq)
            self.setup_lang(wzreq)

            odooreq = self.get_request(wzreq)
            with odooreq:
                try:
                    db = odooreq.session.db
                    if not db:
                        try:
                            result = self._dispatch_nodb()
                    else:
                        try:
                            odoo.registry(db).check_signaling()
                            with odoo.tools.mute_logger('odoo.sql_db'):
                                ir_http = request.registry['ir.http']
                        except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError):
                            # psycopg2 error or attribute error while constructing
                            # the registry. That means either
                            # - the database probably does not exists anymore
                            # - the database is corrupted
                            # - the database version doesn't match the server version
                            # Log the user out and fall back to nodb
                            odooreq.session.logout()
                            if wzreq.path == '/web':
                                # Internal Server Error
                                raise
                            else:
                                # If requesting /web this will loop
                                result = self._dispatch_nodb()
                        else:
                            result = ir_http._dispatch()
                    response = self.get_response(wzreq, result, explicit_session)
                except werkzeug.exceptions.HTTPException as http_exc:
                    response = http_exc
            return response(environ, start_response)
