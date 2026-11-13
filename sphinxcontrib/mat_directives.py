"""The ``mat:auto*`` directives that run the MATLAB documenters.

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

from sphinx.ext.autodoc.directive import (
    AutodocDirective,
    DummyOptionSpec,
    parse_generated_content,
    process_documenter_options,
)
from sphinx.util.logging import getLogger

from . import mat_config
from .mat_documenters import MatDocumenterBridge
from .mat_sidecars import PAGE_LOCATION, HelpPaths
from .mat_types import MatObject
from .mat_typing import override

logger = getLogger("matlab-domain")

#: options of this extension that ``autodoc_default_options`` may set (autodoc
#: itself merges only its own); ``:no-<option>:`` turns one off
DEFAULT_OPTIONS = ("hidden-mask-parameters", "references")
#: the configuration value without which ``:inherited-members:`` does nothing
INHERITED_VALUE = "matlab_inherited_members"


def check_inherited_members(_app, config):
    """``config-inited``: ConfigError unless ``matlab_inherited_members`` is a
    bool; one warning for the build when ``autodoc_default_options`` turns
    ``inherited-members`` on without it.
    """
    if mat_config.typed_value(config, INHERITED_VALUE):
        return
    value = config.autodoc_default_options.get("inherited-members", False)
    if value is not False:
        logger.warning(
            "[sphinxcontrib-matlabdomain] autodoc_default_options sets "
            "inherited-members, which needs %s = True in conf.py; the "
            "inherited members are left out",
            INHERITED_VALUE,
            type="mat",
            subtype="directive",
        )


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

    @override
    def run(self):
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
        defaults = self.config.autodoc_default_options
        for name in DEFAULT_OPTIONS:
            negated = self.options.pop(f"no-{name}", True) is None
            if (
                name in doccls.option_spec
                and name in defaults
                and name not in self.options
                and not negated
            ):
                self.options[name] = defaults[name]
        self._check_inherited_members(doccls)
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
                location=self.get_location(),
            )
            return []

        # Objects described in the generated content are where the outermost
        # auto directive is written (the generated text is in no file).
        temp_data = self.env.temp_data
        outer = temp_data.get(PAGE_LOCATION)
        if outer is None:
            temp_data[PAGE_LOCATION] = self.get_location()
        try:
            return self._generate(doccls, documenter_options, source, lineno)
        finally:
            if outer is None:
                temp_data.pop(PAGE_LOCATION, None)

    def _check_inherited_members(self, doccls):
        """Warn that ``:inherited-members:``, written in this directive, does
        nothing without ``matlab_inherited_members``.
        """
        name = "inherited-members"
        if (
            name in self.options
            and name in doccls.option_spec
            and not self.config.matlab_inherited_members
        ):
            logger.warning(
                "[sphinxcontrib-matlabdomain] :inherited-members: needs "
                "%s = True in conf.py; the inherited members are left out",
                INHERITED_VALUE,
                type="mat",
                subtype="directive",
                location=self.get_location(),
            )

    def _generate(self, doccls, documenter_options, source, lineno):
        reporter = self.state.document.reporter
        params = MatDocumenterBridge(
            self.env,
            reporter,
            documenter_options,
            lineno,
            self.state,
            location=self.get_location(),
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
