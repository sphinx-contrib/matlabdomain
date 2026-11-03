"""sphinxcontrib.mat_directives.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend autodoc directives to matlabdomain.

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
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

from .mat_sidecars import HelpPaths
from .mat_types import MatObject

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
        source, lineno = self.get_source_info()
        logger.debug(
            "[sphinxcontrib-matlabdomain] Input at %s:%s\n\n%s\n",
            source,
            lineno,
            self.block_text.strip(),
        )

        # look up target Documenter
        objtype = self.name.replace("auto", "")  # Removes auto
        doccls = MatObject.sphinx_app.registry.documenters[objtype]

        # process the options with the selected documenter's option_spec
        try:
            documenter_options = process_documenter_options(
                doccls, self.config, self.options
            )
        except (KeyError, ValueError, TypeError) as exc:
            # an option is either unknown or has a wrong type
            logger.error(
                (
                    "[sphinxcontrib-matlabdomain] "
                    "An option to %s is either unknown "
                    "or has an invalid value: %s"
                ),
                self.name,
                exc,
                location=(self.env.docname, lineno),
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

        # Source files are not dependencies; the domain tracks them (doc_sources).
        paths = HelpPaths(self.env, self.state.document)
        with paths.parsing():
            result = parse_generated_content(self.state, params.result, documenter)
        paths.rewrite(result)
        return result
