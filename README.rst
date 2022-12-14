zkvvm
=====

A completely experimental and untested zkVyper version manager.

Usage
-----

#. Install with pip.

    .. code-block:: shell

        $ pip install git+https://github.com/skellet0r/zkvvm@master#egg=zkvvm

#. Use the built-in CLI

    .. code-block:: shell

        $ zkvvm --help
        usage: zkvvm [-h] [--cache-dir CACHE_DIR] [--log-file LOG_FILE] [-v] {ls,ls-remote,install,uninstall} ...

        zkVyper Version Manager

        optional arguments:
        -h, --help            show this help message and exit
        --cache-dir CACHE_DIR
                                Default: /home/user/.cache/zkvvm
        --log-file LOG_FILE   Default: /home/user/.cache/zkvvm/log/zkvvm.log
        -v

        commands:
        {ls,ls-remote,install,uninstall}
            ls                  List available local versions
            ls-remote           List available remote versions
            install             Install a remote version
            uninstall           Uninstall a local version

#. Use in a script

    .. code-block:: python

        import zkvvm

        output = zkvvm.compile(["tmp/Foo.vy"])

        src = """# @version 0.3.3

        @view
        @external
        def foo(_a: uint256) -> uint256:
            return _a
        """
        output = zkvvm.compile_source(src, zk_version="1.1.1", vyper_version="0.3.3")
