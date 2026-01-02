"""
sphinxcontrib.mat_directives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend autodoc directives to matlabdomain.

:copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

from sphinx.ext.autodoc.directive import (
    AutodocDirective,
    DocumenterBridge,
    DummyOptionSpec,
    parse_generated_content,
    process_documenter_options,
)
from sphinx.util.logging import getLogger

logger = getLogger("matlab-domain")


class MatlabAutodocDirective(AutodocDirective):
    """A directive class for all MATLAB autodoc directives.

    Modified version of the Python AutodocDirective

    It works as a dispatcher of Documenters. It invokes a Documenter on running.
    After the processing, it parses and returns the generated content by
    Documenter.
    """

    option_spec = DummyOptionSpec()
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        reporter = self.state.document.reporter

        try:
            source, lineno = reporter.get_source_and_line(self.lineno)  # type: ignore
        except AttributeError:
            source, lineno = (None, None)
        logger.debug(
            "[sphinxcontrib-matlabdomain] Input at %s:%s\n\n%s\n",
            source,
            lineno,
            self.block_text.strip(),
        )

        # look up target Documenter
        objtype = self.name.replace("auto", "")  # Removes auto
        doccls = self.env.app.registry.documenters[objtype]

        # process the options with the selected documenter's option_spec
        try:
            documenter_options = process_documenter_options(
                doccls, self.config, self.options
            )
        except (KeyError, ValueError, TypeError) as exc:
            # an option is either unknown or has a wrong type
            logger.error(
                "[sphinxcontrib-matlabdomain] An option to %s is either unknown or has an invalid value: %s",
                self.name,
                exc,
                location=(source, lineno),
            )
            return []

        # generate the output
        params = DocumenterBridge(
            self.env, reporter, documenter_options, lineno, self.state
        )
        documenter = doccls(params, self.arguments[0])
        documenter.generate(more_content=self.content)
        if not params.result:
            return []

        lines = "\n".join(params.result)
        logger.debug(
            "[sphinxcontrib-matlabdomain] Generated output at %s:%s\n%s",
            source,
            lineno,
            lines,
        )

        # record all filenames as dependencies -- this will at least
        # partially make automatic invalidation possible
        for fn in params.record_dependencies:
            self.state.document.settings.record_dependencies.add(fn)

        result = parse_generated_content(self.state, params.result, documenter)
        return result
